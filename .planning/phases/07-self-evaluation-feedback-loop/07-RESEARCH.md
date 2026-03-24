# Phase 7: Self-Evaluation Feedback Loop - Research

**Researched:** 2026-03-24
**Domain:** LLM self-reflection, lesson extraction, prompt injection, Telegram bot commands
**Confidence:** HIGH

## Summary

Phase 7 builds the feedback loop that makes the trading agent improve over time. The reflect stage runs after evaluate, analyzes mistakes and surprising wins via LLM, extracts lessons with deduplication, stores them in a tiered system (hypothesis/pattern/rule based on observation count), and injects relevant lessons into future decision prompts. The phase also adds a `/lessons` bot command and a "lessons applied today" section in the daily report.

The existing codebase provides strong foundations: `evaluate_stage` already identifies correct/wrong decisions with per-engine breakdown in `engine_results` JSONB, `llm_completion()` handles JSON mode with retry/fallback, `decision_repo` already has a `lessons_applied` JSONB column on `DailyDecision`, and the prompt builder in `src/llm/prompts.py` is ready for extension. The main new work is: (1) a `lessons` table via Alembic migration, (2) a `LessonRepository`, (3) a `reflect_stage` StageFunc, (4) prompt builder modifications for lesson injection, (5) decide stage modifications to query and record lessons, (6) `/lessons` handler, and (7) formatter additions for the daily report.

**Primary recommendation:** Follow the established repository + StageFunc + formatter patterns exactly. The lessons table extends the ARCHITECTURE.md schema with D-08 tagging dimensions (asset_type, engine_tags, topic). Keep LLM calls to two per reflect invocation (per-asset + batch cross-cutting) using JSON mode with the same `llm_completion()` wrapper.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** New `reflect_stage` runs as a separate pipeline stage AFTER `evaluate_stage`. Evaluate stays fast/deterministic, reflect is the LLM-heavy step. Matches ARCHITECTURE.md's SELF-EVALUATE flow
- **D-02:** Reflect stage analyzes decisions at ALL matured evaluation windows (24h, 3d, 7d, 30d). Each window that matures on a given day triggers analysis for its qualifying decisions
- **D-03:** Scope: mistakes + surprising wins (correct decisions where confidence < 0.4). Skip correct high-confidence decisions -- they don't yield useful lessons
- **D-04:** Two-pass extraction: (1) per-asset LLM analysis for each qualifying decision, then (2) batch cross-cutting pass summarizing patterns across all of yesterday's results
- **D-05:** Per-asset LLM output follows full ARCHITECTURE.md schema: analysis, missed_signals, overweighted engines, underweighted engines, lesson text, weight_adjustments
- **D-06:** Batch pass receives all per-asset analyses and extracts 1-3 cross-cutting lessons (tagged `asset_type: "all"`)
- **D-07:** Same model (GPT-4o-mini) for both per-asset and batch passes via existing `llm_completion()` with JSON mode
- **D-08:** Lessons tagged with three dimensions: `asset_type` (stock/crypto/all), `engine_tags` (list of engine names like "technical", "quantitative"), and `topic` (momentum, volatility, macro, sentiment, etc.)
- **D-09:** Performance-based invalidation: after 5+ applications, if accuracy drops below 40%, auto-set `still_valid = false`. Check runs during reflect stage
- **D-10:** LLM deduplication on extraction: when extracting a new lesson, include existing valid lessons in context. LLM either merges with an existing lesson (strengthening its text with new evidence) or creates a new one
- **D-11:** `source_decision_id` FK on lessons table for auditability. No denormalized snapshot -- join back to decisions for full context
- **D-12:** Dynamic injection: up to 20 relevant lessons injected into the LLM decision prompt, selected per-asset based on relevance. Some days may have 3, some 15
- **D-13:** Multi-factor scoring for lesson selection: composite of recency, accuracy rate, asset-type match, and engine relevance to current asset's signal set
- **D-14:** Prompt presents lessons in structured sections: "ASSET-SPECIFIC LESSONS:" and "GENERAL LESSONS:" with engine tags and accuracy stats per lesson
- **D-15:** `lessons_applied` JSONB on DailyDecision stores both lesson IDs and their text. Enables "Lessons applied today" display without joins
- **D-16:** Default view: split display showing "Recently learned" (last 7 days) and "Top lessons" (highest accuracy). Highlights both new insights and proven rules
- **D-17:** Filter syntax: `/lessons [asset_type] [engine]` -- e.g., `/lessons crypto technical`. Both optional, defaults to all
- **D-18:** All lesson text and report content in English (carrying forward Phase 4 D-01, Phase 5 D-05)
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
- Dedup prompt design -- how to present existing lessons for comparison

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-02 | LLM analyzes what went right/wrong and why | Reflect stage per-asset LLM analysis (D-04, D-05). Uses `llm_completion()` with JSON mode to produce analysis, missed_signals, overweighted/underweighted engines |
| EVAL-03 | System extracts concrete lessons and stores in database | Lesson extraction from LLM output + dedup against existing lessons (D-10). New `lessons` table with Alembic migration, `LessonRepository` with UPSERT |
| EVAL-04 | Lessons feed into future LLM decisions automatically | Lesson injection into decide prompt (D-12, D-13, D-14). Multi-factor scoring selects up to 20 relevant lessons per asset |
| LLM-04 | LLM applies lessons learned from past mistakes | Same as EVAL-04 -- prompt builder extended with "ASSET-SPECIFIC LESSONS" and "GENERAL LESSONS" sections |
| TBOT-05 | /lessons shows learned lessons | New bot handler with filter syntax (D-16, D-17). Follows scorecard handler pattern |
| REPT-05 | Lessons applied today in daily report | Per-asset lessons display in signal cards (D-19, D-20). Uses `lessons_applied` JSONB from DailyDecision |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy[asyncio] | 2.0.48+ | ORM for lessons table + queries | Already used for all DB access in project |
| Alembic | 1.18.4+ | Schema migration for lessons table | All schema changes use Alembic |
| litellm | 1.82.6+ | LLM calls for reflect analysis | Existing `llm_completion()` wrapper |
| pydantic-settings | 2.13.1+ | Config for new thresholds | Existing `Settings` class pattern |
| python-telegram-bot | (existing) | /lessons handler | Bot handlers use PTB |
| structlog | 25.5.0+ | Logging in reflect stage | Project standard |

