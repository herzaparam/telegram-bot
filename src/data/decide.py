"""Decide stage: LLM-powered trading verdict with deterministic fallback.

Reads engine signals, calls LLM with structured JSON output, parses the response,
detects contradictions, falls back deterministically on failure, and stores decisions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date as date_type
from itertools import combinations

import structlog

from src.config import settings
from src.db.decision_repo import decision_repo
from src.db.lesson_repo import lesson_repo
from src.db.models import Asset, SignalRecord
from src.db.signal_repo import signal_repo
from src.llm.client import llm_completion
from src.llm.prompts import build_decision_prompt, build_strict_retry_prompt

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DecisionResult:
    """Result from the LLM decision maker or deterministic fallback.

    Attributes:
        verdict: Trading verdict (STRONG BUY, BUY, HOLD, SELL, STRONG SELL).
        score: Decision score from -1.0 to 1.0.
        confidence: Confidence level from 0.0 to 1.0.
        reasoning: Human-readable explanation.
        key_factors: List of key factor strings.
        risk_warning: Risk warning text, or None.
        all_signals: Dict of engine signals used for this decision.
    """

    verdict: str
    score: float
    confidence: float
    reasoning: str
    key_factors: list[str]
    risk_warning: str | None
    all_signals: dict[str, object]


VALID_VERDICTS = {"STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"}

VERDICT_THRESHOLDS = [
    (0.6, "STRONG BUY"),
    (0.2, "BUY"),
    (-0.2, "HOLD"),
    (-0.6, "SELL"),
]


def _score_to_verdict(score: float) -> str:
    """Map a numeric score to a verdict string using threshold ranges.

    Args:
        score: Numeric score from -1.0 to 1.0.

    Returns:
        Verdict string.
    """
    for threshold, verdict in VERDICT_THRESHOLDS:
        if score > threshold:
            return verdict
    return "STRONG SELL"


def _detect_contradictions(signals: list[SignalRecord]) -> list[str]:
    """Detect contradictions between engine signals.

    Per D-08: For each pair, if both confidence > 0.5 and one score > +0.3
    and the other < -0.3, it's a contradiction.

    Args:
        signals: List of signal records.

    Returns:
        List of contradiction description strings.
    """
    contradictions: list[str] = []
    for s1, s2 in combinations(signals, 2):
        if s1.confidence <= 0.5 or s2.confidence <= 0.5:
            continue
        if (s1.score > 0.3 and s2.score < -0.3) or (s2.score > 0.3 and s1.score < -0.3):
            contradictions.append(
                f"{s1.category} ({s1.score:+.2f}) vs {s2.category} ({s2.score:+.2f})"
            )
    return contradictions


def _build_all_signals(signals: list[SignalRecord]) -> dict[str, object]:
    """Build the all_signals dict from signal records.

    Args:
        signals: List of signal records.

    Returns:
        Dict mapping category to score and confidence.
    """
    return {
        s.category: {"score": s.score, "confidence": s.confidence}
        for s in signals
    }


def _deterministic_fallback(
    signals: list[SignalRecord],
    reason: str = "LLM_UNAVAILABLE",
) -> DecisionResult:
    """Compute a deterministic verdict from engine scores.

    Used when the LLM is unavailable or returns unparseable output.
    Confidence is capped at 0.5 per D-14.

    Args:
        signals: List of signal records.
        reason: Reason for fallback (e.g., LLM_UNAVAILABLE, LLM_PARSE_ERROR).

    Returns:
        A DecisionResult based on confidence-weighted scoring.
    """
    if not signals:
        return DecisionResult(
            verdict="HOLD",
            score=0.0,
            confidence=0.0,
            reasoning=f"Deterministic fallback ({reason}). No engine signals available.",
            key_factors=[],
            risk_warning="LLM unavailable -- no signals to analyze",
            all_signals={},
        )

    # Confidence-weighted average score (D-12)
    total_weight = sum(s.confidence for s in signals)
    if total_weight == 0:
        weighted_score = 0.0
    else:
        weighted_score = sum(s.score * s.confidence for s in signals) / total_weight

    # Confidence: capped at 0.5, based on spread (D-14)
    scores = [s.score for s in signals]
    spread = max(scores) - min(scores)
    confidence = min(0.5, max(0.1, 1.0 - spread))

    verdict = _score_to_verdict(weighted_score)

    # Key factors: top 3 signals by abs(score) (D-16)
    sorted_signals = sorted(signals, key=lambda s: abs(s.score), reverse=True)
    key_factors = [f"{s.category}: {s.score:+.2f}" for s in sorted_signals[:3]]

    # Engine details for reasoning (D-15)
    engine_details = ", ".join(f"{s.category}={s.score:+.2f}" for s in signals)
    reasoning = (
        f"Deterministic fallback ({reason}). "
        f"Weighted score: {weighted_score:+.2f} from {len(signals)} engines. "
        f"{engine_details}."
    )

    return DecisionResult(
        verdict=verdict,
        score=round(weighted_score, 4),
        confidence=round(confidence, 4),
        reasoning=reasoning,
        key_factors=key_factors,
        risk_warning="LLM unavailable -- verdict based on engine scores only, no contextual analysis",
        all_signals=_build_all_signals(signals),
    )


def _parse_llm_response(
    content: str,
    signals: list[SignalRecord],
) -> DecisionResult | None:
    """Parse LLM JSON response into a DecisionResult.

    Validates all 6 required fields and clamps score/confidence.
    Returns None on any parsing failure.

    Args:
        content: Raw LLM response string.
        signals: List of signal records (for building all_signals).

    Returns:
        DecisionResult if valid, None otherwise.
    """
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None

    # Validate all 6 required keys
    required_keys = {"verdict", "score", "confidence", "reasoning", "key_factors", "risk_warning"}
    if not required_keys.issubset(data.keys()):
        return None

    # Validate verdict
    verdict = data["verdict"]
    if verdict not in VALID_VERDICTS:
        return None

    # Clamp score and confidence (Pitfall 2)
    score = max(-1.0, min(1.0, float(data["score"])))
    confidence = max(0.0, min(1.0, float(data["confidence"])))

    # Ensure key_factors is a list of strings
    key_factors = data["key_factors"]
    if not isinstance(key_factors, list):
        key_factors = [str(key_factors)]

    return DecisionResult(
        verdict=verdict,
        score=score,
        confidence=confidence,
        reasoning=str(data["reasoning"]),
        key_factors=[str(f) for f in key_factors],
        risk_warning=data.get("risk_warning"),
        all_signals=_build_all_signals(signals),
    )


async def decide_stage(session: "AsyncSession", asset: Asset) -> None:  # noqa: F821
    """Decide stage matching StageFunc(session, asset) signature.

    Loads signals, calls LLM with JSON mode, parses response,
    falls back deterministically on failure, and stores the decision.

    Args:
        session: Async SQLAlchemy session.
        asset: Asset to produce a verdict for.
    """
    log = logger.bind(asset=asset.symbol, asset_type=asset.asset_type)

    # 1. Load today's signals
    today = date_type.today()
    signals = await signal_repo.get_signals_for_asset(session, asset.id, today)

    if not signals:
        log.warning("no_signals_for_decision")
        return

    # 2. Detect contradictions
    contradictions = _detect_contradictions(signals)
    if contradictions:
        log.info("contradictions_detected", count=len(contradictions))

    # 2.5 Load DD flags if available (LLM-06)
    dd_flags: list[dict[str, str]] | None = None
    if asset.asset_type == "stock":
        try:
            from sqlalchemy import select as sa_select

            from src.db.models import DueDiligenceReport

            dd_stmt = (
                sa_select(DueDiligenceReport.dd_flags)
                .where(DueDiligenceReport.asset_id == asset.id)
                .order_by(DueDiligenceReport.report_date.desc())
                .limit(1)
            )
            dd_result = await session.execute(dd_stmt)
            dd_row = dd_result.scalar_one_or_none()
            if dd_row:
                dd_flags = dd_row
                log.info("dd_flags_loaded", count=len(dd_flags))
        except Exception:
            log.debug("dd_flags_load_failed", exc_info=True)

    # Guard: ensure dd_flags is actually a list (not a coroutine from mocked session)
    if dd_flags is not None and not isinstance(dd_flags, list):
        dd_flags = None

    # 2.5b Load relevant lessons for injection (D-12)
    engine_categories = list({s.category for s in signals})
    relevant_lessons = await lesson_repo.get_relevant_lessons(
        session, asset.asset_type, engine_categories, max_lessons=20
    )
    lessons_for_prompt: list[dict[str, object]] | None = None
    if relevant_lessons:
        lessons_for_prompt = [
            {
                "id": l.id,
                "lesson": l.lesson,
                "asset_type": l.asset_type,
                "engine_tags": l.engine_tags or [],
                "accuracy": (l.times_correct / l.times_applied) if l.times_applied > 0 else None,
                "times_applied": l.times_applied,
            }
            for l in relevant_lessons
        ]
        log.info("lessons_injected", count=len(relevant_lessons))

    # 3. Build prompt and call LLM
    messages = build_decision_prompt(asset, signals, contradictions, lessons=lessons_for_prompt, dd_flags=dd_flags)
    result = await llm_completion(
        messages=messages,
        response_format={"type": "json_object"},
        timeout=settings.timeout_decide_per_call,
    )

    decision: DecisionResult | None = None
    model_used = result.model_used

    if result.model_used == "none":
        # LLM unavailable -- use deterministic fallback
        decision = _deterministic_fallback(signals)
        model_used = "none"
    else:
        # Try to parse LLM response
        decision = _parse_llm_response(result.content, signals)

        if decision is None:
            # Retry with stricter prompt
            log.warning("llm_parse_failed_retrying")
            retry_messages = build_strict_retry_prompt(asset, signals)
            retry_result = await llm_completion(
                messages=retry_messages,
                response_format={"type": "json_object"},
                timeout=settings.timeout_decide_per_call,
            )
            decision = _parse_llm_response(retry_result.content, signals)

            if decision is None:
                # Both attempts failed -- deterministic fallback
                log.warning("llm_parse_failed_twice_using_fallback")
                decision = _deterministic_fallback(signals, reason="LLM_PARSE_ERROR")
                model_used = f"{result.model_used}_fallback"

    # 4. Store decision
    await decision_repo.upsert_decision(
        session=session,
        asset_id=asset.id,
        decision_date=today,
        verdict=decision.verdict,
        score=decision.score,
        confidence=decision.confidence,
        reasoning=decision.reasoning,
        key_factors=decision.key_factors,
        risk_warning=decision.risk_warning,
        all_signals=decision.all_signals,
        model_used=model_used,
    )

    # 5. Record lessons applied and update lesson counters
    if relevant_lessons:
        lessons_applied_data = {
            str(l.id): l.lesson for l in relevant_lessons
        }
        await decision_repo.update_lessons_applied(
            session, asset.id, today, lessons_applied_data
        )
        await lesson_repo.increment_times_applied(
            session, [l.id for l in relevant_lessons]
        )

    log.info(
        "decision_stored",
        verdict=decision.verdict,
        score=decision.score,
        confidence=decision.confidence,
        model_used=model_used,
    )
