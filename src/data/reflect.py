"""Reflect stage: LLM-powered analysis of past decisions to extract lessons.

Runs AFTER evaluate_stage in the pipeline. Analyzes mistakes and surprising
wins, extracts lessons with dedup.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.data.evaluate import EVAL_WINDOWS
from src.db.decision_repo import decision_repo
from src.db.evaluation_repo import evaluation_repo
from src.db.lesson_repo import lesson_repo
from src.db.models import Asset, Lesson
from src.db.signal_repo import signal_repo
from src.llm.client import LLM_UNAVAILABLE, llm_completion

logger = structlog.get_logger(__name__)

# Max LLM calls per asset to prevent token budget explosion (Pitfall 1 from research)
MAX_ANALYSES_PER_ASSET = 3
# Max existing lessons shown for dedup context (Pitfall 2)
MAX_DEDUP_CONTEXT = 30

# Module-level accumulator for batch cross-cutting pass
_batch_analyses: list[dict] = []


async def reflect_stage(session: AsyncSession, asset: Asset) -> None:
    """Reflect on past decisions, extract lessons via LLM analysis.

    For each evaluation window, finds qualifying decisions (mistakes or
    surprising wins), analyzes them via LLM, extracts lessons with
    deduplication, and stores them.

    This stage is idempotent: already-reflected decisions are skipped.
    Error-isolated: exceptions are logged but never crash the pipeline.
    """
    log = logger.bind(asset=asset.symbol, asset_id=asset.id)

    try:
        today = date.today()
        analyses: list[dict] = []

        for window_name, window_delta in EVAL_WINDOWS:
            target_date = today - window_delta

            # Get decision for that date
            decision = await decision_repo.get_decision(session, asset.id, target_date)
            if decision is None:
                continue

            # Get evaluation
            evaluation = await evaluation_repo.get_evaluation(
                session, decision.id, window_name
            )
            if evaluation is None:
                continue

            # D-03 filter: only analyze mistakes + surprising wins
            # Skip correct decisions with reasonable confidence
            if evaluation.was_correct and float(decision.confidence or 1.0) >= 0.4:
                continue

            # Idempotency check (Pitfall 4): skip already-reflected decisions
            existing_lesson = await session.execute(
                select(Lesson.id)
                .where(Lesson.source_decision_id == decision.id)
                .limit(1)
            )
            if existing_lesson.scalar_one_or_none() is not None:
                continue

            # Analyze the decision
            analysis = await _analyze_decision(
                session, asset, decision, evaluation, window_name
            )
            if analysis is None:
                continue

            analyses.append(analysis)

            # Extract and store lesson
            await _extract_and_store_lesson(session, analysis, asset, decision)

            if len(analyses) >= MAX_ANALYSES_PER_ASSET:
                break

        # Lesson accuracy tracking (Pitfall 3)
        for window_name, window_delta in EVAL_WINDOWS:
            target_date = today - window_delta
            decision = await decision_repo.get_decision(session, asset.id, target_date)
            if decision is None:
                continue
            evaluation = await evaluation_repo.get_evaluation(
                session, decision.id, window_name
            )
            if evaluation is None:
                continue

            if evaluation.was_correct and decision.lessons_applied:
                lesson_ids = decision.lessons_applied.get("lesson_ids", [])
                for lid in lesson_ids:
                    if isinstance(lid, int):
                        await lesson_repo.update_lesson_accuracy(
                            session, lid, True
                        )

        # Run invalidation (D-09)
        await lesson_repo.invalidate_underperforming(session)

        # Accumulate for batch cross-cutting
        _batch_analyses.extend(analyses)

        if analyses:
            log.info("reflect_complete", lessons_extracted=len(analyses))
        else:
            log.debug("reflect_no_qualifying_decisions")

    except Exception:
        log.exception("reflect_stage_error")


async def _analyze_decision(
    session: AsyncSession,
    asset: Asset,
    decision,
    evaluation,
    window_name: str,
) -> dict | None:
    """Run per-asset LLM analysis on a single decision.

    Returns parsed analysis dict or None on failure.
    """
    log = logger.bind(asset=asset.symbol, decision_id=decision.id)

    # Get signals for the decision date
    signals = await signal_repo.get_signals_for_asset(
        session, asset.id, decision.date
    )

    # Build signal summary
    signal_lines = []
    for sig in signals:
        signal_lines.append(
            f"- {sig.category}: score={sig.score:+.2f}, confidence={sig.confidence:.2f}"
        )
    signal_text = "\n".join(signal_lines) if signal_lines else "No signals recorded."

    system_msg = (
        "You are a trading analyst reviewing past decisions. "
        "Analyze what went right or wrong.\n"
        "Output valid JSON with exactly these keys:\n"
        "- analysis: string (100-200 words analyzing the decision outcome)\n"
        "- missed_signals: list of strings (signals that were ignored or underweighted)\n"
        "- overweighted_engines: list of strings (engines given too much weight)\n"
        "- underweighted_engines: list of strings (engines given too little weight)\n"
        "- lesson: string (one concrete lesson, max 150 characters)\n"
        "- weight_adjustments: dict mapping engine name to suggested weight change (-0.1 to +0.1)"
    )

    user_msg = (
        f"Asset: {asset.symbol} ({asset.asset_type})\n"
        f"Decision date: {decision.date}\n"
        f"Verdict: {decision.verdict}\n"
        f"Score: {decision.score}\n"
        f"Confidence: {decision.confidence}\n"
        f"Window: {window_name}\n"
        f"Actual change: {evaluation.change_pct}%\n"
        f"Was correct: {evaluation.was_correct}\n"
        f"\nEngine signals:\n{signal_text}"
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    result = await llm_completion(
        messages=messages,
        response_format={"type": "json_object"},
        timeout=settings.timeout_decide_per_call,
    )

    if result is LLM_UNAVAILABLE or not result.content:
        log.warning("reflect_llm_unavailable", window=window_name)
        return None

    try:
        data = json.loads(result.content)
    except json.JSONDecodeError:
        log.warning("reflect_json_parse_error", content=result.content[:200])
        return None

    # Validate required keys
    required = {
        "analysis", "missed_signals", "overweighted_engines",
        "underweighted_engines", "lesson", "weight_adjustments",
    }
    if not required.issubset(data.keys()):
        log.warning("reflect_missing_keys", keys=list(data.keys()))
        return None

    # Enrich with context
    data["asset_symbol"] = asset.symbol
    data["asset_type"] = asset.asset_type
    data["decision_id"] = decision.id
    data["window"] = window_name

    return data


async def _extract_and_store_lesson(
    session: AsyncSession,
    analysis: dict,
    asset: Asset,
    decision,
) -> None:
    """Extract lesson from analysis, deduplicate against existing, and store.

    Falls back to raw lesson text on any LLM or parse failure.
    """
    log = logger.bind(asset=asset.symbol, decision_id=decision.id)

    # Get existing lessons for dedup context
    existing = await lesson_repo.get_valid_lessons(
        session, asset_type=asset.asset_type, limit=MAX_DEDUP_CONTEXT
    )

    # Build dedup prompt
    system_msg = (
        "You are comparing a new lesson against existing lessons. "
        "Output valid JSON with:\n"
        "- action: \"new\" or \"merge\"\n"
        "- merge_target_id: int or null (ID of existing lesson to merge with, "
        "only if action=\"merge\")\n"
        "- final_lesson_text: string (the lesson text to store -- either the "
        "new lesson or a merged version combining both)\n"
        "- topic: string (one of: momentum, volatility, trend, reversal, "
        "correlation, timing, risk, sentiment, macro, valuation, general)"
    )

    existing_lines = []
    existing_ids = set()
    for i, les in enumerate(existing):
        text_preview = les.lesson[:100]
        existing_lines.append(f"{i+1}. [ID={les.id}] {text_preview}")
        existing_ids.add(les.id)

    existing_text = "\n".join(existing_lines) if existing_lines else "No existing lessons."

    user_msg = (
        f"New lesson: {analysis['lesson']}\n\n"
        f"Existing lessons:\n{existing_text}"
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    try:
        result = await llm_completion(
            messages=messages,
            response_format={"type": "json_object"},
            timeout=settings.timeout_decide_per_call,
        )

        if result is LLM_UNAVAILABLE or not result.content:
            raise ValueError("LLM unavailable for dedup")

        data = json.loads(result.content)
        action = data.get("action", "new")
        merge_target_id = data.get("merge_target_id")
        final_text = data.get("final_lesson_text", analysis["lesson"])
        topic = data.get("topic", "general")

        if action == "merge" and merge_target_id in existing_ids:
            await lesson_repo.merge_lesson(session, merge_target_id, final_text)
            log.info("lesson_merged", target_id=merge_target_id)
        else:
            # New lesson
            engine_tags = list(set(
                analysis.get("overweighted_engines", [])
                + analysis.get("underweighted_engines", [])
            ))
            await lesson_repo.upsert_lesson(
                session,
                date=date.today(),
                asset_type=asset.asset_type,
                engine_tags=engine_tags or None,
                topic=topic,
                lesson_text=final_text,
                source_decision_id=decision.id,
            )
            log.info("lesson_created", topic=topic)

    except Exception:
        # Fallback: store raw lesson text
        log.warning("lesson_dedup_fallback", exc_info=True)
        engine_tags = list(set(
            analysis.get("overweighted_engines", [])
            + analysis.get("underweighted_engines", [])
        ))
        await lesson_repo.upsert_lesson(
            session,
            date=date.today(),
            asset_type=asset.asset_type,
            engine_tags=engine_tags or None,
            topic="general",
            lesson_text=analysis["lesson"],
            source_decision_id=decision.id,
        )


async def run_batch_cross_cutting(session: AsyncSession) -> None:
    """Run batch cross-cutting analysis across all assets.

    Extracts 1-3 lessons that apply across all assets from accumulated
    per-asset analyses. Called post-pipeline after all reflect_stage calls.
    """
    global _batch_analyses

    if len(_batch_analyses) < 2:
        _batch_analyses = []
        return

    log = logger.bind(batch_size=len(_batch_analyses))

    try:
        # Summarize accumulated analyses
        summaries = []
        for a in _batch_analyses:
            summaries.append(
                f"- {a['asset_symbol']} ({a['window']}): {a['lesson']}"
            )
        summary_text = "\n".join(summaries)

        system_msg = (
            "Extract 1-3 cross-cutting lessons that apply across all assets. "
            "Output JSON: {\"lessons\": [{\"lesson\": string, \"topic\": string, "
            "\"engine_tags\": list[str]}]}"
        )

        user_msg = (
            f"Per-asset analysis results:\n{summary_text}\n\n"
            "What patterns do you see across these assets?"
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        result = await llm_completion(
            messages=messages,
            response_format={"type": "json_object"},
            timeout=settings.timeout_decide_per_call,
        )

        if result is LLM_UNAVAILABLE or not result.content:
            log.warning("batch_cross_cutting_llm_unavailable")
            return

        data = json.loads(result.content)
        lessons = data.get("lessons", [])

        for les in lessons:
            if not isinstance(les, dict) or "lesson" not in les:
                continue
            await lesson_repo.upsert_lesson(
                session,
                date=date.today(),
                asset_type="all",
                engine_tags=les.get("engine_tags"),
                topic=les.get("topic", "general"),
                lesson_text=les["lesson"],
                source_decision_id=None,
            )

        log.info("batch_cross_cutting_complete", lessons_extracted=len(lessons))

    except Exception:
        log.exception("batch_cross_cutting_error")

    finally:
        _batch_analyses = []
