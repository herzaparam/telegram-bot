# Phase 4: LLM Decision Maker - Research

**Researched:** 2026-03-24
**Domain:** LLM structured output, prompt engineering, deterministic fallback logic
**Confidence:** HIGH

## Summary

Phase 4 builds the "decide" stage of the pipeline, which reads engine signals from the `signals` table, constructs a prompt for each asset, calls the LLM via `llm_completion()` with JSON mode, parses the structured verdict, and stores the result in `daily_decisions`. A deterministic weighted-average fallback handles LLM unavailability.

The existing infrastructure is well-suited for this phase. The `llm_completion()` function in `src/llm/client.py` already handles retry + model fallback + timeout and returns `LLM_UNAVAILABLE` on total failure. The `DailyDecision` model in `src/db/models.py` already has all required columns (verdict, score, confidence, reasoning, key_factors, risk_warning, all_signals, model_used). The `SignalRepository` in `src/db/signal_repo.py` provides `get_signals_for_asset()` to read engine outputs. The `PipelineRunner` already has "decide" in its default stage list and a `timeout_llm` of 30 seconds.

**Primary recommendation:** Follow the established `analyze_stage` pattern exactly -- create `decide_stage(session, asset)` as a `StageFunc`, build a `DecisionRepository` mirroring `SignalRepository`, and extend `llm_completion()` to accept `response_format` kwargs for JSON mode.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** All prompts and reasoning in English only. Indonesian terms used only for specific names (IHSG, laporan keuangan, asset names like BBCA)
- **D-02:** Concise analyst persona -- brief, data-driven reasoning. Leads with verdict + key factors. Like a Bloomberg terminal note. Target ~100-200 words per asset
- **D-03:** Engine data sent as scores + key indicators (~500 tokens/asset). Example: `Technical: score=0.65, conf=0.8, RSI(14)=32, MACD=bullish_cross`. Full reasoning text NOT included in prompt
- **D-04:** One asset per LLM call -- focused context, error isolation per asset. Matches existing per-asset pipeline pattern in `analyze_stage`
- **D-05:** Use litellm JSON mode (`response_format={'type': 'json_object'}`) for structured verdict output
- **D-06:** JSON schema includes: `verdict` (string), `score` (float), `confidence` (float), `reasoning` (string), `key_factors` (list[string]), `risk_warning` (string|null)
- **D-07:** On malformed JSON or missing fields: retry once with a stricter prompt, then fall through to deterministic fallback marked `LLM_PARSE_ERROR`
- **D-08:** Contradictions defined as: two engines with opposite score signs (one >+0.3, other <-0.3) AND both with confidence >0.5
- **D-09:** LLM instructed explicitly in system prompt: "Identify any contradictions between engine signals. When engines disagree, explain why and lower your confidence"
- **D-10:** Contradictions woven into the reasoning text -- no separate JSON field. Simpler schema, cleaner for Telegram display
- **D-11:** LLM flags contradictions in reasoning AND reduces confidence score. Verdict still reflects LLM's net assessment
- **D-12:** When LLM fails 3x or returns unparseable output: compute confidence-weighted average of engine scores
- **D-13:** Verdict thresholds: >0.6 STRONG BUY, >0.2 BUY, -0.2 to 0.2 HOLD, <-0.2 SELL, <-0.6 STRONG SELL. Same config weights as engine scoring
- **D-14:** Fallback confidence: computed from engine agreement, capped at 0.5 max. Signals lower reliability than LLM verdict
- **D-15:** Fallback reasoning: auto-generated summary listing weighted score and each engine's contribution
- **D-16:** Fallback populates key_factors (extracted from top engine signals) and risk_warning = "LLM unavailable -- verdict based on engine scores only, no contextual analysis"
- **D-17:** Stub event context in prompt: "Upcoming Events" section present but empty or says "No event data available yet."