### Supporting
No new dependencies required. Phase 7 uses only existing libraries.

**Installation:** No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── data/
│   └── reflect.py          # reflect_stage StageFunc
├── db/
│   ├── models.py            # + Lesson model
│   ├── lesson_repo.py       # LessonRepository (new)
│   └── migrations/versions/
│       └── 006_lessons.py   # Alembic migration
├── llm/
│   └── prompts.py           # + reflect prompts, lesson injection
├── bot/handlers/
│   └── lessons.py           # /lessons handler (new)
└── report/
    └── formatter.py         # + lesson formatting functions
```

### Pattern 1: Reflect Stage as StageFunc
**What:** `reflect_stage(session, asset)` follows the established per-asset stage pattern. Runs AFTER evaluate in the pipeline stage order.
**When to use:** Always -- this is the locked decision (D-01).
**Key detail:** The reflect stage is LLM-heavy (1+ calls per qualifying decision per asset). Must have its own timeout setting in config (e.g., `timeout_reflect: int = 120`). Error isolation: catch all exceptions, log, never crash pipeline.

```python
# Registration in src/pipeline/main.py
stage_funcs = {
    "evaluate": evaluate_stage,
    "reflect": reflect_stage,   # NEW: after evaluate, before fetch
    "fetch": ingest_stage,
    "analyze": analyze_stage,
    "decide": decide_stage,
}
```

### Pattern 2: LessonRepository Following Existing Repo Pattern
**What:** Singleton repository class with UPSERT methods, matching `evaluation_repo` and `decision_repo` patterns.
**Key methods:**
- `upsert_lesson()` -- insert or update (for dedup merge)
- `get_valid_lessons()` -- query `still_valid=True` with optional filters
- `get_relevant_lessons()` -- multi-factor scored query for injection
- `increment_times_applied()` -- bump count when lesson is used in a decision
- `invalidate_underperforming()` -- D-09 performance check
- `get_lessons_for_display()` -- for /lessons command

```python
# Singleton pattern matching existing repos
lesson_repo = LessonRepository()
```

### Pattern 3: Lesson Table Schema
**What:** Extends the ARCHITECTURE.md base schema with D-08 tagging dimensions.

```sql
CREATE TABLE lessons (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    asset_type VARCHAR(10),               -- "stock", "crypto", or "all"
    engine_tags JSONB,                    -- ["technical", "quantitative"]
    topic VARCHAR(30),                    -- "momentum", "volatility", etc.
    lesson TEXT NOT NULL,
    source_decision_id INTEGER REFERENCES daily_decisions(id),
    times_observed INTEGER DEFAULT 1,     -- how many times pattern seen
    times_applied INTEGER DEFAULT 0,      -- how many times injected
    times_correct INTEGER DEFAULT 0,      -- correct when applied
    confidence_tier VARCHAR(15) DEFAULT 'hypothesis',  -- hypothesis/pattern/rule
    still_valid BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lessons_valid_type ON lessons(still_valid, asset_type);
CREATE INDEX idx_lessons_tier ON lessons(confidence_tier) WHERE still_valid = TRUE;
```

**Tier logic (derived from success criteria #2 -- 10 observations minimum):**
- `hypothesis`: times_observed < 10
- `pattern`: times_observed >= 10 AND times_observed < 30
- `rule`: times_observed >= 30

Only `pattern` and `rule` tier lessons are injected into the decision prompt (success criteria #2 says "does not become active until observed at least 10 times").

### Pattern 4: Two-Pass LLM Analysis in Reflect Stage
**What:** Per-asset analysis first, then batch cross-cutting analysis.
**Flow:**
1. For each asset: query evaluations that matured today across all windows
2. Filter to qualifying decisions (wrong OR correct with confidence < 0.4)
3. For each qualifying decision: call LLM with decision context + signals + evaluation result
4. After all per-asset analyses: batch call with all analyses for cross-cutting lessons
5. For each extracted lesson: dedup check against existing valid lessons via LLM
6. Run performance invalidation check (D-09)

### Pattern 5: Lesson Injection into Decision Prompt
**What:** Extend `build_decision_prompt()` to accept lessons and format them in sections.
**Key detail:** The prompt builder currently takes `(asset, signals, contradictions)`. Add a `lessons` parameter. Format as:

```
ASSET-SPECIFIC LESSONS:
1. [lesson text] (engine: technical, accuracy: 72% over 15 applications)
2. ...

GENERAL LESSONS:
1. [lesson text] (engine: quantitative, accuracy: 65% over 20 applications)
```

### Anti-Patterns to Avoid
- **Storing lesson text in lessons_applied without IDs:** D-15 requires BOTH IDs and text. The IDs enable tracking, the text enables display without joins.
- **Running reflect before evaluate:** D-01 is explicit -- evaluate stays fast/deterministic, reflect is separate.
- **Injecting hypothesis-tier lessons:** Success criteria #2 requires 10 observations minimum. Only pattern/rule tiers should be injected.
- **Single LLM call for all assets:** D-04 specifies per-asset analysis. Each qualifying decision gets its own LLM call for detailed analysis.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Lesson deduplication | String similarity matching | LLM-based dedup (D-10) | Semantic similarity requires understanding, not string distance |
| Lesson relevance scoring | Simple SQL ORDER BY | Multi-factor composite score (D-13) | Recency, accuracy, asset-type match, engine relevance all matter |
| Performance tracking | External analytics | In-table counters (times_applied, times_correct) | Simple, no additional dependencies, updated atomically |
| Tier promotion | Manual thresholds in app code | DB-computed from times_observed | Single source of truth, queryable |

## Common Pitfalls

### Pitfall 1: LLM Token Budget Explosion in Reflect Stage
**What goes wrong:** Each qualifying decision triggers an LLM call. With 6 assets and 4 windows, worst case is 24 LLM calls per reflect run.
**Why it happens:** All decisions could be wrong on a bad day.
**How to avoid:** Cap per-asset analysis calls (e.g., max 3 per asset, prioritize most recent windows). Use GPT-4o-mini which is cheap. Log token usage.
**Warning signs:** Reflect stage consistently hitting timeout.

### Pitfall 2: Dedup Prompt Growing Unbounded
**What goes wrong:** D-10 includes existing valid lessons in the dedup prompt. As lessons accumulate, this prompt grows.
**Why it happens:** No limit on existing lessons shown for dedup.
**How to avoid:** Cap dedup context to top 30 most relevant existing lessons (by asset_type + engine_tags match). Summarize lesson text to first 100 chars if needed.
**Warning signs:** Dedup LLM call approaching token limits.

### Pitfall 3: Circular Lesson Application Tracking
**What goes wrong:** Lesson accuracy tracking counts times_correct, but determining "correct" requires evaluating decisions that applied the lesson -- which happens days later.
**Why it happens:** Evaluation is delayed (24h minimum).
**How to avoid:** Update lesson accuracy during reflect stage, not during decide stage. When evaluating a decision, check its `lessons_applied` JSONB, and for each lesson ID, update `times_correct` if the decision was correct.
**Warning signs:** `times_correct` never incrementing despite lessons being applied.

### Pitfall 4: Reflect Stage Processing Already-Reflected Decisions
**What goes wrong:** Without idempotency tracking, the same decision could be analyzed multiple times across pipeline reruns.
**Why it happens:** Reflect stage queries by matured window dates, which don't change between reruns.
**How to avoid:** Store per-asset LLM analysis results (consider an `evaluations.analysis` column or a separate `reflection_results` table). Check for existing analysis before calling LLM. Or add a `reflected_at` timestamp to evaluations.
**Warning signs:** Duplicate lessons being extracted.

### Pitfall 5: Bot Process Importing Pipeline Modules
**What goes wrong:** `/lessons` handler must read from `lessons` table but MUST NOT import from `src/pipeline` or `src/llm`.
**Why it happens:** Convenience -- wanting to reuse reflect stage logic in bot.
**How to avoid:** `LessonRepository` lives in `src/db/` (importable by both processes). Formatter functions live in `src/report/`. `/lessons` handler only uses these two.
**Warning signs:** Import errors in bot process.

### Pitfall 6: JSON Mode Output Schema Mismatch
**What goes wrong:** LLM returns JSON that doesn't match expected schema for per-asset analysis.
**Why it happens:** GPT-4o-mini may omit fields or use different key names.
**How to avoid:** Validate response with required keys check (same pattern as `_parse_llm_response` in decide.py). Provide explicit field list in prompt. Have a fallback that logs but doesn't crash.
**Warning signs:** Analysis records with null/empty fields.

## Code Examples

### Lesson Model (for models.py)
```python
class Lesson(Base):
    """Learned lesson from self-evaluation feedback loop."""

    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    asset_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    engine_tags: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(30), nullable=True)
    lesson: Mapped[str] = mapped_column(Text, nullable=False)
    source_decision_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("daily_decisions.id"), nullable=True
    )
    times_observed: Mapped[int] = mapped_column(Integer, default=1)
    times_applied: Mapped[int] = mapped_column(Integer, default=0)
    times_correct: Mapped[int] = mapped_column(Integer, default=0)
    confidence_tier: Mapped[str] = mapped_column(
        String(15), nullable=False, default="hypothesis"
    )
    still_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

