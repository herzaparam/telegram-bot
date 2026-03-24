---
phase: 07-self-evaluation-feedback-loop
plan: 01
subsystem: database, pipeline
tags: [sqlalchemy, alembic, llm, lesson-extraction, dedup, reflect]

requires:
  - phase: 06-evaluation-scoring
    provides: Evaluation model, evaluation_repo, evaluate_stage, EVAL_WINDOWS
provides:
  - Lesson ORM model with tier promotion (hypothesis/pattern/rule)
  - LessonRepository with CRUD, scoring, invalidation, display methods
  - reflect_stage StageFunc with per-asset LLM analysis and dedup
  - run_batch_cross_cutting for cross-asset lesson extraction
  - Alembic migration 006 for lessons table
affects: [07-02-lesson-injection, decision-maker, report]

tech-stack:
  added: []
  patterns: [two-pass-llm-analysis, lesson-dedup-via-llm, tier-promotion-thresholds]

key-files:
  created:
    - src/db/lesson_repo.py
    - src/db/migrations/versions/006_lessons.py
    - src/data/reflect.py
    - tests/test_db/test_lesson_repo.py
    - tests/test_data/test_reflect.py
  modified:
    - src/db/models.py
    - src/config.py
    - src/pipeline/main.py

key-decisions:
  - "Lesson scoring uses four weighted factors: recency 0.25, accuracy 0.30, asset-type match 0.25, engine relevance 0.20"
  - "Tier promotion thresholds: hypothesis <10, pattern 10-29, rule >=30 observations"
  - "Reflect stage placed after evaluate in pipeline ordering (evaluate -> reflect -> fetch -> analyze -> decide)"
  - "Batch cross-cutting runs post-pipeline as a separate call, not as a per-asset stage"

patterns-established:
  - "Two-pass LLM analysis: per-asset analysis first, then dedup against existing lessons"
  - "Idempotency via source_decision_id check before analyzing a decision"
  - "Auto-invalidation of underperforming lessons (accuracy <40% after 5+ applications)"

requirements-completed: [EVAL-02, EVAL-03]

duration: 6min
completed: 2026-03-24
---

# Phase 7 Plan 1: Lesson Extraction Infrastructure Summary

**Lesson model with tier promotion, LessonRepository with multi-factor scoring, and reflect_stage with two-pass LLM analysis and dedup**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-24T16:09:03Z
- **Completed:** 2026-03-24T16:15:03Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Lesson ORM model with 14 columns including tier promotion, scoring counters, and JSONB engine_tags
- LessonRepository with upsert, merge, multi-factor scoring, tier promotion, invalidation, and display methods
- reflect_stage analyzing mistakes and surprising wins via per-asset LLM calls with JSON structured output
- Deduplication of new lessons against existing via second LLM call, with fallback to raw storage
- Batch cross-cutting pass extracting general lessons across all assets post-pipeline

## Task Commits

Each task was committed atomically:

1. **Task 1: Lesson model, migration, LessonRepository, and config** - `00e00d1` (feat)
2. **Task 2: Reflect stage with two-pass LLM analysis, dedup, and pipeline wiring** - `f955873` (feat)

## Files Created/Modified
- `src/db/models.py` - Added Lesson ORM model before SEED_ASSETS
- `src/db/migrations/versions/006_lessons.py` - Alembic migration creating lessons table with ix_lessons_valid_type and ix_lessons_tier indexes
- `src/db/lesson_repo.py` - LessonRepository with CRUD, multi-factor scoring, tier promotion, invalidation, display
- `src/config.py` - Added timeout_reflect=120 setting
- `src/data/reflect.py` - reflect_stage, _analyze_decision, _extract_and_store_lesson, run_batch_cross_cutting
- `src/pipeline/main.py` - Wired reflect_stage into stage_funcs and batch cross-cutting post-pipeline
- `tests/test_db/test_lesson_repo.py` - Model, scoring, tier promotion, invalidation tests (15 tests)
- `tests/test_data/test_reflect.py` - Analysis, extraction, qualifying filter, error isolation, idempotency tests (7 tests)

## Decisions Made
- Lesson scoring weights (recency 0.25, accuracy 0.30, asset match 0.25, engine relevance 0.20) follow D-13 spec
- Tier thresholds at 10 and 30 observations per D-09
- reflect_stage placed after evaluate, before fetch in pipeline ordering
- Batch cross-cutting runs as separate function post-pipeline (not a StageFunc) to aggregate across all assets
- Module-level _batch_analyses accumulator for collecting analyses across per-asset calls

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pre-existing test failure in `tests/test_data/test_report_stage.py` (AsyncMock coroutine issue with evaluation_repo.get_recent_evaluations) -- not related to this plan's changes, verified by running the same test on the unmodified branch.

## Known Stubs

None - all functionality is fully wired.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Lesson infrastructure complete, ready for Plan 02 (lesson injection into decisions)
- LessonRepository.get_relevant_lessons returns scored lessons filtered to pattern/rule tier
- LessonRepository.increment_times_applied ready for tracking which lessons were used in decisions

---
*Phase: 07-self-evaluation-feedback-loop*
*Completed: 2026-03-24*
