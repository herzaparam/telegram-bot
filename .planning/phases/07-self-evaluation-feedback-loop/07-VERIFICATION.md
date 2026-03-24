---
phase: 07-self-evaluation-feedback-loop
verified: 2026-03-24T16:45:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 7: Self-Evaluation Feedback Loop Verification Report

**Phase Goal:** Self-evaluation feedback loop — lesson extraction, injection into decisions, /lessons command, report integration
**Verified:** 2026-03-24T16:45:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                     | Status     | Evidence                                                                                   |
|----|-----------------------------------------------------------------------------------------------------------|------------|--------------------------------------------------------------------------------------------|
| 1  | After pipeline evaluate stage, reflect stage runs and analyzes qualifying decisions via LLM               | VERIFIED   | `src/pipeline/main.py` line 68 wires `"reflect": reflect_stage`; `reflect_stage` calls `llm_completion` per-asset  |
| 2  | Lessons are extracted from LLM analysis, deduplicated against existing lessons, and stored in the database | VERIFIED   | `_extract_and_store_lesson` in `reflect.py` runs second LLM pass for dedup, then calls `lesson_repo.upsert_lesson` or `merge_lesson`  |
| 3  | Lesson tiers promote from hypothesis to pattern to rule based on times_observed thresholds (10, 30)        | VERIFIED   | `_compute_tier()` in `lesson_repo.py` lines 303-309; `merge_lesson` applies it on each update  |
| 4  | Underperforming lessons are auto-invalidated after 5+ applications with accuracy below 40%                | VERIFIED   | `invalidate_underperforming` in `lesson_repo.py` lines 225-242; called in `reflect_stage` line 117  |
| 5  | Reflect stage is idempotent — rerunning does not re-analyze already-reflected evaluations                 | VERIFIED   | `reflect.py` lines 73-79: SELECT on `source_decision_id` before analysis; skips if row exists  |
| 6  | Active lessons (pattern/rule tier) are injected into the LLM decision prompt for each asset               | VERIFIED   | `decide.py` line 255 calls `get_relevant_lessons` (filters to `pattern`/`rule`); line 274 passes `lessons=lessons_for_prompt` to `build_decision_prompt` |
| 7  | The decide stage records which lessons were applied in the DailyDecision.lessons_applied JSONB            | VERIFIED   | `decide.py` lines 326-333: builds `lessons_applied_data` dict and calls `decision_repo.update_lessons_applied` + `lesson_repo.increment_times_applied` |
| 8  | /lessons command shows recently learned and top lessons with tier and accuracy stats                      | VERIFIED   | `src/bot/handlers/lessons.py` calls `lesson_repo.get_lessons_for_display`; `src/bot/main.py` line 48 registers `CommandHandler("lessons", lessons_handler)` |
| 9  | Daily report includes per-asset lessons applied section under each signal card                            | VERIFIED   | `src/data/report.py` lines 25, 264 import and call `format_lessons_applied(d.lessons_applied)` in asset card loop  |

**Score:** 9/9 truths verified

---

### Required Artifacts

#### Plan 01 Artifacts

| Artifact                                      | Expected                                        | Status   | Details                                                                                    |
|-----------------------------------------------|-------------------------------------------------|----------|--------------------------------------------------------------------------------------------|
| `src/db/models.py`                            | Lesson ORM model                                | VERIFIED | `class Lesson(Base)` at line 289 with all 14 required columns                             |
| `src/db/lesson_repo.py`                       | LessonRepository with CRUD, scoring, invalidation | VERIFIED | 334 lines; exports `lesson_repo` singleton at line 334; all 8 methods present             |
| `src/data/reflect.py`                         | reflect_stage StageFunc                         | VERIFIED | 394 lines; `reflect_stage`, `_analyze_decision`, `_extract_and_store_lesson`, `run_batch_cross_cutting` all present |
| `src/db/migrations/versions/006_lessons.py`   | Alembic migration for lessons table             | VERIFIED | Creates `lessons` table with `ix_lessons_valid_type` and `ix_lessons_tier` indexes        |
| `src/config.py`                               | timeout_reflect setting                         | VERIFIED | `timeout_reflect: int = 120` at line 46                                                   |

#### Plan 02 Artifacts