### Multi-Factor Lesson Scoring (for lesson_repo.py)
```python
def _score_lesson(
    lesson: Lesson,
    asset_type: str,
    engine_categories: set[str],
    now: datetime,
) -> float:
    """Score a lesson for relevance to a specific decision context.

    Composite of: recency, accuracy rate, asset-type match, engine relevance.
    """
    # Recency: decay over 30 days
    age_days = (now.date() - lesson.date).days
    recency = max(0.0, 1.0 - (age_days / 90))  # linear decay over 90 days

    # Accuracy rate
    if lesson.times_applied > 0:
        accuracy = lesson.times_correct / lesson.times_applied
    else:
        accuracy = 0.5  # neutral prior

    # Asset-type match: 1.0 for exact or "all", 0.3 for mismatch
    if lesson.asset_type == asset_type or lesson.asset_type == "all":
        type_match = 1.0
    else:
        type_match = 0.3

    # Engine relevance: fraction of lesson's engine_tags present in current signals
    if lesson.engine_tags and engine_categories:
        overlap = len(set(lesson.engine_tags) & engine_categories)
        total = len(lesson.engine_tags)
        engine_match = overlap / total if total > 0 else 0.5
    else:
        engine_match = 0.5

    # Weighted composite
    return (
        0.25 * recency
        + 0.30 * accuracy
        + 0.25 * type_match
        + 0.20 * engine_match
    )
```