### Claude's Discretion
- Exact system prompt wording and structure
- JSON schema field names and validation logic
- Engine weight configuration values for fallback
- Retry prompt wording for malformed JSON
- How to extract key indicators from Signal.indicators JSONB for prompt construction
- DecisionRepository method signatures and query patterns
- Decide stage wiring into PipelineRunner
- `all_signals` JSONB shape in DailyDecision (how to serialize engine signals)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LLM-01 | LLM reads all engine scores + valuation data + context to produce final verdict | `SignalRepository.get_signals_for_asset()` provides engine signals; prompt construction formats scores + key indicators; event stub for future context |
| LLM-02 | LLM detects contradictions between signals (e.g., bullish technicals but overvalued) | Contradiction detection logic (D-08 thresholds) pre-computed and injected into prompt; LLM instructed to flag in reasoning (D-09) |
| LLM-03 | LLM considers upcoming events that could invalidate signals | Stub "Upcoming Events" section in prompt (D-17); extensible for Phase 8 event engine |
| LLM-05 | LLM outputs STRONG BUY / BUY / HOLD / SELL / STRONG SELL + reasoning + fair value context | JSON mode structured output (D-05/D-06); verdict enum with 5 levels; fallback uses same thresholds (D-13) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Async Python pipeline with per-asset checkpointing
- litellm for LLM abstraction (gpt-4o-mini primary, Gemini fallback)
- Two-process model: pipeline never imports bot modules
- $0.50-1.00/month LLM cost target -- use gpt-4o-mini, keep prompts compact (~500 tokens/asset)
- pydantic-settings for configuration
- structlog for logging with component binding
- Frozen dataclasses for immutable results
- Per-asset error isolation -- failures produce fallback, never crash pipeline
- StageFunc signature: `async def stage(session: AsyncSession, asset: Asset) -> None`
- Google-style docstrings with Args/Returns sections
- ruff + mypy strict mode

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| litellm | 1.82.6+ | LLM gateway with JSON mode | Already in stack; `response_format` param supported for OpenAI and Gemini |
| sqlalchemy[asyncio] | 2.0.48+ | ORM for DecisionRepository | Already in stack; matches SignalRepository pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | -- | Parse LLM JSON response | Always -- `json.loads()` on `LLMResult.content` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| json.loads + manual validation | Pydantic model for response parsing | Pydantic adds type safety but is heavier; manual validation is simpler for 6 fields and matches project's dataclass convention |
| response_format json_schema | response_format json_object | json_schema provides stricter guarantees but not all fallback models support it; json_object is more portable across providers |

**No new dependencies required.** All needed libraries are already installed.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── llm/
│   ├── client.py          # Extend llm_completion() to accept response_format kwargs
│   ├── prompts.py          # NEW: System prompt template, prompt builder, indicator formatter
│   └── __init__.py
├── data/
│   ├── decide.py           # NEW: decide_stage() StageFunc, fallback logic, contradiction detection
│   └── ...
├── db/
│   ├── decision_repo.py    # NEW: DecisionRepository (mirrors signal_repo.py)
│   └── ...
├── pipeline/
│   ├── main.py             # Wire decide_stage into stage_funcs dict
│   └── ...
└── config.py               # Add engine weight settings for fallback
```

### Pattern 1: Decide Stage (mirrors analyze_stage)
**What:** `decide_stage(session, asset)` loads signals, builds prompt, calls LLM, parses response, stores decision
**When to use:** Every pipeline run for the "decide" stage
**Example:**
```python
# Source: Derived from src/data/analyze.py pattern
async def decide_stage(session: AsyncSession, asset: Asset) -> None:
    """Decide stage matching StageFunc signature."""
    log = logger.bind(asset=asset.symbol, asset_type=asset.asset_type)

    # 1. Load today's signals
    signals = await signal_repo.get_signals_for_asset(session, asset.id, date.today())
    if not signals:
        log.warning("no_signals_for_decision")
        return

    # 2. Detect contradictions
    contradictions = _detect_contradictions(signals)

    # 3. Build prompt
    messages = build_decision_prompt(asset, signals, contradictions)

    # 4. Call LLM with JSON mode
    result = await llm_completion(
        messages=messages,
        response_format={"type": "json_object"},
    )

    # 5. Parse or fallback
    if result.model_used == "none":
        decision = _deterministic_fallback(signals)
    else:
        decision = _parse_llm_response(result.content, signals)
        if decision is None:
            # Retry once with stricter prompt
            result2 = await llm_completion(
                messages=build_strict_retry_prompt(asset, signals),
                response_format={"type": "json_object"},
            )
            decision = _parse_llm_response(result2.content, signals)
            if decision is None:
                decision = _deterministic_fallback(signals, reason="LLM_PARSE_ERROR")

    # 6. Store decision
    await decision_repo.upsert_decision(session, asset.id, date.today(), decision, result.model_used)
