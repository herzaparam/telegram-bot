---
phase: 06-accuracy-tracking-scorecard
plan: 01
subsystem: database, evaluation
tags: [sqlalchemy, alembic, evaluation, accuracy, idx-calendar, timescaledb]

# Dependency graph
requires:
  - phase: 04-llm-decision-maker
    provides: DailyDecision model, decision_repo
  - phase: 03-analysis-engines
    provides: SignalRecord model, signal_repo
  - phase: 02-data-ingestion
    provides: PriceHistory, PriceHistoryHourly, price_repo
provides:
  - Evaluation ORM model with multi-window tracking
  - AccuracyStats ORM model for pre-computed scorecard data
  - IDXHoliday ORM model with 2026 holiday seed data
  - EvaluationRepository with upsert, recompute, scorecard methods
  - evaluate_stage StageFunc wired as first pipeline stage
  - _classify_result with direction-based HOLD band classification
  - _get_next_trading_day for IDX trading calendar
affects: [06-02-scorecard-report, daily-report, telegram-bot]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-window evaluation (24h/3d/7d/30d) with maturity checks"
    - "Direction-based classification with asset-specific HOLD bands"
    - "Per-engine accuracy tracking via engine_results JSONB"
    - "IDX trading calendar with static holiday seed data"

key-files:
  created:
    - src/db/evaluation_repo.py
    - src/db/migrations/versions/005_evaluations.py
    - src/data/evaluate.py
    - tests/test_data/test_evaluate.py
    - tests/test_db/test_evaluation_repo.py
  modified:
    - src/db/models.py
    - src/config.py
    - src/pipeline/main.py
    - src/pipeline/runner.py

key-decisions:
  - "Evaluation uses SQLAlchemy ORM (not raw asyncpg) matching decision_repo pattern"
  - "HOLD bands scale per window: stock 2%/3%/5%/8%, crypto 5%/8%/12%/20%"
  - "Crypto 24h/3d uses hourly candle with 30min tolerance, 7d/30d falls back to daily"
  - "evaluate_stage catches all exceptions and logs without raising (pipeline error isolation)"
  - "accuracy_stats recomputed after each asset evaluation, not batched"

patterns-established:
  - "evaluate_stage as first pipeline stage (before fetch) for prior-day evaluation"
  - "HOLD_BANDS constant for asset-type-specific band thresholds"
  - "TDD flow: RED (failing tests) -> GREEN (implementation) for both tasks"

requirements-completed: [EVAL-01, EVAL-05]

# Metrics
duration: 6min
completed: 2026-03-24
---

# Phase 6 Plan 1: Evaluation Engine Summary

**Evaluation engine with direction-based classification, multi-window maturity tracking, IDX trading calendar, and per-engine accuracy stats via JSONB**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-24T10:38:13Z
- **Completed:** 2026-03-24T10:44:30Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Three new ORM models (Evaluation, AccuracyStats, IDXHoliday) with Alembic migration 005 seeding 19 IDX 2026 holidays
- EvaluationRepository with UPSERT evaluation, accuracy stats recomputation, scorecard data, engine ranking, and IDX holiday check
- evaluate_stage with _classify_result (BUY/SELL/HOLD direction-based with scaled bands), _get_next_trading_day (weekend+holiday skip), _get_evaluation_price (stock daily/crypto hourly+daily), _compute_engine_results (per-engine correctness tracking)
- evaluate_stage wired as first pipeline stage (before fetch) with timeout_evaluate=60s

## Task Commits

Each task was committed atomically:

1. **Task 1: DB models, migration, evaluation repository, and config** (TDD)
   - `5b936e7` test: add failing tests for evaluation repository and models
   - `41345c4` feat: add evaluation models, migration, repository, and config
2. **Task 2: Evaluate stage with classification logic and pipeline wiring** (TDD)
   - `2624391` test: add failing tests for evaluate stage
   - `0d6df0f` feat: implement evaluate_stage with classification and pipeline wiring

## Files Created/Modified
- `src/db/models.py` - Added Evaluation, AccuracyStats, IDXHoliday ORM models
- `src/db/migrations/versions/005_evaluations.py` - Alembic migration creating 3 tables + IDX 2026 holiday seed
- `src/db/evaluation_repo.py` - EvaluationRepository with all CRUD + stats methods
- `src/data/evaluate.py` - evaluate_stage StageFunc with classification and multi-window evaluation
- `src/config.py` - Added timeout_evaluate=60 setting
- `src/pipeline/main.py` - Wired evaluate_stage as first pipeline stage
- `src/pipeline/runner.py` - Added evaluate to default stages and timeout mapping
- `tests/test_db/test_evaluation_repo.py` - 17 repository tests
- `tests/test_data/test_evaluate.py` - 23 evaluate stage tests

## Decisions Made
- Evaluation uses SQLAlchemy ORM (not raw asyncpg) matching decision_repo pattern for consistency
- HOLD bands scale per window and asset type per plan spec (D-01/D-02/D-04)
- Crypto 24h/3d uses hourly candle lookup with 30-minute tolerance, 7d/30d falls back to daily close (hourly retention is 7 days)
- evaluate_stage catches all exceptions and logs without raising per pipeline error isolation pattern
- accuracy_stats recomputed immediately after each asset evaluation for freshness

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Evaluation data layer complete and wired into pipeline
- Plan 06-02 (scorecard report) can now read from evaluations and accuracy_stats tables
- REPT-01 and TBOT-04 have the foundation data to render accuracy scorecards

## Self-Check: PASSED

---
*Phase: 06-accuracy-tracking-scorecard*
*Completed: 2026-03-24*