### Reflect Stage Skeleton (for src/data/reflect.py)
```python
async def reflect_stage(session: AsyncSession, asset: Asset) -> None:
    """Reflect on past decisions: analyze mistakes, extract lessons.

    Runs AFTER evaluate_stage. Analyzes qualifying decisions at all
    matured evaluation windows for this asset.
    """
    log = logger.bind(asset=asset.symbol, asset_id=asset.id)

    try:
        today = date.today()
        analyses: list[dict] = []

        for window_name, window_delta in EVAL_WINDOWS:
            target_date = today - window_delta
            # Get decision + evaluation for this window
            decision = await decision_repo.get_decision(session, asset.id, target_date)
            if decision is None:
                continue
            evaluation = await evaluation_repo.get_evaluation(
                session, decision.id, window_name
            )
            if evaluation is None:
                continue

            # D-03: Only analyze mistakes and surprising wins
            if evaluation.was_correct and float(decision.confidence or 1.0) >= 0.4:
                continue

            # Per-asset LLM analysis (D-04, D-05)
            analysis = await _analyze_decision(session, asset, decision, evaluation, window_name)
            if analysis:
                analyses.append(analysis)
                # Extract and dedup lesson
                await _extract_and_store_lesson(session, analysis, asset, decision)

        # Performance invalidation check (D-09)
        await lesson_repo.invalidate_underperforming(session)

        if analyses:
            log.info("reflect_complete", analyses=len(analyses))
        else:
            log.debug("reflect_no_qualifying_decisions")

    except Exception:
        log.exception("reflect_stage_error")
        # Error isolation: never crash pipeline
```

