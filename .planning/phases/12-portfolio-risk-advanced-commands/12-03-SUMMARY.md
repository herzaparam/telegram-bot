---
phase: 12-portfolio-risk-advanced-commands
plan: 03
subsystem: backtest-command
tags: [backtest, subprocess, telegram-bot, signal-replay, look-ahead-prevention]

requires:
  - phase: 12-portfolio-risk-advanced-commands
    provides: BacktestResult ORM model for caching results
  - phase: 04-llm-decision-maker
    provides: LLM verdict generation and deterministic fallback pattern
  - phase: 03-technical-engine-pipeline-shell
    provides: Engine analyze() pattern and Signal dataclass
provides:
  - src/data/backtest.py runnable module with run_backtest() and __main__ entry point
  - /backtest Telegram command with subprocess spawning and cached result path
affects: []

tech-stack:
  added: []
  patterns: [subprocess-for-two-process-boundary, cached-result-fast-path]

key-files:
  created:
    - src/data/backtest.py
    - src/bot/handlers/backtest.py
    - tests/test_data/test_backtest.py
    - tests/test_bot/test_backtest_handler.py
  modified:
    - src/db/models.py
    - src/bot/main.py

key-decisions:
  - "Subprocess spawning via asyncio.create_subprocess_exec for two-process boundary compliance"
  - "Deterministic fallback verdict when LLM unavailable (confidence-weighted score mapping)"
  - "10-minute timeout on subprocess with progress feedback to user"
  - "Cached result fast path: bot checks BacktestResult table before spawning subprocess"

patterns-established:
  - "Subprocess command pattern: bot spawns python -m module with JSON stdout for cross-process communication"
  - "Cached result fast path: check DB cache in handler before expensive subprocess call"

requirements-completed: [TBOT-08]

duration: 8min
completed: 2026-03-27
---

# Phase 12 Plan 03: Historical Signal Backtest Command Summary

**/backtest command replaying all engines + LLM verdict per historical day via subprocess, with look-ahead prevention, result caching, and progress feedback**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-27T10:51:06Z
- **Completed:** 2026-03-27T10:59:06Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Backtest engine (src/data/backtest.py) that replays engines + LLM for each historical trading day
- Look-ahead bias prevention: price data sliced to only include rows up to each test date
- Result caching via pg_insert with on_conflict_do_update on (asset_id, period, run_date)
- /backtest bot handler spawning subprocess with 10-minute timeout and progress message
- Cached result fast path: handler checks DB before spawning subprocess
- 19 tests total (11 engine + 8 handler) all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Backtest engine with subprocess entry point** - `942ccb3` (feat)
2. **Task 2: /backtest bot handler with subprocess spawning** - `aa822ca` (feat)

## Files Created/Modified
- `src/data/backtest.py` - Full backtest engine with run_backtest(), __main__ entry, LLM+deterministic fallback
- `src/bot/handlers/backtest.py` - /backtest Telegram command handler with subprocess spawning
- `src/bot/main.py` - Added CommandHandler("backtest") registration
- `src/db/models.py` - Added PortfolioRiskSnapshot and BacktestResult models
- `tests/test_data/test_backtest.py` - 11 tests for backtest engine
- `tests/test_bot/test_backtest_handler.py` - 8 tests for handler

## Decisions Made
- Subprocess spawning via asyncio.create_subprocess_exec to maintain two-process boundary (bot never imports src.pipeline or src.llm)
- Deterministic fallback verdict uses confidence-weighted average score mapped to thresholds (same pattern as Phase 4)
- 10-minute timeout on subprocess with kill and user notification
- Bot checks BacktestResult cache before spawning subprocess to avoid redundant computation
- 0.5s delay between LLM calls during backtest to avoid rate limits

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added PortfolioRiskSnapshot and BacktestResult models to models.py**
- **Found during:** Task 1
- **Issue:** Plan 01 outputs (ORM models) were created in a separate parallel worktree and not yet merged into this worktree
- **Fix:** Added both models directly to src/db/models.py following the exact schema from Plan 01
- **Files modified:** src/db/models.py
- **Verification:** Models import successfully, all 863 tests pass
- **Committed in:** 942ccb3 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required prerequisite model from Plan 01. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- /backtest command fully functional for 7d/30d/90d periods
- Results cached in backtest_results table for fast re-retrieval
- 863 total tests passing including 19 new backtest tests

## Self-Check: PASSED
