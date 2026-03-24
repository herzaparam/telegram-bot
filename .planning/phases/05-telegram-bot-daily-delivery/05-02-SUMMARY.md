---
phase: 05-telegram-bot-daily-delivery
plan: 02
subsystem: bot, api
tags: [python-telegram-bot, fastapi, webhook, telegram, command-handlers]

requires:
  - phase: 05-telegram-bot-daily-delivery plan 01
    provides: Watchlist/BotSettings models, report formatter, Alembic migration
provides:
  - PTB Application mounted on FastAPI with webhook at /telegram/webhook
  - All 6 command handlers: start, add, remove, watchlist, report, settings
  - Chat ID whitelist authorization module
  - Symbol validation via yfinance (stocks) and ccxt (crypto) in executor threads
  - Bot handler test suite with 19 tests
affects: [05-telegram-bot-daily-delivery plan 03, pipeline report stage]

tech-stack:
  added: [python-telegram-bot>=22.7]
  patterns: [PTB webhook on FastAPI lifespan, run_in_executor for sync libs, chat ID whitelist auth]

key-files:
  created:
    - src/bot/auth.py
    - src/bot/handlers/__init__.py
    - src/bot/handlers/start.py
    - src/bot/handlers/watchlist.py
    - src/bot/handlers/report.py
    - src/bot/handlers/settings.py
    - tests/test_bot/conftest.py
    - tests/test_bot/test_auth.py
    - tests/test_bot/test_handlers.py
  modified:
    - src/bot/main.py
    - pyproject.toml
    - uv.lock

key-decisions:
  - "PTB Application with updater(None) and lifespan context manager for clean FastAPI integration"
  - "Module-level ptb_app global with None guard for graceful degradation when no token set"
  - "Lazy imports of yfinance and ccxt inside validation functions to avoid import overhead"
  - "run_in_executor for synchronous yfinance/ccxt calls to prevent event loop blocking"

patterns-established:
  - "Handler pattern: check is_authorized first, return silently if not"
  - "Session-per-handler: async with async_session_factory() for each DB operation"
  - "HTML parse_mode on all reply_text calls"

requirements-completed: [WTCH-01, WTCH-02, WTCH-03, TBOT-01, TBOT-02, TBOT-03, TBOT-07]

duration: 3min
completed: 2026-03-24
---

# Phase 05 Plan 02: Bot Command Handlers Summary

**PTB webhook bot on FastAPI with /start, /add (yfinance+ccxt validation), /remove, /watchlist, /report (full+single-asset), /settings (06-09 WIB range), and chat ID whitelist auth**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T09:47:37Z
- **Completed:** 2026-03-24T09:50:37Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- PTB Application mounted on FastAPI via lifespan with webhook at /telegram/webhook
- All 6 Telegram commands registered with whitelist authorization
- /add validates unknown symbols via yfinance (IDX stocks) and ccxt (crypto) in executor threads
- /report supports both full watchlist report with split_report and single-asset detail view
- /settings validates delivery time in 06:00-09:00 WIB range
- 19 tests covering auth, all handlers, and two-process boundary

## Task Commits

Each task was committed atomically:

1. **Task 1: PTB webhook integration, auth module, and all command handlers** - `39d9428` (feat)
2. **Task 2: Bot handler and auth tests** - `1e936e7` (test)

## Files Created/Modified
- `src/bot/main.py` - FastAPI app with PTB webhook integration via lifespan
- `src/bot/auth.py` - Chat ID whitelist authorization check
- `src/bot/handlers/__init__.py` - Handler package init
- `src/bot/handlers/start.py` - /start welcome message handler
- `src/bot/handlers/watchlist.py` - /add, /remove, /watchlist handlers with symbol validation
- `src/bot/handlers/report.py` - /report full and single-asset handler
- `src/bot/handlers/settings.py` - /settings delivery time handler
- `tests/test_bot/conftest.py` - Mock fixtures for Update, Context
- `tests/test_bot/test_auth.py` - 6 auth whitelist tests
- `tests/test_bot/test_handlers.py` - 13 handler + boundary tests
- `pyproject.toml` - Added python-telegram-bot dependency
- `uv.lock` - Lockfile update

## Decisions Made
- PTB Application with updater(None) for custom server mode, no PTB updater/webhook server
- Module-level ptb_app global initialized in lifespan, None-guarded in webhook endpoint
- Lazy imports of yfinance and ccxt inside validation functions to keep bot startup fast
- run_in_executor wraps synchronous yfinance/ccxt calls to prevent async event loop blocking
- Webhook secret token verified manually in FastAPI route (since PTB's own server isn't used)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

External services require manual configuration:
- `TELEGRAM_BOT_TOKEN` - from Telegram BotFather
- `TELEGRAM_CHAT_ID` - your chat ID (comma-separated for multiple users)
- `WEBHOOK_BASE_URL` - HTTPS domain for webhook
- `TELEGRAM_WEBHOOK_SECRET` - random string for webhook security

## Next Phase Readiness
- Bot command handlers complete, ready for Plan 03 (pipeline report stage + scheduled delivery)
- Report formatter from Plan 01 successfully integrated with /report handler
- Watchlist/BotSettings DB models from Plan 01 used by all handlers

## Self-Check: PASSED

All 10 created files verified present. Both commit hashes (39d9428, 1e936e7) confirmed in git log.

---
*Phase: 05-telegram-bot-daily-delivery*
*Completed: 2026-03-24*