### Lesson Display Format (for /lessons command)
```python
def format_lessons_message(
    recently_learned: list[dict],
    top_lessons: list[dict],
    asset_filter: str | None = None,
    engine_filter: str | None = None,
) -> str:
    """Format /lessons response with two sections."""
    lines: list[str] = []

    # Title
    filters = []
    if asset_filter:
        filters.append(asset_filter)
    if engine_filter:
        filters.append(engine_filter)
    filter_str = f" ({', '.join(filters)})" if filters else ""
    lines.append(f"<b>Lessons{filter_str}</b>")
    lines.append("")

    # Recently Learned section
    if recently_learned:
        lines.append("<b>Recently Learned (7d)</b>")
        for item in recently_learned:
            tier_emoji = {"hypothesis": "?", "pattern": "~", "rule": "!"}
            emoji = tier_emoji.get(item["tier"], "?")
            lines.append(
                f"[{emoji}] {html.escape(item['lesson'][:120])}"
                f"\n    {item['tier']} | seen {item['times_observed']}x"
            )
        lines.append("")

    # Top Lessons section
    if top_lessons:
        lines.append("<b>Top Lessons (by accuracy)</b>")
        for item in top_lessons:
            accuracy = round(item["accuracy"] * 100) if item["accuracy"] else 0
            lines.append(
                f"[!] {html.escape(item['lesson'][:120])}"
                f"\n    {item['tier']} | {accuracy}% accuracy over {item['times_applied']} uses"
            )

    if not recently_learned and not top_lessons:
        lines.append("No lessons learned yet. Check back after the pipeline runs for a few days.")

    return "\n".join(lines)
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio (auto mode) |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVAL-02 | Reflect stage calls LLM for qualifying decisions, produces analysis | unit | `pytest tests/test_data/test_reflect.py -x` | Wave 0 |
| EVAL-03 | Lessons extracted and stored with dedup | unit | `pytest tests/test_data/test_reflect.py::TestLessonExtraction -x` | Wave 0 |
| EVAL-04 | Relevant lessons injected into decide prompt | unit | `pytest tests/test_data/test_decide.py::TestLessonInjection -x` | Wave 0 |
| LLM-04 | Decision prompt includes lesson sections | unit | `pytest tests/test_llm/test_prompts.py::TestLessonPrompt -x` | Wave 0 |
| TBOT-05 | /lessons command returns formatted lessons | unit | `pytest tests/test_bot/test_lessons.py -x` | Wave 0 |
| REPT-05 | Daily report includes lessons applied | unit | `pytest tests/test_report/test_formatter.py::TestLessonsSection -x` | Wave 0 |

### Supplementary Tests
| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| Lesson model schema (columns, constraints, FKs) | unit | `pytest tests/test_db/test_models.py::TestLessonModel -x` | Wave 0 |
| LessonRepository CRUD operations | unit | `pytest tests/test_db/test_lesson_repo.py -x` | Wave 0 |
| Tier promotion logic (hypothesis -> pattern -> rule) | unit | `pytest tests/test_data/test_reflect.py::TestTierPromotion -x` | Wave 0 |
| Performance invalidation (D-09) | unit | `pytest tests/test_db/test_lesson_repo.py::TestInvalidation -x` | Wave 0 |
| Multi-factor lesson scoring | unit | `pytest tests/test_db/test_lesson_repo.py::TestLessonScoring -x` | Wave 0 |
| Reflect stage error isolation | unit | `pytest tests/test_data/test_reflect.py::TestErrorIsolation -x` | Wave 0 |
| Reflect stage skips already-reflected decisions | unit | `pytest tests/test_data/test_reflect.py::TestIdempotency -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_data/test_reflect.py` -- covers EVAL-02, EVAL-03, tier promotion, error isolation, idempotency
- [ ] `tests/test_db/test_lesson_repo.py` -- covers lesson CRUD, scoring, invalidation
- [ ] `tests/test_llm/test_prompts.py` (extend) -- covers LLM-04 lesson prompt sections
- [ ] `tests/test_data/test_decide.py` (extend) -- covers EVAL-04 lesson injection
- [ ] `tests/test_bot/test_lessons.py` -- covers TBOT-05
- [ ] `tests/test_report/test_formatter.py` (extend) -- covers REPT-05

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static prompts | Dynamic lesson injection | This phase | Decisions improve over time |
| No feedback loop | Reflect -> Extract -> Inject cycle | This phase | System learns from mistakes |
| Manual lesson curation | LLM-based extraction + dedup | This phase | Zero human intervention |

## Open Questions

1. **Batch cross-cutting pass timing**
   - What we know: D-06 says batch pass receives "all of yesterday's results." But reflect_stage is per-asset (StageFunc pattern).
   - What's unclear: Where does the batch pass run? It needs all per-asset analyses aggregated.
   - Recommendation: Run per-asset analysis in `reflect_stage` per-asset calls. Store analyses in a temporary structure (in-memory or in evaluations.analysis column). Run batch cross-cutting as a post-reflect hook similar to how report runs post-pipeline. Or: run it in the last asset's reflect call if all assets are processed.

2. **Idempotency for reflect stage**
   - What we know: Evaluate stage checks `existing = await evaluation_repo.get_evaluation()` to skip already-evaluated decisions.
   - What's unclear: Where to store the "already reflected" flag.
   - Recommendation: Add a `reflected_at` nullable timestamp column to the `evaluations` table (via the same migration). Check it before calling LLM. Alternatively, store analysis results in a separate column on evaluations.

3. **Lesson accuracy computation timing**
   - What we know: D-09 checks accuracy after 5+ applications. But accuracy requires knowing if decisions that applied the lesson were correct.
   - What's unclear: The gap between applying a lesson (during decide) and knowing if it was correct (during evaluate, 1-30 days later).
   - Recommendation: During reflect stage, when processing evaluations, check each evaluated decision's `lessons_applied` JSONB. For each lesson ID found, update `times_correct` on the lesson if `was_correct = true`. This piggybacks on the existing evaluate -> reflect flow.

## Sources

### Primary (HIGH confidence)
- `src/db/models.py` -- Existing ORM models, DailyDecision.lessons_applied already exists
- `src/data/evaluate.py` -- Evaluate stage implementation, pattern for reflect stage
- `src/data/decide.py` -- Decide stage, prompt building, LLM call pattern
- `src/llm/prompts.py` -- Current prompt builder to extend
- `src/llm/client.py` -- llm_completion() with JSON mode
- `src/db/evaluation_repo.py` -- Repository pattern to follow
- `src/db/decision_repo.py` -- Repository pattern to follow
- `src/pipeline/main.py` -- Stage registration pattern
- `src/bot/handlers/scorecard.py` -- Bot handler pattern for /lessons
- `src/report/formatter.py` -- Formatter pattern for lessons display
- `plan/ARCHITECTURE.md` -- Lessons table schema, prompt builder step 4, self-evaluation flow

### Secondary (MEDIUM confidence)
- `07-CONTEXT.md` -- All 20 locked decisions, canonical references

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns established in prior phases
- Architecture: HIGH -- StageFunc, repository, formatter, handler patterns all proven by phases 3-6
- Pitfalls: HIGH -- derived from direct analysis of existing code patterns and known constraints
- Lesson scoring/injection: MEDIUM -- multi-factor scoring weights are Claude's discretion, will need tuning

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- no external dependency changes expected)