```

### Pattern 2: DecisionRepository (mirrors SignalRepository)
**What:** UPSERT-based repository for `daily_decisions` table
**When to use:** Writing and reading decisions
**Example:**
```python
# Source: Derived from src/db/signal_repo.py pattern
class DecisionRepository:
    async def upsert_decision(
        self,
        session: AsyncSession,
        asset_id: int,
        decision_date: date,
        decision: DecisionResult,
        model_used: str,
    ) -> None:
        stmt = pg_insert(DailyDecision).values(
            asset_id=asset_id,
            date=decision_date,
            verdict=decision.verdict,
            score=decision.score,
            confidence=decision.confidence,
            reasoning=decision.reasoning,
            key_factors=decision.key_factors,
            risk_warning=decision.risk_warning,
            all_signals=decision.all_signals,
            model_used=model_used,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["asset_id", "date"],
            set_={...},
        )
        await session.execute(stmt)
```

### Pattern 3: Prompt Construction
**What:** Build system + user messages from signals data
**When to use:** Before each LLM call
**Example:**
```python
# Prompt structure (Claude's discretion on exact wording)
def build_decision_prompt(
    asset: Asset,
    signals: list[SignalRecord],
    contradictions: list[str],
) -> list[dict[str, str]]:
    system = """You are a concise financial analyst. Analyze the engine signals and produce a verdict.
Output valid JSON with keys: verdict, score, confidence, reasoning, key_factors, risk_warning.
verdict must be one of: STRONG BUY, BUY, HOLD, SELL, STRONG SELL.
score: float -1.0 to 1.0. confidence: float 0.0 to 1.0.
reasoning: 100-200 words, data-driven. key_factors: list of 3-5 strings.
risk_warning: string or null.
Identify any contradictions between engine signals. When engines disagree, explain why and lower your confidence."""

    user = _format_engine_data(asset, signals, contradictions)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
