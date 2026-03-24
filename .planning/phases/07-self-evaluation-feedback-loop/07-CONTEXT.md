# Phase 7: Self-Evaluation Feedback Loop - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

The LLM reviews its past mistakes, extracts concrete lessons, stores them in tiers, and injects them into future decisions — the system improves over time without human intervention. Covers: reflect stage function, per-asset LLM analysis, batch cross-cutting analysis, lesson extraction with deduplication, lessons table with engine+topic tags, performance-based invalidation, lesson injection into decide prompt, lessons_applied tracking, /lessons command, "Lessons applied today" in daily report. Does NOT include: engine weight auto-tuning (future phase), automated retraining of ML models, additional analysis engines, or news/event integration (Phase 8).

</domain>

<decisions>
## Implementation Decisions

### Lesson Extraction — Stage Design
- **D-01:** New `reflect_stage` runs as a separate pipeline stage AFTER `evaluate_stage`. Evaluate stays fast/deterministic, reflect is the LLM-heavy step. Matches ARCHITECTURE.md's SELF-EVALUATE flow
- **D-02:** Reflect stage analyzes decisions at ALL matured evaluation windows (24h, 3d, 7d, 30d). Each window that matures on a given day triggers analysis for its qualifying decisions
- **D-03:** Scope: mistakes + surprising wins (correct decisions where confidence < 0.4). Skip correct high-confidence decisions — they don't yield useful lessons

### Lesson Extraction — LLM Analysis
- **D-04:** Two-pass extraction: (1) per-asset LLM analysis for each qualifying decision, then (2) batch cross-cutting pass summarizing patterns across all of yesterday's results
- **D-05:** Per-asset LLM output follows full ARCHITECTURE.md schema: analysis, missed_signals, overweighted engines, underweighted engines, lesson text, weight_adjustments
- **D-06:** Batch pass receives all per-asset analyses and extracts 1-3 cross-cutting lessons (tagged `asset_type: "all"`)
- **D-07:** Same model (GPT-4o-mini) for both per-asset and batch passes via existing `llm_completion()` with JSON mode

### Lesson Storage & Tiers
- **D-08:** Lessons tagged with three dimensions: `asset_type` (stock/crypto/all), `engine_tags` (list of engine names like "technical", "quantitative"), and `topic` (momentum, volatility, macro, sentiment, etc.)
- **D-09:** Performance-based invalidation: after 5+ applications, if accuracy drops below 40%, auto-set `still_valid = false`. Check runs during reflect stage
- **D-10:** LLM deduplication on extraction: when extracting a new lesson, include existing valid lessons in context. LLM either merges with an existing lesson (strengthening its text with new evidence) or creates a new one
- **D-11:** `source_decision_id` FK on lessons table for auditability. No denormalized snapshot — join back to decisions for full context

### Lesson Injection
- **D-12:** Dynamic injection: up to 20 relevant lessons injected into the LLM decision prompt, selected per-asset based on relevance. Some days may have 3, some 15
- **D-13:** Multi-factor scoring for lesson selection: composite of recency, accuracy rate, asset-type match, and engine relevance to current asset's signal set
- **D-14:** Prompt presents lessons in structured sections: "ASSET-SPECIFIC LESSONS:" and "GENERAL LESSONS:" with engine tags and accuracy stats per lesson
- **D-15:** `lessons_applied` JSONB on DailyDecision stores both lesson IDs and their text. Enables "Lessons applied today" display without joins

### /lessons Command
- **D-16:** Default view: split display showing "Recently learned" (last 7 days) and "Top lessons" (highest accuracy). Highlights both new insights and proven rules
- **D-17:** Filter syntax: `/lessons [asset_type] [engine]` — e.g., `/lessons crypto technical`. Both optional, defaults to all
- **D-18:** All lesson text and report content in English (carrying forward Phase 4 D-01, Phase 5 D-05)

### Daily Report — Lessons Applied
- **D-19:** Full per-asset lesson display: under each asset's signal card in the daily report, list which lessons influenced that specific decision with accuracy track record
- **D-20:** Matches REPT-05 requirement: "Lessons applied today" section visible in daily report

### Claude's Discretion
- Exact reflect stage `StageFunc` implementation details and error isolation
- LLM prompt wording for per-asset analysis and batch cross-cutting pass
- Multi-factor scoring weights for lesson selection
- Lesson topic taxonomy (specific topic values)
- Performance tracking implementation (how accuracy per lesson is computed)
- Alembic migration details for lessons table schema extensions
- /lessons message formatting and Telegram message splitting
- How to handle reflect stage when no qualifying decisions exist (skip gracefully)
- Dedup prompt design — how to present existing lessons for comparison

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Self-Evaluation Design
- `plan/ARCHITECTURE.md` — Full system architecture, SELF-EVALUATE flow diagram, `lessons` table schema, prompt builder step 4 ("Add recent lessons top 20"), LLM cost estimates for self-evaluation
- `plan/ARCHITECTURE.md` §Daily Execution Flow — Stage 1 (SELF-EVALUATE) processes yesterday's decisions with LLM analysis
- `plan/ARCHITECTURE.md` §Self-Evaluation Flow — Input/output schema for LLM analysis (analysis, missed_signals, overweighted, underweighted, lesson, weight_adjustments)