| Artifact                          | Expected                                         | Status   | Details                                                                                    |
|-----------------------------------|--------------------------------------------------|----------|--------------------------------------------------------------------------------------------|
| `src/llm/prompts.py`              | Extended prompt builder with lesson injection    | VERIFIED | `build_decision_prompt` accepts `lessons` param; `_format_engine_data` contains `"ASSET-SPECIFIC LESSONS:"` and `"GENERAL LESSONS:"`; `_SYSTEM_PROMPT` contains `"lessons from past mistakes"` |
| `src/data/decide.py`              | Modified decide_stage that queries and records lessons | VERIFIED | Imports `lesson_repo`; calls `get_relevant_lessons`, `update_lessons_applied`, `increment_times_applied` |
| `src/bot/handlers/lessons.py`     | /lessons command handler                         | VERIFIED | `async def lessons_handler` with auth check, filter parsing, and error handling            |
| `src/report/formatter.py`         | Lessons formatting functions                     | VERIFIED | `format_lessons_message` (line 376) and `format_lessons_applied` (line 429) both present  |

**Note on naming:** The PLAN artifact spec listed `contains: "format_lessons_section"` but the implemented function is `format_lessons_applied`. Both the formatter and report.py are consistently using `format_lessons_applied`. The goal (lessons section in daily report) is fully satisfied — this is a non-blocking name deviation documented in the SUMMARY.

---

### Key Link Verification

#### Plan 01 Key Links

| From                   | To                        | Via                                                     | Status   | Details                                                                    |
|------------------------|---------------------------|---------------------------------------------------------|----------|----------------------------------------------------------------------------|
| `src/data/reflect.py`  | `src/db/lesson_repo.py`   | `lesson_repo.upsert_lesson()`, `lesson_repo.invalidate_underperforming()` | WIRED    | `lesson_repo.` called 7 times in reflect.py at lines 112, 117, 233, 286, 294, 312, 378 |
| `src/data/reflect.py`  | `src/llm/client.py`       | `llm_completion()` for per-asset and batch analysis     | WIRED    | `llm_completion` called at lines 186, 270, 362                             |
| `src/pipeline/main.py` | `src/data/reflect.py`     | `stage_funcs["reflect"] = reflect_stage`                | WIRED    | Line 20 imports both; line 68 wires `"reflect": reflect_stage`; line 94 calls `run_batch_cross_cutting` |

#### Plan 02 Key Links

| From                         | To                        | Via                                              | Status   | Details                                                                    |
|------------------------------|---------------------------|--------------------------------------------------|----------|----------------------------------------------------------------------------|
| `src/data/decide.py`         | `src/db/lesson_repo.py`   | `lesson_repo.get_relevant_lessons()`             | WIRED    | Line 255 calls `lesson_repo.get_relevant_lessons(session, asset.asset_type, engine_categories, max_lessons=20)` |
| `src/data/decide.py`         | `src/llm/prompts.py`      | `build_decision_prompt()` with lessons parameter | WIRED    | Line 274: `build_decision_prompt(asset, signals, contradictions, lessons=lessons_for_prompt)` |
| `src/bot/handlers/lessons.py` | `src/db/lesson_repo.py`  | `lesson_repo.get_lessons_for_display()`          | WIRED    | Line 64: `data = await lesson_repo.get_lessons_for_display(session, ...)` |
| `src/data/report.py`         | `src/report/formatter.py` | `format_lessons_applied()` for daily report      | WIRED    | Line 25 imports `format_lessons_applied`; line 264 calls it in asset card loop |

---

### Data-Flow Trace (Level 4)

| Artifact                      | Data Variable       | Source                              | Produces Real Data | Status    |
|-------------------------------|---------------------|-------------------------------------|--------------------|-----------|
| `src/data/reflect.py`         | `evaluation`        | `evaluation_repo.get_evaluation()`  | Yes — DB query     | FLOWING   |
| `src/data/reflect.py`         | `analyses`          | `llm_completion()` JSON parse       | Yes — LLM output   | FLOWING   |
| `src/db/lesson_repo.py`       | lessons list        | `select(Lesson).where(...)` ORM queries | Yes — DB query  | FLOWING   |
| `src/data/decide.py`          | `relevant_lessons`  | `lesson_repo.get_relevant_lessons()` | Yes — DB query    | FLOWING   |
| `src/data/decide.py`          | `lessons_applied_data` | `{str(l.id): l.lesson for l in relevant_lessons}` | Yes — from DB result | FLOWING |
| `src/bot/handlers/lessons.py` | `data`              | `lesson_repo.get_lessons_for_display()` | Yes — DB query  | FLOWING   |
| `src/data/report.py`          | `lessons_text`      | `d.lessons_applied` from DailyDecision ORM | Yes — DB column | FLOWING |

---

### Behavioral Spot-Checks

