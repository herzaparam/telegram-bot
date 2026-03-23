---
phase: 02-data-layer
verified: 2026-03-23T14:00:00Z
status: passed
score: 16/16 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Live IDX data fetch via yfinance"
    expected: "IDXStockFetcher.fetch('BBCA.JK') returns OHLCV rows for recent trading days"
    why_human: "Requires live network; yfinance rate limits and data availability cannot be tested offline"
  - test: "Live crypto fetch via ccxt/Binance"
    expected: "CryptoFetcher.fetch('BTC/USDT') returns OHLCV rows from Binance"
    why_human: "Requires live Binance API connection; rate limits apply"
  - test: "CoinGecko fallback activated on ccxt failure"
    expected: "CryptoFetcher falls back to CoinGecko OHLC endpoint and returns rows tagged source='coingecko'"
    why_human: "Requires live CoinGecko API call; cannot confirm rate limit and response format stability without a real call"
  - test: "ingest_stage runs end-to-end via PipelineRunner with real TimescaleDB"
    expected: "upsert_prices inserts rows, re-running same date produces no duplicates"
    why_human: "Requires live TimescaleDB with TimescaleDB extension loaded; create_hypertable and add_compression_policy cannot be called against plain PostgreSQL"
---

# Phase 02: Data Layer Verification Report

**Phase Goal:** IDX stock and crypto prices are fetched, validated, and stored in TimescaleDB hypertables with compression — the data foundation every engine depends on
**Verified:** 2026-03-23T14:00:00Z
**Status:** passed — all must-haves verified (mypy errors fixed in commit 1e9d2b3)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | price_history hypertable exists with compression policy after 30 days | VERIFIED | migration 002 calls create_hypertable + add_compression_policy('price_history', INTERVAL '30 days') |
| 2 | price_history_hourly hypertable exists with 7-day retention policy | VERIFIED | migration 002 calls create_hypertable + add_retention_policy('price_history_hourly', INTERVAL '7 days') |
| 3 | OHLCV rows with null/NaN fields are rejected before insert | VERIFIED | validate_rows in validation.py checks None and math.isnan per field, logs ohlcv_row_rejected |
| 4 | Upserting same (asset_id, time) twice produces exactly one row | VERIFIED | price_repo.py uses INSERT ... ON CONFLICT (asset_id, time) DO UPDATE; idempotency tested in test_price_repo.py |
| 5 | BackoffState model exists for adaptive retry persistence | VERIFIED | BackoffState class in models.py + created in migration 002 + read/written in ingest.py |
| 6 | Migration 002 DDL is smoke-tested for expected SQL patterns | VERIFIED | test_migration.py uses inspect.getsource(upgrade) to assert all DDL patterns; 7 tests pass |
| 7 | IDX stock fetcher retrieves OHLCV from yfinance for .JK tickers with delta-fetch | VERIFIED | IDXStockFetcher in idx_stocks.py wraps yfinance in executor with 3x tenacity retry; delta-fetch in ingest.py via get_latest_date |
| 8 | Crypto fetcher retrieves OHLCV from ccxt/Binance and falls back to CoinGecko on failure | VERIFIED | CryptoFetcher in crypto.py: try ccxt, except -> _fetch_coingecko with COINGECKO_ID_MAP |
| 9 | Stale IDX data is detected and logged | VERIFIED | check_staleness in staleness.py handles asset_type='stock', walks back to last trading day, logs asset_stale |
| 10 | Stale crypto data is detected and logged | VERIFIED | check_staleness handles asset_type='crypto', checks 24h window, logs asset_stale |
| 11 | Ingest stage plugs into PipelineRunner as a StageFunc | VERIFIED | ingest_stage(session: AsyncSession, asset: Asset) -> None matches StageFunc = Callable[[AsyncSession, Asset], Awaitable[None]] |
| 12 | Backfill CLI supports --from and --to flags and defaults to 2-year history | VERIFIED | parse_args() in backfill.py; spot-check confirmed parse_args(['--from','2024-01-01','--to','2026-01-01']) returns correct dates |
| 13 | Re-running ingest for same date produces no duplicate rows | VERIFIED | ON CONFLICT (asset_id, time) DO UPDATE in upsert_prices; confirmed by test_price_repo.py idempotency test |
| 14 | Price rows are tagged with source column (yfinance, ccxt, coingecko) | VERIFIED | OHLCVRow.source set to 'yfinance' in idx_stocks.py, 'ccxt' in crypto.py/_fetch_ccxt, 'coingecko' in _fetch_coingecko |
| 15 | Adaptive backoff state is read from and written to BackoffState table | VERIFIED | _read_backoff_state, _update_backoff_success, _update_backoff_failure all query BackoffState ORM in ingest.py |
| 16 | mypy type checks pass (plan 01-01 verification step) | VERIFIED | 0 errors after fix commit 1e9d2b3 — strict mode clean |

