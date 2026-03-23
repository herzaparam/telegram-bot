---
phase: 02-data-layer
plan: 02
subsystem: data
tags: [yfinance, ccxt, coingecko, asyncio, tenacity, staleness, backfill, ingest]

# Dependency graph
requires:
  - phase: 02-data-layer/01
    provides: BaseFetcher ABC, OHLCVRow dataclass, validate_rows, upsert_prices, get_latest_date, BackoffState model
  - phase: 01-foundation
    provides: PipelineRunner, StageFunc, SourceCriticalError, handle_source_failure, Asset model, Settings
provides:
  - IDXStockFetcher for .JK tickers via yfinance with executor wrapping and 3x retry
  - CryptoFetcher via ccxt/Binance with CoinGecko OHLC fallback
  - Staleness detection (IDX last trading day, crypto 24h window)
  - AlertCollector for DATA_STALE and FETCH_FAILURE batching
  - ingest_stage matching StageFunc signature with delta-fetch, weekly re-fetch, adaptive backoff
  - Backfill CLI with --from/--to flags and Semaphore(5) concurrency
affects: [03-technical-engines, 05-telegram, 10-evaluation]

# Tech tracking
tech-stack:
  added: [yfinance, ccxt, pandas]
  patterns: [executor-wrapping for sync libs, tenacity retry with exponential backoff, adaptive backoff persistence, weekly correction re-fetch]

key-files:
  created:
    - src/data/idx_stocks.py
    - src/data/crypto.py
    - src/data/staleness.py
    - src/data/alerts.py
    - src/data/ingest.py
    - src/data/backfill.py
    - src/data/__main__.py
    - tests/test_data/test_idx_fetcher.py
    - tests/test_data/test_crypto_fetcher.py
    - tests/test_data/test_staleness.py
    - tests/test_data/test_ingest.py
  modified:
    - pyproject.toml
    - tests/test_data/conftest.py
    - uv.lock

key-decisions:
  - "tenacity wait patched to wait_none() in tests to avoid multi-second retry delays"
  - "CoinGecko OHLC endpoint used for fallback (no volume data, tagged source=coingecko)"
  - "Monday detection for weekly re-fetch trigger (simplest approach per plan)"

patterns-established:
  - "Executor wrapping: sync libraries (yfinance) run via asyncio.get_event_loop().run_in_executor()"
  - "Adaptive backoff: BackoffState read before fetch, reset on success, doubled on failure (cap 300s)"
  - "Source tagging: every OHLCVRow tagged with source column for data provenance"

requirements-completed: [DATA-02, DATA-03]

# Metrics
duration: 17min
completed: 2026-03-23
---

# Phase 02 Plan 02: Data Fetchers and Ingest Pipeline Summary

**IDX and crypto fetchers with yfinance/ccxt/CoinGecko, staleness detection, adaptive backoff ingest stage, and backfill CLI**

## Performance

- **Duration:** 17 min
- **Started:** 2026-03-23T12:58:10Z
- **Completed:** 2026-03-23T13:15:10Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- IDXStockFetcher wraps yfinance in executor with +1 day end-date fix and 3x tenacity retry
- CryptoFetcher uses ccxt/Binance with automatic CoinGecko OHLC fallback, always closes exchange
- Ingest stage integrates with PipelineRunner as StageFunc, supports delta-fetch, 2-year auto-backfill, weekly 30-day correction re-fetch, and adaptive backoff from BackoffState table
- Staleness detection handles IDX trading day logic (weekday walk-back) and crypto 24h window
- AlertCollector batches DATA_STALE and FETCH_FAILURE alerts for future Telegram integration
- Backfill CLI with --from/--to/--type/--assets flags and Semaphore(5) concurrency
- 57 data layer tests pass, 117 total tests pass (excluding pre-existing config test)

## Task Commits

Each task was committed atomically:

1. **Task 1: IDX stock fetcher and crypto fetcher with fallback** - `02dfa66` (feat)
2. **Task 2: Staleness detection, alerts, ingest stage, and backfill CLI** - `a67209d` (feat)

**Plan metadata:** TBD (docs: complete plan)

_Note: TDD tasks had test-first approach with RED/GREEN phases in each commit._

## Files Created/Modified
- `src/data/idx_stocks.py` - IDXStockFetcher using yfinance with executor wrapping and tenacity retry
- `src/data/crypto.py` - CryptoFetcher with ccxt/Binance primary and CoinGecko OHLC fallback
- `src/data/staleness.py` - check_staleness for IDX (last trading day) and crypto (24h)
- `src/data/alerts.py` - AlertCollector batching DATA_STALE and FETCH_FAILURE
- `src/data/ingest.py` - ingest_stage with delta-fetch, weekly re-fetch, adaptive backoff
- `src/data/backfill.py` - CLI with --from/--to/--type/--assets and Semaphore(5)
- `src/data/__main__.py` - Enables `python -m src.data.backfill` invocation
- `pyproject.toml` - Added yfinance, ccxt, pandas dependencies
- `tests/test_data/conftest.py` - Added mock_yfinance_df, mock_ccxt_ohlcv, mock_coingecko_ohlc_response fixtures
- `tests/test_data/test_idx_fetcher.py` - 5 tests for IDX fetcher
- `tests/test_data/test_crypto_fetcher.py` - 6 tests for crypto fetcher
- `tests/test_data/test_staleness.py` - 8 tests for staleness detection
- `tests/test_data/test_ingest.py` - 14 tests for ingest stage + backfill CLI

## Decisions Made
- Used tenacity wait_none() patching in tests to avoid multi-second retry backoff delays
- CoinGecko /coins/{id}/ohlc endpoint chosen for fallback (returns OHLC but no volume; volume set to 0 with source="coingecko" tag)
- Monday weekday detection used for weekly re-fetch trigger (simplest reliable approach)
- Ruff auto-fixed UTC alias (datetime.UTC vs timezone.utc) and removed unused imports

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed infinite pagination loop in retry test**
- **Found during:** Task 1 (crypto fetcher tests)
- **Issue:** Mock ccxt fetch_ohlcv returned same data on every call after retries succeeded, causing infinite pagination
- **Fix:** Made mock return data once then empty list to stop pagination loop
- **Files modified:** tests/test_data/test_crypto_fetcher.py
- **Verification:** Test runs in < 1 second
- **Committed in:** a67209d

**2. [Rule 3 - Blocking] Fixed tenacity exponential backoff causing slow tests**
- **Found during:** Task 1 (fetcher tests)
- **Issue:** Retry tests waited 2-30 seconds per retry attempt due to exponential backoff
- **Fix:** Patched tenacity wait to wait_none() in test scope, restored after
- **Files modified:** tests/test_data/test_idx_fetcher.py, tests/test_data/test_crypto_fetcher.py
- **Verification:** All 12 fetcher tests complete in < 1 second
- **Committed in:** a67209d

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for test reliability. No scope creep.

## Issues Encountered
- Pre-existing test_config.py failure (telegram_chat_id reads from .env file) -- not caused by this plan's changes, documented but not fixed (out of scope)

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all modules are fully wired with no placeholder data.

## Next Phase Readiness
- Data fetchers complete and tested, ready for technical engine consumption (Phase 3)
- Ingest stage registered as StageFunc, ready for PipelineRunner integration
- AlertCollector ready for Telegram integration (Phase 5)
- Backfill CLI ready for initial 2-year history load on deployment

---
*Phase: 02-data-layer*
*Completed: 2026-03-23*