### Decision Storage (Phase 4 output, Phase 7 input)
- `src/data/decide.py` — Current decide stage implementation. Phase 7 modifies this to inject lessons and record lessons_applied
- `src/llm/prompts.py` — Current prompt builder. Phase 7 adds lesson injection sections
- `src/db/models.py` — `DailyDecision` model with existing `lessons_applied` JSONB column
- `src/db/decision_repo.py` — `DecisionRepository` for reading decisions to analyze

### Evaluation Data (Phase 6 output, Phase 7 input)
- `src/data/evaluate.py` — Evaluate stage implementation. Reflect stage runs AFTER this
- `src/db/evaluation_repo.py` — `EvaluationRepository` with evaluation results data
- `src/db/models.py` — `Evaluation` model with `was_correct`, `change_pct`, `engine_results`

### Signal Data (for per-engine analysis)
- `src/db/signal_repo.py` — `SignalRepository` for reading per-engine signals at time of decision
- `src/engines/base.py` — `BaseEngine` ABC, `Signal` dataclass

### Pipeline Infrastructure
- `src/pipeline/runner.py` — `PipelineRunner` with `StageFunc` interface
- `src/pipeline/main.py` — Stage registration (`stage_funcs` dict). Add `reflect` stage here

### Bot & Report Infrastructure
- `src/bot/handlers/report.py` — Report command handlers (pattern for /lessons handler)
- `src/report/formatter.py` — Shared report formatter (add lessons section to daily report)

### LLM Infrastructure
- `src/llm/client.py` — `llm_completion()` with retry + fallback + JSON mode
- `src/config.py` — Settings for timeouts, model names

### Prior Phase Context
- `.planning/phases/04-llm-decision-maker/04-CONTEXT.md` — D-01: English only, D-04: one asset per LLM call, D-05: JSON mode output
- `.planning/phases/06-accuracy-tracking-scorecard/06-CONTEXT.md` — D-05: per-engine accuracy, D-11: evaluate stage runs first

### Requirements
- `.planning/REQUIREMENTS.md` — EVAL-02 (LLM analyzes right/wrong), EVAL-03 (extract lessons), EVAL-04 (lessons feed into decisions), TBOT-05 (/lessons), REPT-05 (lessons applied today), LLM-04 (apply lessons learned)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/llm/client.py` — `llm_completion()` with JSON mode, retry, and fallback. Used by reflect stage for per-asset and batch analysis
- `src/llm/prompts.py` — Prompt builder pattern. Extend with lesson injection sections and new reflect prompts
- `src/db/models.py` — `DailyDecision.lessons_applied` JSONB column already exists. `lessons` table schema in ARCHITECTURE.md (needs migration)
- `src/db/evaluation_repo.py` — `EvaluationRepository` pattern for querying evaluation results to feed into reflect stage
- `src/db/signal_repo.py` — `SignalRepository` for reading per-engine signals at decision time
- `src/report/formatter.py` — Shared formatter between bot and pipeline. Add lessons section here
- `src/bot/handlers/report.py` — Existing handler pattern for `/lessons` command

### Established Patterns
- StageFunc signature: `async def reflect_stage(session: AsyncSession, asset: Asset) -> None`
- Per-asset error isolation: failures produce fallback behavior, never crash pipeline
- structlog with component binding for logging
- pydantic-settings for configuration (thresholds, scoring weights)
- Two-process boundary: bot MUST NOT import from `src/pipeline` or `src/llm`
- Alembic for all schema migrations
- HTML parse_mode for Telegram messages
- Frozen dataclasses for immutable results

### Integration Points
- Reflect stage plugs into PipelineRunner as `stage_funcs["reflect"]` — runs AFTER evaluate, BEFORE ingest
- Reads from `evaluations` table (which decisions were wrong/surprising) and `daily_decisions` + `signals` (original context)
- Writes to new `lessons` table (or updates existing lessons via dedup)
- Decide stage (`src/data/decide.py`) modified to: (1) query relevant lessons, (2) inject into prompt, (3) record lessons_applied
- `/lessons` handler reads from `lessons` table via bot-side repository
- Report formatter adds per-asset lessons section using `lessons_applied` from DailyDecision

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing patterns (StageFunc, per-asset processing, structlog logging, Alembic migrations, JSON mode LLM output).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-self-evaluation-feedback-loop*
*Context gathered: 2026-03-24*