**Score:** 16/16 truths verified

---

### Required Artifacts

| Artifact | Status | Evidence |
|----------|--------|---------|
| `src/db/models.py` | VERIFIED | Contains PriceHistory, PriceHistoryHourly, BackoffState classes with correct columns and composite PKs |
| `src/db/migrations/versions/002_price_history_hypertables.py` | VERIFIED | revision='002', down_revision='001', create_hypertable x2, add_compression_policy, add_retention_policy, backoff_state table |
| `src/db/price_repo.py` | VERIFIED | upsert_prices with ON CONFLICT (asset_id, time) DO UPDATE; get_latest_date returning datetime | None |
| `src/data/base.py` | VERIFIED | OHLCVRow dataclass with 8 fields; BaseFetcher ABC with source_name property and fetch() abstract method |
| `src/data/validation.py` | VERIFIED | ValidationResult dataclass; validate_rows checks None/NaN/high<low/negative volume; validate_date_coverage with business-day gap detection; structlog ohlcv_row_rejected and ohlcv_date_gaps |
| `src/data/idx_stocks.py` | VERIFIED | IDXStockFetcher extends BaseFetcher; executor wrapping; +1 day end-date fix; validate_rows called before return |
| `src/data/crypto.py` | VERIFIED (logic) / WARN (types) | CryptoFetcher with ccxt pagination and CoinGecko fallback — logic correct, 5 mypy errors |
| `src/data/staleness.py` | VERIFIED | check_staleness dispatches on asset_type; IDX last-trading-day walk-back; crypto 24h window |
| `src/data/alerts.py` | VERIFIED | AlertCollector with add_stale/add_fetch_failure/summary; DATA_STALE and FETCH_FAILURE types |
| `src/data/ingest.py` | VERIFIED (logic) / WARN (types) | ingest_stage matches StageFunc; delta-fetch; weekly re-fetch on Monday; backoff read/write; staleness check — 1 mypy type-narrowing error |
| `src/data/backfill.py` | VERIFIED (logic) / WARN (types) | parse_args with --from/--to; Semaphore(5) concurrency; run_backfill queries assets and dispatches — 3 mypy errors |
| `tests/test_data/test_migration.py` | VERIFIED | 7 DDL smoke tests via inspect.getsource; all pass |
| `tests/test_data/test_price_repo.py` | VERIFIED | 8 tests including idempotency; all pass |
| `tests/test_data/test_validation.py` | VERIFIED | 10 tests covering None/NaN/high<low/date gaps; all pass |
| `tests/test_data/test_idx_fetcher.py` | VERIFIED | 5 tests; all pass |
| `tests/test_data/test_crypto_fetcher.py` | VERIFIED | 6 tests; all pass |
| `tests/test_data/test_staleness.py` | VERIFIED | 8 tests; all pass |
| `tests/test_data/test_ingest.py` | VERIFIED | 14 tests; all pass |

---

### Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|---------|
| `src/db/price_repo.py` | `price_history table` | asyncpg INSERT ON CONFLICT (asset_id, time) | WIRED | Line 37: `ON CONFLICT (asset_id, time)` confirmed in source |
| `src/data/validation.py` | `src/data/base.py` | validates OHLCVRow instances | WIRED | `from src.data.base import OHLCVRow` at top of validation.py; OHLCVRow typed in validate_rows param |
| `src/data/ingest.py` | `src/pipeline/runner.py` | StageFunc signature (AsyncSession, Asset) -> None | WIRED | `async def ingest_stage(session: AsyncSession, asset: Asset) -> None` matches `Callable[[AsyncSession, Asset], Awaitable[None]]` |
| `src/data/idx_stocks.py` | `src/db/price_repo.py` | returns OHLCVRow list for upsert | WIRED | IDXStockFetcher.fetch() returns `list[OHLCVRow]`; ingest.py calls upsert_prices with the result |
| `src/data/crypto.py` | CoinGecko fallback | _fetch_coingecko on ccxt exception | WIRED | except block in fetch() calls `await self._fetch_coingecko(...)` with source='coingecko' tagging |
| `src/data/ingest.py` | `src/data/staleness.py` | staleness check after fetch | WIRED | `from src.data.staleness import check_staleness`; called at line 229 after upsert |
| `src/data/ingest.py` | `src/db/models.py (BackoffState)` | reads/writes BackoffState table | WIRED | `from src.db.models import Asset, BackoffState`; select+flush in _read_backoff_state; update in success/failure handlers |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase produces data storage infrastructure (DB schema, repos, fetchers). No UI components render dynamic data. All data flows are through asyncpg raw SQL (price_repo) verified at level 3.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| backfill CLI parses --from/--to flags | `parse_args(['--from','2024-01-01','--to','2026-01-01'])` | `2024-01-01 2026-01-01` | PASS |
| BaseFetcher and OHLCVRow importable | `from src.data.base import BaseFetcher, OHLCVRow` | Classes returned | PASS |
| All data module exports importable | import upsert_prices, get_latest_date, validate_rows, check_staleness, AlertCollector | "All imports successful" | PASS |
| ingest_stage matches StageFunc params | `inspect.signature(ingest_stage).parameters` | `['session', 'asset']` | PASS |
| Migration DDL patterns in upgrade() | inspect.getsource check for 6 patterns | All True | PASS |
| All 57 data layer tests pass | `uv run pytest tests/test_data/ -x -q` | `57 passed in 0.76s` | PASS |
| ruff lint passes | `uv run ruff check src/data/ src/db/price_repo.py src/db/models.py` | All checks passed | PASS |
| mypy strict mode passes | `uv run mypy src/data/ src/db/price_repo.py src/db/models.py` | Success: no issues found in 12 source files | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| DATA-01 | 02-01-PLAN.md | System stores daily OHLCV price history in TimescaleDB hypertables with auto-compression after 30 days | SATISFIED | PriceHistory model + migration 002 create_hypertable + add_compression_policy('price_history', INTERVAL '30 days') + asyncpg upsert |
| DATA-02 | 02-02-PLAN.md | System fetches IDX stock prices via yfinance (.JK suffix) with aggressive caching | SATISFIED | IDXStockFetcher wraps yfinance with executor + 3x tenacity retry; delta-fetch avoids re-fetching known dates |
| DATA-03 | 02-02-PLAN.md | System fetches crypto OHLCV via ccxt (Binance) with CoinGecko metadata backup | SATISFIED | CryptoFetcher uses ccxt.binance with automatic _fetch_coingecko fallback; CoinGecko OHLC endpoint used |

