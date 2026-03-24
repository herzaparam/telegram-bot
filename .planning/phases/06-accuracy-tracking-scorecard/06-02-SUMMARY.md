---
phase: 06-accuracy-tracking-scorecard
plan: 02
subsystem: report, bot
tags: [telegram, formatter, scorecard, accuracy, html]

# Dependency graph
requires:
  - phase: 06-accuracy-tracking-scorecard
    provides: Evaluation model, EvaluationRepository with scorecard data methods
  - phase: 05-telegram-bot
    provides: Bot handler pattern, formatter module, split_report, is_authorized
provides:
  - format_scorecard_section for daily report scorecard prepend
  - format_scorecard_message for /scorecard command response
  - /scorecard bot command with period/asset arg parsing
  - Daily report integration with evaluation data
affects: [daily-report, telegram-bot]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "EvalDisplayItem frozen dataclass for evaluation display items"
    - "Scorecard section prepended to daily report with --- separator"
    - "Weekly trend computation with directional indicators (^/v/~)"
    - "Period/asset arg parsing with invalid-period detection"

key-files:
  created:
    - src/bot/handlers/scorecard.py
  modified:
    - src/report/formatter.py
    - src/data/report.py
    - src/bot/main.py
    - tests/test_report/test_formatter.py
    - tests/test_bot/test_handlers.py

key-decisions:
  - "EvalDisplayItem as frozen dataclass for type-safe evaluation display"
  - "Weekly trend uses 2pp threshold for directional indicators"
  - "Scorecard prepended to daily report header (before signals) with --- separator"
  - "Asset filter resolved via Watchlist join (only watchlisted assets valid)"

patterns-established:
  - "format_scorecard_section returns '' for empty state (D-18 skip pattern)"
  - "/scorecard handler follows report_handler pattern with is_authorized + async_session_factory"
  - "period_empty flag distinguishes absolute empty from period-scoped empty"

requirements-completed: [TBOT-04, REPT-01]

# Metrics
duration: 5min
completed: 2026-03-24
---

# Phase 6 Plan 2: Scorecard Report Summary

**Scorecard presentation layer with format_scorecard_section for daily reports, format_scorecard_message for /scorecard command, per-window results with emoji, buy-and-hold alpha comparison, and weekly trend indicators**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-24T10:47:15Z
- **Completed:** 2026-03-24T10:52:22Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- EvalDisplayItem dataclass and two scorecard formatting functions (section + message) with full emoji, window headers, trend line per UI-SPEC
- /scorecard bot command handler with period/asset arg parsing, error states, asset-filtered recent calls
- Daily report integration prepending scorecard section when evaluations exist (D-18 skip when empty)
- 82 total tests passing (61 formatter + 21 bot handlers including two-process boundary check)

## Task Commits

Each task was committed atomically:

1. **Task 1: Scorecard formatting functions and daily report integration** (TDD)
   - `11ba12e` test: add failing tests for scorecard formatting functions
   - `d16e144` feat: implement scorecard formatting and daily report integration
2. **Task 2: /scorecard bot command handler and registration**
   - `cfae8ba` feat: add /scorecard bot command handler and registration

## Files Created/Modified
- `src/report/formatter.py` - Added EvalDisplayItem, format_scorecard_section, format_scorecard_message, format_scorecard_error
- `src/data/report.py` - Added _build_scorecard_section helper, scorecard prepend in send_daily_report
- `src/bot/handlers/scorecard.py` - New /scorecard command handler with period/asset parsing
- `src/bot/main.py` - Registered scorecard_handler as CommandHandler
- `tests/test_report/test_formatter.py` - 38 new tests for scorecard formatting
- `tests/test_bot/test_handlers.py` - 9 new tests for scorecard handler

## Decisions Made
- EvalDisplayItem as frozen dataclass for type-safe evaluation display (matches Signal dataclass pattern from Phase 3)
- Weekly trend uses 2 percentage-point threshold for directional indicators (^ up, v down, ~ flat)
- Scorecard section prepended to daily report header with "---" text separator per UI-SPEC
- Asset filter resolved via Watchlist join to ensure only watchlisted assets are valid targets
- period_empty flag in format_scorecard_message distinguishes "no data at all" from "no data in this period"

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 6 (accuracy tracking and scorecard) is complete
- Evaluation engine (Plan 01) + scorecard presentation (Plan 02) form complete self-evaluation loop
- Users can see accuracy stats via /scorecard command and daily report scorecard section

## Self-Check: PASSED

---
*Phase: 06-accuracy-tracking-scorecard*
*Completed: 2026-03-24*