| Behavior                                         | Command                                                              | Result       | Status  |
|--------------------------------------------------|----------------------------------------------------------------------|--------------|---------|
| reflect_stage exported from reflect.py           | `grep "^async def reflect_stage" src/data/reflect.py`               | Match found  | PASS    |
| lesson_repo singleton exported                   | `grep "^lesson_repo = " src/db/lesson_repo.py`                      | line 334     | PASS    |
| reflect wired into pipeline stage_funcs          | `grep '"reflect": reflect_stage' src/pipeline/main.py`              | line 68      | PASS    |
| /lessons registered in bot                       | `grep 'CommandHandler("lessons"' src/bot/main.py`                   | line 48      | PASS    |
| 128 phase-07-related tests pass                  | `.venv/bin/pytest <all 6 test files> -x -q`                         | 128 passed   | PASS    |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                               | Status    | Evidence                                                                 |
|-------------|-------------|-----------------------------------------------------------|-----------|--------------------------------------------------------------------------|
| EVAL-02     | 07-01       | LLM analyzes what went right/wrong and why                | SATISFIED | `_analyze_decision` in `reflect.py` calls `llm_completion` with structured JSON prompt; returns analysis dict with `analysis`, `missed_signals`, `overweighted_engines`, `underweighted_engines` |
| EVAL-03     | 07-01       | System extracts concrete lessons and stores in database   | SATISFIED | `_extract_and_store_lesson` deduplicates and calls `lesson_repo.upsert_lesson` or `merge_lesson`; all stored in `lessons` table |
| EVAL-04     | 07-02       | Lessons feed into future LLM decisions automatically      | SATISFIED | `decide_stage` in `decide.py` queries `get_relevant_lessons` (pattern/rule tier only), passes to `build_decision_prompt`, records applied lessons |
| LLM-04      | 07-02       | LLM applies lessons learned from past mistakes            | SATISFIED | `_format_engine_data` injects `ASSET-SPECIFIC LESSONS` and `GENERAL LESSONS` sections with accuracy and usage stats; `_SYSTEM_PROMPT` instructs LLM to weight them |
| TBOT-05     | 07-02       | /lessons shows learned lessons                            | SATISFIED | `lessons_handler` in `src/bot/handlers/lessons.py`; `CommandHandler("lessons", lessons_handler)` in `src/bot/main.py`; supports asset_type and engine filters |
| REPT-05     | 07-02       | Lessons applied today                                     | SATISFIED | `src/data/report.py` calls `format_lessons_applied(d.lessons_applied)` and appends to each asset card when lessons were used |

All 6 requirement IDs declared across both plans are satisfied. No orphaned requirements found in REQUIREMENTS.md mapping to Phase 7.

---

### Anti-Patterns Found

No anti-patterns found. Scan of all 8 modified/created source files produced:
- Zero TODO/FIXME/HACK/PLACEHOLDER comments
- No stub return patterns (`return []`, `return {}`, `return null`)
- No hardcoded empty data flowing to user-visible output
- No console.log-only handlers

---

### Human Verification Required

#### 1. LLM Lesson Quality

**Test:** Run the pipeline with `--stages reflect` against a real database with existing evaluations containing mistakes (was_correct=False). Inspect the lesson text in the `lessons` table.
**Expected:** Lessons are concrete and actionable (e.g., "RSI divergence ignored when volume confirmed the move"), not generic (e.g., "be more careful").
**Why human:** LLM output quality cannot be verified programmatically without a running database and real evaluation history.

#### 2. /lessons Telegram Output Formatting

**Test:** Send `/lessons`, `/lessons stock`, `/lessons crypto technical` to the bot.
**Expected:** Response renders properly in Telegram HTML mode: tier icons display, accuracy percentages show, the two sections ("Recently Learned" and "Top Lessons") are visually distinct.
**Why human:** Telegram HTML rendering requires a live bot to verify visual output.

#### 3. Deduplication LLM Pass

**Test:** Run reflect_stage twice with the same decision data (after removing the source_decision_id idempotency bypass). Check whether the second run merges or creates a duplicate lesson.
**Expected:** The dedup LLM call detects similarity and returns `action: "merge"` rather than creating a near-duplicate lesson.
**Why human:** Requires a live LLM call and database state to observe the merge behavior.

---

### Gaps Summary

No gaps. All 9 truths are verified, all artifacts exist at sufficient depth, all key links are wired end-to-end, all 6 requirements are satisfied, and 128 tests pass.

The one named deviation from plan (function named `format_lessons_applied` rather than `format_lessons_section`) is internally consistent across formatter and report.py and does not break the goal.

---

_Verified: 2026-03-24T16:45:00Z_
_Verifier: Claude (gsd-verifier)_
