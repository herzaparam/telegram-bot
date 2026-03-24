---
phase: 05-telegram-bot-daily-delivery
plan: 01
subsystem: database, reporting
tags: [sqlalchemy, alembic, telegram, html-formatting, orm]

requires:
  - phase: 04-llm-decision-maker
    provides: DailyDecision model and LLM verdict pipeline
provides:
  - Watchlist and BotSettings ORM models
  - Alembic migration 004 for watchlist and bot_settings tables
  - Shared report formatter (format_asset_card, format_asset_detail, format_report_header, split_report, format_watchlist_message)
  - Config fields for webhook_base_url and telegram_webhook_secret
  - Test infrastructure for bot and report test suites
affects: [05-02, 05-03, telegram-bot, pipeline-report]

tech-stack:
  added: []
  patterns: [html-parse-mode-formatting, message-splitting-at-card-boundaries, verdict-emoji-mapping]

key-files:
  created:
    - src/db/migrations/versions/004_watchlist_bot_settings.py
    - src/report/__init__.py
    - src/report/formatter.py
    - tests/test_bot/__init__.py
    - tests/test_bot/conftest.py
    - tests/test_report/__init__.py
    - tests/test_report/test_formatter.py
  modified:
    - src/db/models.py
    - src/config.py

key-decisions:
  - "HTML parse_mode for Telegram messages (avoids MarkdownV2 escape issues with financial data per D-06)"
  - "Formatter in src/report/ shared by both bot and pipeline processes (not duplicated)"
  - "Reasoning truncation at word boundary with 100-char limit for compact cards"

patterns-established:
  - "Verdict emoji mapping: STRONG BUY=double green, BUY=green, HOLD=yellow, SELL=red, STRONG SELL=double red"
  - "Message splitting at asset card boundaries, never mid-card, with continuation headers"
  - "Score as signed float (+0.85), confidence as integer percentage (90%)"

requirements-completed: [WTCH-01, WTCH-02, WTCH-03, REPT-02, REPT-04]

duration: 4min
completed: 2026-03-24
---

# Phase 5 Plan 1: Foundation Models and Report Formatter Summary

**Watchlist/BotSettings ORM models with Alembic migration 004, shared HTML report formatter with emoji verdicts and 4096-char message splitting**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-24T09:40:18Z
- **Completed:** 2026-03-24T09:44:44Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Watchlist and BotSettings ORM models with proper ForeignKey constraints and unique keys
- Alembic migration 004 creating both tables with default delivery_time=06:30
- Shared report formatter producing HTML-formatted asset cards with emoji verdict badges
- Message splitting at card boundaries respecting Telegram's 4096-char limit
- 35 passing formatter tests covering all formatting behaviors

## Task Commits

Each task was committed atomically:

1. **Task 1: Watchlist + BotSettings models, migration, config, and test infrastructure** - `5dbef44` (feat)
2. **Task 2 RED: Failing tests for report formatter** - `0abb2fb` (test)
3. **Task 2 GREEN: Implement shared report formatter** - `3117ff8` (feat)

## Files Created/Modified
- `src/db/models.py` - Added Watchlist and BotSettings ORM models
- `src/db/migrations/versions/004_watchlist_bot_settings.py` - Migration creating watchlist and bot_settings tables
- `src/config.py` - Added webhook_base_url and telegram_webhook_secret fields
- `src/report/__init__.py` - Report package init
- `src/report/formatter.py` - Shared HTML formatter with asset cards, detail view, header, splitting, watchlist
- `tests/test_bot/__init__.py` - Bot test package init
- `tests/test_bot/conftest.py` - Shared fixtures (sample_assets, sample_decisions, mock_update, mock_context)
- `tests/test_report/__init__.py` - Report test package init
- `tests/test_report/test_formatter.py` - 35 tests for formatter module

## Decisions Made
- HTML parse_mode chosen over MarkdownV2 to avoid escape issues with financial data (per D-06 research)
- Formatter placed in src/report/ so both bot and pipeline processes can import without crossing process boundary
- Reasoning truncated at word boundary (not mid-word) for cleaner display

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Watchlist and BotSettings models ready for bot handler implementation (Plan 02)
- Report formatter ready for both /report command and pipeline report stage (Plans 02 and 03)
- Test fixtures ready for bot handler tests

---
*Phase: 05-telegram-bot-daily-delivery*
*Completed: 2026-03-24*