```

### Pattern 4: Extending llm_completion for JSON mode
**What:** Pass `response_format` kwargs through to litellm.acompletion
**When to use:** When calling LLM with structured output
**Example:**
```python
# In src/llm/client.py -- add **kwargs to pass response_format through
async def llm_completion(
    messages: list[dict[str, str]],
    model: str | None = None,
    fallback_models: list[str] | None = None,
    num_retries: int | None = None,
    timeout: int | None = None,
    response_format: dict[str, str] | None = None,  # NEW
) -> LLMResult:
    ...
    kwargs: dict[str, object] = {
        "model": model,
        "messages": messages,
        "num_retries": retries,
        "timeout": tout,
        "fallbacks": fallbacks,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format

    response = await litellm.acompletion(**kwargs)
```

### Anti-Patterns to Avoid
- **Passing full engine reasoning text to LLM:** Wastes tokens, exceeds cost budget. Send scores + key indicators only (~500 tokens/asset per D-03)
- **Batch multi-asset calls:** Violates D-04 (one asset per call) and breaks error isolation
- **Custom JSON parser instead of json.loads:** Standard library is sufficient; don't hand-roll
- **Raising exceptions from decide_stage:** Must produce a fallback verdict, never crash. Exceptions would propagate to PipelineRunner which marks asset as failed

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM retry + fallback | Custom retry loop | `llm_completion()` with litellm's built-in `num_retries` + `fallbacks` | Already handles 3 retries + Gemini fallback; battle-tested in Phase 1 |
| JSON parsing | Custom JSON tokenizer | `json.loads()` + field validation | stdlib JSON is fast and reliable |
| DB UPSERT | Raw SQL | SQLAlchemy `pg_insert().on_conflict_do_update()` | Matches existing SignalRepository pattern |
| Verdict enum validation | String matching | Set membership check `{"STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"}` | Simple, explicit, no enum import needed |

## Common Pitfalls

### Pitfall 1: LLM Returns Valid JSON But Wrong Schema
**What goes wrong:** LLM returns `{"answer": "buy"}` instead of `{"verdict": "BUY", "score": 0.5, ...}`
**Why it happens:** JSON mode guarantees valid JSON, not schema compliance
**How to avoid:** Validate all 6 required fields after `json.loads()`. On missing/wrong fields, trigger retry with stricter prompt, then fallback (D-07)
**Warning signs:** `KeyError` or `TypeError` when accessing parsed response fields

### Pitfall 2: Numeric(4,3) Column Overflow
**What goes wrong:** LLM returns score > 1.0 or < -1.0, causing DB constraint violation
**Why it happens:** `Numeric(4,3)` in DailyDecision.score allows values from -9.999 to 9.999, but semantically we want -1.0 to 1.0. Confidence is 0.0 to 1.0
**How to avoid:** Clamp score to [-1.0, 1.0] and confidence to [0.0, 1.0] before DB write
**Warning signs:** `DataError` from PostgreSQL on insert

### Pitfall 3: Forgetting response_format in Retry Call
**What goes wrong:** Retry call to LLM omits `response_format` and gets plain text back
**Why it happens:** Copy-paste error or separate code path for retry
**How to avoid:** Both initial and retry calls must pass `response_format={"type": "json_object"}`
**Warning signs:** `json.JSONDecodeError` on retry

### Pitfall 4: Empty Signals List
**What goes wrong:** Decide stage called when analyze stage was skipped or failed for this asset
**Why it happens:** PipelineRunner processes stages independently; analyze failure doesn't block decide
**How to avoid:** Check for empty signals at the top of `decide_stage()` and return early (log warning, skip asset)
**Warning signs:** Empty prompt, wasted LLM call, meaningless verdict

### Pitfall 5: Timeout Double-Counting
**What goes wrong:** LLM call takes 25s, retry takes 25s, total 50s exceeds `timeout_llm` (30s)
**Why it happens:** `PipelineRunner.run_stage()` wraps `stage_func` in `asyncio.wait_for(timeout=30)`, but retry doubles the time
**How to avoid:** Set a shorter per-call timeout (e.g., 12s) so that initial call + retry + parse all fit within the 30s stage timeout. Or increase `timeout_llm` to 60s to accommodate retries
**Warning signs:** `TimeoutError` from PipelineRunner during retry path

### Pitfall 6: JSON Mode Not Supported by Fallback Model
**What goes wrong:** litellm falls back to a model that doesn't support `response_format`
**Why it happens:** Not all models support JSON mode identically
**How to avoid:** Both gpt-4o-mini and gemini-2.0-flash support JSON mode via litellm. Verified in litellm docs. If adding other fallbacks, test JSON mode support first
**Warning signs:** Error from litellm about unsupported parameter

## Code Examples

### Contradiction Detection
```python
# Source: Derived from D-08 thresholds
def _detect_contradictions(signals: list[SignalRecord]) -> list[str]:
    """Detect contradictions between engine signals.

    A contradiction exists when two engines have opposite score signs
    (one > +0.3, other < -0.3) and both have confidence > 0.5.

    Args:
        signals: List of SignalRecord from the signals table.

    Returns:
        List of human-readable contradiction descriptions.
    """
    contradictions: list[str] = []
    for i, s1 in enumerate(signals):
        for s2 in signals[i + 1:]:
            if (
                s1.confidence > 0.5
                and s2.confidence > 0.5
                and (
                    (s1.score > 0.3 and s2.score < -0.3)
                    or (s1.score < -0.3 and s2.score > 0.3)
                )
            ):
                contradictions.append(
                    f"{s1.category} ({s1.score:+.2f}) vs "
                    f"{s2.category} ({s2.score:+.2f})"
                )
    return contradictions
```

### Deterministic Fallback
```python
# Source: Derived from D-12 through D-16
from dataclasses import dataclass

@dataclass(frozen=True)
class DecisionResult:
    """Parsed decision from LLM or fallback."""

    verdict: str
    score: float
    confidence: float
    reasoning: str
    key_factors: list[str]
    risk_warning: str | None
    all_signals: dict[str, object]

VERDICT_THRESHOLDS = [
    (0.6, "STRONG BUY"),
    (0.2, "BUY"),
    (-0.2, "HOLD"),
    (-0.6, "SELL"),
]

def _score_to_verdict(score: float) -> str:
    """Convert numeric score to verdict string."""
    for threshold, verdict in VERDICT_THRESHOLDS:
        if score > threshold:
            return verdict
    return "STRONG SELL"

def _deterministic_fallback(
    signals: list[SignalRecord],
    reason: str = "LLM_UNAVAILABLE",
) -> DecisionResult:
    """Compute fallback verdict from engine signals."""
    if not signals:
        return DecisionResult(
            verdict="HOLD",
            score=0.0,
            confidence=0.0,
            reasoning=f"Deterministic fallback ({reason}). No engine signals available.",
            key_factors=["No data"],
            risk_warning="No engine signals -- cannot assess",
            all_signals={},
        )

    total_weight = sum(s.confidence for s in signals)
    if total_weight == 0:
        weighted_score = 0.0
    else:
        weighted_score = sum(s.score * s.confidence for s in signals) / total_weight

    # Engine agreement: lower spread = higher confidence, capped at 0.5
    scores = [s.score for s in signals]
    spread = max(scores) - min(scores) if len(scores) > 1 else 0.0
    confidence = min(0.5, max(0.1, 1.0 - spread))

    # Build reasoning
    engine_parts = [
        f"{s.category}: {s.score:+.2f} (conf {s.confidence:.1f})"
        for s in signals
    ]
    reasoning = (
        f"Deterministic fallback ({reason}). "
        f"Weighted score: {weighted_score:+.2f} from {len(signals)} engines. "
        + ", ".join(engine_parts) + "."
    )

    # Extract key factors from top signals
    key_factors = [
        f"{s.category}: {s.score:+.2f}"
        for s in sorted(signals, key=lambda x: abs(x.score), reverse=True)[:3]
    ]

    return DecisionResult(
        verdict=_score_to_verdict(weighted_score),
        score=round(weighted_score, 3),
        confidence=round(confidence, 3),
        reasoning=reasoning,
        key_factors=key_factors,
        risk_warning="LLM unavailable -- verdict based on engine scores only, no contextual analysis",
        all_signals={s.category: {"score": s.score, "confidence": s.confidence} for s in signals},
    )
```

### Indicator Formatting for Prompt
```python
# Source: Derived from D-03 and Signal.indicators JSONB
def _format_engine_data(
    asset: Asset,
    signals: list[SignalRecord],
    contradictions: list[str],
) -> str:
    """Format engine signals into compact prompt text (~500 tokens)."""
    lines = [f"Asset: {asset.symbol} ({asset.name or asset.asset_type})"]

    for sig in signals:
        # Extract key indicators from JSONB
        ind = sig.indicators or {}
        indicator_parts = [f"{k}={v}" for k, v in list(ind.items())[:6]]
        indicator_str = ", ".join(indicator_parts) if indicator_parts else "none"
        lines.append(
            f"{sig.category.title()}: score={sig.score:+.2f}, "
            f"conf={sig.confidence:.1f}, {indicator_str}"
        )

    if contradictions:
        lines.append(f"\nContradictions detected: {'; '.join(contradictions)}")

    lines.append("\nUpcoming Events: No event data available yet.")

    return "\n".join(lines)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Plain text LLM output + regex parsing | JSON mode (`response_format`) | OpenAI 2024, litellm 2024 | Reliable structured output without fragile parsing |
| Function calling for structured output | JSON mode or json_schema | litellm 2025 | Simpler for pure data extraction; function calling better for tool use |

**Deprecated/outdated:**
- Regex-based LLM output parsing: Fragile, replaced by JSON mode
- litellm `response_format` with `json_schema` strict mode: Available but not universally supported across all fallback models; `json_object` is more portable

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/test_data/test_decide.py tests/test_llm/ tests/test_db/test_decision_repo.py -x -vv` |
| Full suite command | `pytest` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LLM-01 | decide_stage reads signals and produces verdict via LLM | unit | `pytest tests/test_data/test_decide.py::TestDecideStage -x` | Wave 0 |
| LLM-02 | Contradiction detection when engines disagree | unit | `pytest tests/test_data/test_decide.py::TestContradictionDetection -x` | Wave 0 |
| LLM-03 | Event stub present in prompt | unit | `pytest tests/test_data/test_decide.py::TestPromptConstruction -x` | Wave 0 |
| LLM-05 | Verdict output with 5 levels + reasoning + fair value context | unit | `pytest tests/test_data/test_decide.py::TestVerdictOutput -x` | Wave 0 |
| FALLBACK | Deterministic fallback on LLM failure | unit | `pytest tests/test_data/test_decide.py::TestDeterministicFallback -x` | Wave 0 |
| PARSE | JSON response parsing with retry on malformed | unit | `pytest tests/test_data/test_decide.py::TestResponseParsing -x` | Wave 0 |
| REPO | DecisionRepository UPSERT | integration | `pytest tests/test_db/test_decision_repo.py -x` | Wave 0 |
| WIRE | decide_stage wired into PipelineRunner | unit | `pytest tests/test_pipeline/test_runner.py -x` | Extend existing |

### Sampling Rate
- **Per task commit:** `pytest tests/test_data/test_decide.py tests/test_db/test_decision_repo.py -x -vv`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_data/test_decide.py` -- covers LLM-01, LLM-02, LLM-03, LLM-05, fallback, parsing
- [ ] `tests/test_db/test_decision_repo.py` -- covers DecisionRepository UPSERT
- [ ] `tests/test_llm/test_client.py` -- extend with JSON mode response_format tests

## Open Questions

1. **Timeout budget for retry path**
   - What we know: `timeout_llm` is 30s, `PipelineRunner` wraps stage_func in `asyncio.wait_for(30s)`. Initial LLM call + retry + parse must fit within 30s.
   - What's unclear: Whether to set per-call timeout to ~12s (fitting 2 calls in 30s) or increase `timeout_llm` to 60s
   - Recommendation: Set per-call LLM timeout to 12s for the decide stage. Two calls (12s + 12s) plus parsing overhead fits in 30s. If this proves too tight, increase `timeout_llm` in config.

2. **Engine weight values for fallback**
   - What we know: Currently only technical and quantitative engines exist. Equal weighting is simplest.
   - What's unclear: Whether to use confidence-weighting (D-12) or add explicit per-engine weights in config
   - Recommendation: Use confidence-weighting as specified in D-12 (simpler, no new config needed). Each signal's score is weighted by its confidence. Add per-engine weight config later if needed.

## Sources

### Primary (HIGH confidence)
- `src/llm/client.py` -- existing LLM wrapper, retry + fallback logic
- `src/db/models.py` -- DailyDecision model with all required columns
- `src/engines/base.py` -- Signal dataclass structure
- `src/data/analyze.py` -- analyze_stage pattern to replicate
- `src/db/signal_repo.py` -- SignalRepository pattern to replicate
- `src/pipeline/runner.py` -- PipelineRunner stage execution, timeout handling
- `src/config.py` -- Settings with LLM config values
- [litellm JSON mode docs](https://docs.litellm.ai/docs/completion/json_mode) -- response_format parameter support

### Secondary (MEDIUM confidence)
- litellm docs confirmed JSON mode support for both gpt-4o-mini and gemini-2.0-flash

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all libraries already in use
- Architecture: HIGH -- follows established patterns (analyze_stage, SignalRepository)
- Pitfalls: HIGH -- derived from concrete codebase analysis (timeout math, column constraints, error paths)

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- litellm JSON mode is mature, codebase patterns are established)