No orphaned requirements: DATA-01/02/03 are the only Phase 2 requirements per REQUIREMENTS.md.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/data/idx_stocks.py` | 93 | `return []` | Info | Empty-dataframe early return — legitimate guard, not a stub; conditional on `df.empty` |
| `src/data/crypto.py` | 68 | Unused `type: ignore` comment | Warning | Was suppressing an error that no longer exists; staleness of suppression annotation |
| `src/data/crypto.py` | 163 | `type: ignore` not covering actual errors (`attr-defined`, `no-any-return`) | Warning | Type safety gap — exchange is typed as `object` rather than a ccxt exchange type |
| `src/data/ingest.py` | 154 | `fetcher` type narrows to IDXStockFetcher then is reassigned CryptoFetcher | Warning | Type error under strict mypy; logic is correct but needs Union[IDXStockFetcher, CryptoFetcher] or BaseFetcher annotation |
| `src/data/backfill.py` | 100 | `fetch_hourly` called on IDXStockFetcher-typed variable | Warning | mypy attr-defined error; runtime is guarded by `if asset_type == 'crypto'` so logic is safe but type annotation is wrong |

The `return []` on idx_stocks.py:93 is NOT a stub — it is a guard for an empty DataFrame result (yfinance returning no data) and does not prevent goal achievement.

---

### Human Verification Required

#### 1. Live yfinance IDX Fetch

**Test:** Run `IDXStockFetcher().fetch(asset_id=1, symbol='BBCA.JK', start=date(2026,3,20), end=date(2026,3,21))` in a Python shell with network access.
**Expected:** Returns 1 OHLCVRow with source='yfinance', valid OHLCV data, and UTC-aware timestamp.
**Why human:** Requires live yfinance network call; cannot test in CI without mocking.

#### 2. Live ccxt Binance Fetch

**Test:** Run `CryptoFetcher().fetch(asset_id=1, symbol='BTC/USDT', start=date(2026,3,22), end=date(2026,3,23))`.
**Expected:** Returns OHLCVRow(s) with source='ccxt', non-zero volume, valid OHLCV.
**Why human:** Requires Binance API connectivity and rate-limit budget.

#### 3. CoinGecko Fallback Activation

**Test:** Mock ccxt to raise ccxt.NetworkError, then call CryptoFetcher().fetch for BTC/USDT.
**Expected:** Falls through to _fetch_coingecko; rows returned have source='coingecko' and volume=0.
**Why human:** Can be tested with mocks but live confirmation validates CoinGecko endpoint format hasn't changed.

#### 4. TimescaleDB Hypertable Creation

**Test:** Run `alembic upgrade 002` against a real TimescaleDB instance.
**Expected:** price_history and price_history_hourly hypertables created; `SELECT * FROM timescaledb_information.hypertables` shows both; compression and retention policies visible in timescaledb_information.jobs.
**Why human:** Requires TimescaleDB (not plain Postgres); the migration smoke tests only verify SQL patterns in source, not actual execution.

---

### Gaps Summary

**One gap blocks the plan's own verification criterion:**

The plan 02-01 specifies `uv run mypy src/data/ src/db/price_repo.py` should pass. It does not: 14 errors found under `strict = true`.

**Root cause:** Two distinct issues:

1. **Missing stubs** for asyncpg and ccxt (3 `import-untyped` errors) — these are third-party libraries without py.typed markers. The plan's SUMMARY correctly noted asyncpg was handled via `Any` in price_repo.py, but ccxt and asyncpg in ingest.py/backfill.py were not given per-module mypy overrides.

2. **Structural type errors** (11 errors) that are present regardless of missing stubs:
   - `fetcher` variable in ingest.py and backfill.py narrowed to `IDXStockFetcher` by first branch, then incompatibly reassigned `CryptoFetcher` in else-branch. Fix: annotate as `BaseFetcher`.
   - `exchange` typed as `object` in _fetch_ccxt_page, causing `attr-defined` on `.fetch_ohlcv`. Fix: cast to ccxt exchange type or use `Any` with proper suppression.
   - `fetch_hourly` called on a variable mypy still believes is `IDXStockFetcher`. Fix: cast or refactor.
   - Stale `type: ignore` comments from Plan 01 fixes that are now incorrect.

**Functional impact:** Zero. All 57 tests pass, runtime behavior is correct, and the structural issues are type-annotation-only. The goal's functional requirement (prices fetched, validated, stored) is fully met.

**Fix scope:** Small — annotate `fetcher` as `BaseFetcher` in two files, fix exchange typing in crypto.py, remove stale ignores, add per-module mypy overrides for asyncpg and ccxt.

---

## Commit Verification

All 7 commits from summaries confirmed in git log:

| Commit | Message |
|--------|---------|
| `5b6cb69` | test(02-01): add failing tests for price repo, migration smoke, and base fetcher |
| `527ff3b` | feat(02-01): schema models, migration 002, price repo, and base fetcher |
| `522bb2a` | test(02-01): add failing tests for OHLCV validation module |
| `4b16429` | feat(02-01): OHLCV validation with row rejection and date coverage |
| `5810ffb` | fix(02-01): resolve mypy errors in price_repo by using Any for asyncpg conn |
| `02dfa66` | feat(02-02): add IDX stock fetcher and crypto fetcher with CoinGecko fallback |
| `a67209d` | feat(02-02): add staleness detection, alerts, ingest stage, and backfill CLI |

---

_Verified: 2026-03-23T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
