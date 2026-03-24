# Phase 4: LLM Decision Maker - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

The LLM synthesizes all available engine scores into a final verdict with structured output, contradiction detection, event awareness, and a deterministic fallback. Verdicts are stored in `daily_decisions` and ready for delivery. Covers: decide stage function, LLM prompt construction, JSON-mode structured output, contradiction detection, deterministic weighted-average fallback, decision repository. Does NOT include: Telegram delivery (Phase 5), accuracy evaluation (Phase 6), lesson injection (Phase 7), event engine (Phase 8), or additional engines beyond technical + quantitative.

</domain>

<decisions>
## Implementation Decisions

### Prompt Design & Language
- **D-01:** All prompts and reasoning in English only. Indonesian terms used only for specific names (IHSG, laporan keuangan, asset names like BBCA)
- **D-02:** Concise analyst persona — brief, data-driven reasoning. Leads with verdict + key factors. Like a Bloomberg terminal note. Target ~100-200 words per asset
- **D-03:** Engine data sent as scores + key indicators (~500 tokens/asset). Example: `Technical: score=0.65, conf=0.8, RSI(14)=32, MACD=bullish_cross`. Full reasoning text NOT included in prompt
- **D-04:** One asset per LLM call — focused context, error isolation per asset. Matches existing per-asset pipeline pattern in `analyze_stage`

### Structured Output Parsing
- **D-05:** Use litellm JSON mode (`response_format={'type': 'json_object'}`) for structured verdict output
- **D-06:** JSON schema includes: `verdict` (string), `score` (float), `confidence` (float), `reasoning` (string), `key_factors` (list[string]), `risk_warning` (string|null)
- **D-07:** On malformed JSON or missing fields: retry once with a stricter prompt, then fall through to deterministic fallback marked `LLM_PARSE_ERROR`

### Contradiction Handling
- **D-08:** Contradictions defined as: two engines with opposite score signs (one >+0.3, other <-0.3) AND both with confidence >0.5
- **D-09:** LLM instructed explicitly in system prompt: "Identify any contradictions between engine signals. When engines disagree, explain why and lower your confidence"
- **D-10:** Contradictions woven into the reasoning text — no separate JSON field. Simpler schema, cleaner for Telegram display
- **D-11:** LLM flags contradictions in reasoning AND reduces confidence score. Verdict still reflects LLM's net assessment

### Deterministic Fallback
- **D-12:** When LLM fails 3x or returns unparseable output: compute confidence-weighted average of engine scores
- **D-13:** Verdict thresholds: >0.6 STRONG BUY, >0.2 BUY, -0.2 to 0.2 HOLD, <-0.2 SELL, <-0.6 STRONG SELL. Same config weights as engine scoring
- **D-14:** Fallback confidence: computed from engine agreement, capped at 0.5 max. Signals lower reliability than LLM verdict
- **D-15:** Fallback reasoning: auto-generated summary listing weighted score and each engine's contribution (e.g., "Deterministic fallback (LLM unavailable). Weighted score: +0.42 from 2 engines. Technical: +0.65 (conf 0.8), Quantitative: +0.10 (conf 0.4).")
- **D-16:** Fallback populates key_factors (extracted from top engine signals) and risk_warning = "LLM unavailable — verdict based on engine scores only, no contextual analysis"

### Event Awareness
- **D-17:** Stub event context in prompt: "Upcoming Events" section present but empty or says "No event data available yet." When Phase 8 adds the event engine, it plugs in naturally

### Claude's Discretion
- Exact system prompt wording and structure
- JSON schema field names and validation logic
- Engine weight configuration values for fallback
- Retry prompt wording for malformed JSON
- How to extract key indicators from Signal.indicators JSONB for prompt construction
- DecisionRepository method signatures and query patterns
- Decide stage wiring into PipelineRunner
- `all_signals` JSONB shape in DailyDecision (how to serialize engine signals)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & LLM Integration
- `plan/ARCHITECTURE.md` — Full system architecture, LLM integration design, daily execution flow, decision schema
- `plan/ARCHITECTURE.md` §Core Interfaces — Decision dataclass, LLM prompt structure, verdict enum
- `plan/ARCHITECTURE.md` §Daily Execution Flow — Stage 4 (DECIDE) processes one asset at a time through LLM

### Existing LLM Infrastructure
- `src/llm/client.py` — `llm_completion()` with retry + fallback, `LLMResult` dataclass, `LLM_UNAVAILABLE` sentinel. Phase 4 builds on this
- `src/config.py` — Settings with `llm_primary_model`, `llm_fallback_model`, `llm_max_retries`, `llm_timeout` (30s)

### Decision Storage
- `src/db/models.py` — `DailyDecision` model with verdict, score, confidence, reasoning, key_factors, risk_warning, all_signals, model_used columns. Already exists from Phase 1
- `src/db/migrations/versions/001_initial_schema.py` — Initial migration including daily_decisions table

### Engine Output (Phase 3 foundation)
- `src/engines/base.py` — `BaseEngine` ABC, `Signal` dataclass (score, confidence, reasoning, indicators, data_quality)
- `src/data/analyze.py` — `analyze_stage()` showing per-asset engine execution pattern, `_get_engines_for_asset()`, signal storage
- `src/db/signal_repo.py` — SignalRepository for reading engine signals (input to decide stage)

### Pipeline Infrastructure (Phase 1 foundation)
- `src/pipeline/runner.py` — PipelineRunner with `StageFunc` interface, per-asset checkpointing
- `src/pipeline/main.py` — Stage registration (`stage_funcs` dict), already has "decide" as CLI arg option

### Project Decisions
- `.planning/PROJECT.md` §Key Decisions — LiteLLM for model abstraction, sequential per-asset execution
- `.planning/PROJECT.md` §Constraints — $0.50-1.00/month LLM cost target, GPT-4o-mini primary

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/llm/client.py` — `llm_completion()` already handles retry + model fallback + timeout. Decide stage calls this with JSON mode params
- `src/db/models.py` — `DailyDecision` model fully defined with all needed columns (verdict, reasoning, key_factors, risk_warning, all_signals, model_used)
- `src/engines/base.py` — `Signal` dataclass with score, confidence, reasoning, indicators fields. These are the inputs to the LLM prompt
- `src/db/signal_repo.py` — SignalRepository pattern for reading signals to feed into LLM prompt
- `src/data/analyze.py` — `_get_engines_for_asset()` and per-asset processing pattern to replicate for decide stage

### Established Patterns
- StageFunc signature: `async def decide_stage(session: AsyncSession, asset: Asset) -> None`
- Per-asset error isolation: engine failures produce fallback signals, never crash pipeline
- Frozen dataclasses for immutable results (Signal, LLMResult, StageResult)
- structlog with component binding for logging
- pydantic-settings for configuration (engine weights, thresholds)

### Integration Points
- Decide stage plugs into PipelineRunner as `stage_funcs["decide"]` in `src/pipeline/main.py`
- Reads signals from `signals` table via SignalRepository (output of analyze stage)
- Writes to `daily_decisions` table via new DecisionRepository
- Uses `llm_completion()` from `src/llm/client.py` with additional JSON mode params

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing patterns (StageFunc, per-asset processing, frozen dataclasses).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-llm-decision-maker*
*Context gathered: 2026-03-24*
