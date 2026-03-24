# Codebase Concerns

**Analysis Date:** 2026-03-24

## Tech Debt

**Pipeline stages "analyze", "decide", "report" are stubs:**
- Issue: `PipelineRunner.run_pipeline()` in `src/pipeline/runner.py:70` lists four stages (`["fetch", "analyze", "decide", "report"]`), but only the `fetch` stage has a real implementation (`ingest_stage` in `src/data/ingest.py`). The analyze, decide, and report stages are passed via `stage_funcs` dict — if callers omit them (as `src/pipeline/main.py` currently does), those stages silently log a warning and skip execution with no error raised.
- Files: `src/pipeline/runner.py:69-83`, `src/pipeline/main.py:59-63`
- Impact: Running the default pipeline produces incomplete output with no obvious failure signal. `stage_funcs` is passed as `{}` by the current CLI, meaning only `fetch` will ever run.
- Fix approach: Either raise an error when a declared stage has no registered function, or wire Phase 3+ engine stages as they are built.

**`asyncio.get_event_loop()` deprecation in Python 3.10+:**
- Issue: `src/data/idx_stocks.py:86` calls `asyncio.get_event_loop()` directly. This is deprecated in Python 3.10 and raises `DeprecationWarning` in 3.12+; in Python 3.13 (the project's minimum) it will not reliably return the running loop from inside a coroutine.
- Files: `src/data/idx_stocks.py:86-89`
- Impact: Potential `RuntimeError` when the running loop is not the event loop returned by `get_event_loop()`. Test passes today because of mocking, but could silently fail under certain async runners.
- Fix approach: Replace with `asyncio.get_running_loop()` inside the async method.

**Hardcoded default credentials in production config:**
- Issue: `src/config.py:17-19` ships `db_password = "trade_dev"`, `database_url` and `database_url_sync` with embedded plaintext credentials as pydantic-settings defaults. These get used if the environment variable is not set.
- Files: `src/config.py:17-19`
- Impact: Any deployment that fails to set `DATABASE_URL` silently connects with a known-public password. The values are also committed to git history.
- Fix approach: Change defaults to empty strings (or `SecretStr("")`) and add a validator that raises `ValidationError` if still empty, forcing explicit environment configuration. Treat `database_url` the same as `openai_api_key`.

**`database_url` string manipulation to produce asyncpg URL:**
- Issue: Two files manually strip the SQLAlchemy dialect prefix from `settings.database_url` using `str.replace("postgresql+asyncpg://", "postgresql://")` to produce a raw asyncpg URL. This is fragile — it breaks silently if the URL scheme ever changes (e.g., switching to `postgresql+psycopg`).
- Files: `src/data/ingest.py:172`, `src/data/backfill.py:128`
- Impact: Silent misconfiguration if the dialect prefix changes; raw asyncpg connection is opened with a malformed URL.
- Fix approach: Add a `database_url_asyncpg` computed property to `Settings` that derives the raw URL from `database_url` via `urllib.parse`, or store a separate `ASYNCPG_DATABASE_URL` env var.

**Module-level mutable global state in ingest:**
- Issue: `src/data/ingest.py:33` initialises `_alert_collector` as a module-level global `AlertCollector`. `reset_alert_collector()` mutates it via `global` (suppressed with `# noqa: PLW0603`). This pattern is fragile under concurrent runs or test isolation — tests that import `ingest` share state unless they explicitly call `reset_alert_collector()`.
- Files: `src/data/ingest.py:33-44`
- Impact: Test pollution if tests don't call `reset_alert_collector()`; stale alerts from a previous pipeline run can bleed into the next if `reset_alert_collector()` is not called before each run.
- Fix approach: Pass `AlertCollector` as a parameter to `ingest_stage()` (dependency injection) rather than relying on the module global.

**`upsert_prices` uses unparameterized table name in SQL:**
- Issue: `src/db/price_repo.py:34-41` constructs SQL with an f-string for the table name: `f"INSERT INTO {table} ..."`. The `table` parameter is caller-controlled and not validated. Same pattern in `get_latest_date` at line 66.
- Files: `src/db/price_repo.py:34-41`, `src/db/price_repo.py:66`
- Impact: SQL injection vector if `table` is ever passed from untrusted input. Currently callers pass hardcoded literals (`"price_history"`, `"price_history_hourly"`), but the pattern is unsafe as a convention.
- Fix approach: Validate `table` against an explicit allowlist (e.g., `{"price_history", "price_history_hourly"}`) and raise `ValueError` for unknown names before interpolating into SQL.

**`_should_weekly_refresh` uses `date.today()` instead of injected `run_date`:**
- Issue: `src/data/ingest.py:56` calls `date.today()` directly inside `_should_weekly_refresh()`. The pipeline already has a `run_date` parameter (passed into `PipelineRunner.run_stage`), which is ignored here. When running the pipeline for a historical date (e.g., `--date 2026-01-01`), the weekly-refresh check still uses the real current day.
- Files: `src/data/ingest.py:56-58`, `src/data/ingest.py:181`
- Impact: Incorrect fetch ranges when running historical/backfill pipeline runs. A Tuesday historical run may trigger the Monday weekly-refresh logic.
- Fix approach: Thread `run_date` from `PipelineRunner` through `ingest_stage` and pass it to `_should_weekly_refresh`.

**`ingest_stage` uses `date.today()` instead of injected `run_date`:**
- Issue: `src/data/ingest.py:179` calls `today = date.today()` rather than using the pipeline `run_date`. This also affects auto-backfill range calculation at line 187 (`today - timedelta(days=730)`).
- Files: `src/data/ingest.py:179`, `src/data/ingest.py:187-193`
- Impact: Historical runs always fetch up to today rather than to the specified run date. Produces incorrect data ranges for any date other than today.
- Fix approach: `ingest_stage` needs to accept `run_date: date` as a parameter, or be closured with `run_date` before being passed as `StageFunc`. The `StageFunc` signature (`AsyncSession, Asset`) currently has no mechanism for this.

**`StageFunc` signature has no context parameter:**
- Issue: `src/pipeline/runner.py:24` defines `StageFunc = Callable[[AsyncSession, Asset], Awaitable[None]]`. There is no way to pass the pipeline `run_date` or other context to a stage function without using a closure or global. This was already hit by `ingest_stage` relying on `date.today()`.
- Files: `src/pipeline/runner.py:24`, `src/data/ingest.py:136`
- Impact: All future stages (analyze, decide) will face the same limitation — they can't receive the canonical pipeline date without workarounds.
- Fix approach: Introduce a `PipelineContext` dataclass with `run_date`, `rerun_failed`, etc. and change `StageFunc` to `Callable[[AsyncSession, Asset, PipelineContext], Awaitable[None]]`.

**`yfinance` retry catches `Exception` broadly:**
- Issue: `src/data/idx_stocks.py:35` configures tenacity with `retry_if_exception_type((ConnectionError, TimeoutError, Exception))`. Since `Exception` is the base of all non-system exceptions, this effectively retries on every exception including programming errors (`AttributeError`, `KeyError`, etc.).
- Files: `src/data/idx_stocks.py:32-37`
- Impact: Retry storms on bugs that should fail fast; wastes up to 3×30 seconds per asset on non-transient errors.
- Fix approach: Remove `Exception` from the retry tuple; keep only transient network exceptions.

**`ccxt` exchange instance not reused across assets:**
- Issue: `src/data/crypto.py:56` and `src/data/crypto.py:89` create a new `ccxt.binance` exchange object per `fetch()` call, which runs once per asset. Each construction and teardown creates a new HTTP client. With 3+ crypto assets, this multiplies connection overhead.
- Files: `src/data/crypto.py:56`, `src/data/crypto.py:89`
- Impact: Extra connection setup latency; not catastrophic but wasteful.
- Fix approach: Reuse a shared exchange instance per pipeline run, or make `CryptoFetcher` own the exchange as an instance attribute with proper lifecycle management (open once, close in `__aenter__`/`__aexit__`).

## Known Bugs

**`PipelineRunner` opens raw asyncpg connection per asset inside `ingest_stage`, leaking connections on exception:**
- Symptoms: asyncpg connection opened at `src/data/ingest.py:173`; if `asyncpg.connect()` itself raises, the `finally: await conn.close()` never runs since `conn` is not yet bound.
- Files: `src/data/ingest.py:173-249`
- Trigger: asyncpg connection failure during ingest.
- Workaround: The outer `try/finally` block does guard `conn.close()` once `conn` is assigned, so normal failures are handled. The bug only manifests if `asyncpg.connect()` raises.

**`PipelineRunner` status logic double-counts skipped assets as partial:**
- Symptoms: `src/pipeline/runner.py:260-265` — if `total_failed == 0` and `total_skipped > 0`, the pipeline run is marked `"partial"`, but the returned `StageResult.status` at line 271 uses `total_failed == 0 and total_skipped == 0` for `"completed"`. Any skipped asset causes both the DB record and return value to report `"partial"`, even if skipping is expected behavior.
- Files: `src/pipeline/runner.py:260-271`
- Trigger: Any asset classified as `SourceCriticalError` (skipped).
- Workaround: Acceptable behavior for now; becomes confusing in reporting once the report stage is implemented.

## Security Considerations

**Hardcoded credentials in source code defaults:**
- Risk: Database password `"trade_dev"` embedded in `src/config.py:17-19`; if `DATABASE_URL` env var is not set, the application connects with the known default credentials.
- Files: `src/config.py:17-19`
- Current mitigation: Credentials are labeled as development defaults; production is expected to override via environment.
- Recommendations: Remove plaintext defaults; require explicit environment configuration; add a startup assertion that rejects the default password string in non-development environments.

**Bot server listens on `0.0.0.0`:**
- Risk: `src/bot/main.py:25` binds uvicorn to `0.0.0.0:8000` without any authentication on the `/health` endpoint. In a cloud deployment without a firewall rule, this endpoint is publicly reachable.
- Files: `src/bot/main.py:25`
- Current mitigation: Only a `/health` endpoint exists today; no sensitive data is exposed currently.
- Recommendations: Add a reverse proxy (nginx) in front of uvicorn, or restrict bind to `127.0.0.1` and expose via Docker port mapping only.

**LLM API key not validated at startup:**
- Risk: `openai_api_key` in `src/config.py:22` defaults to `SecretStr("")`. No startup check validates the key. LLM calls silently return `LLM_UNAVAILABLE` sentinel on failure (`src/llm/client.py:61-68`), which means a missing key causes silent degraded operation rather than a startup error.
- Files: `src/config.py:22`, `src/llm/client.py:61-68`
- Current mitigation: `LLM_UNAVAILABLE` sentinel prevents crashes.
- Recommendations: Log a prominent warning at pipeline startup if `openai_api_key` is empty; consider making pipeline stages that require LLM explicitly check for key availability before attempting calls.

## Performance Bottlenecks

**Sequential per-asset asyncpg connection creation during ingest:**
- Problem: `src/data/ingest.py:173` opens a new asyncpg connection for every asset processed. With 6 assets and a connection establishment time of ~5-20ms each, this is minor but is a pattern that will not scale well as the asset list grows.
- Files: `src/data/ingest.py:171-174`
- Cause: The design decision to use raw asyncpg for hot paths, combined with no connection pooling at the ingest level.
- Improvement path: Create the asyncpg connection once per stage run in the caller (`PipelineRunner`) and pass it to the stage function, or use a dedicated asyncpg pool.

**`backfill.py` shares one asyncpg connection across all concurrent tasks:**
- Problem: `src/data/backfill.py:129` creates a single asyncpg `conn` and passes it to all concurrent `_fetch_and_upsert` tasks running under `asyncio.Semaphore(5)`. asyncpg connections are not safe to use concurrently — concurrent `executemany` calls on the same connection will serialize or raise.
- Files: `src/data/backfill.py:129`, `src/data/backfill.py:161-165`
- Cause: Semaphore limits concurrency to 5, but the shared connection is not protected.
- Improvement path: Create a connection per task inside `_fetch_and_upsert` (already done for ingest), or use an asyncpg connection pool.

**yfinance executor calls block a thread pool thread:**
- Problem: `src/data/idx_stocks.py:86-90` runs synchronous yfinance in `loop.run_in_executor(None, ...)` using the default thread pool. With 3 stock assets processed sequentially, this ties up default executor threads during potentially slow yfinance HTTP calls.
- Files: `src/data/idx_stocks.py:86-90`
- Cause: yfinance is synchronous; executor wrapping is the correct approach but uses the shared default pool.
- Improvement path: Pass a dedicated `ThreadPoolExecutor` with a bounded size so yfinance calls do not compete with other executor usage.

## Fragile Areas

**`PriceHistory` and `PriceHistoryHourly` use `Float` (IEEE 754):**
- Files: `src/db/models.py:129-133`, `src/db/models.py:146-150`
- Why fragile: ORM model columns use `Float` (double precision), but `DailyDecision.decision_price` uses `Numeric(20, 8)`. Financial calculations on `Float` columns can accumulate rounding errors. The ORM model and migration may be inconsistent (migration not checked here).
- Safe modification: Consider using `Numeric` for all price columns; note this changes query performance.
- Test coverage: Validation tests check NaN/None but do not test rounding or precision.

**`validate_date_coverage` is defined but never called in the pipeline:**
- Files: `src/data/validation.py:89-131`
- Why fragile: The function exists and is tested, but `ingest_stage` only calls `validate_rows` — never `validate_date_coverage`. Gap detection is dead code in the live pipeline.
- Safe modification: Adding a call is safe; removing would break tests that cover it.
- Test coverage: Covered by `tests/test_data/test_validation.py` but the call site does not exist in production.

**`COINGECKO_ID_MAP` is a hardcoded 3-entry dict:**
- Files: `src/data/crypto.py:23-27`
- Why fragile: CoinGecko fallback only works for BTC, ETH, SOL. Adding any new crypto asset requires code changes (not just a database insert) unless the asset also has a mapping entry.
- Safe modification: Adding new entries is safe; this pattern will not scale without a config-driven or DB-driven mapping.
- Test coverage: Not explicitly tested for missing mappings in current tests.

**`PipelineRun` has a unique constraint on `(run_date, stage)` but no unique index exists on `stage` enum values:**
- Files: `src/db/models.py:60-61`, `src/pipeline/runner.py:70`
- Why fragile: Stage names are free-form strings (`"fetch"`, `"analyze"`, etc.). A typo in a `stage_funcs` key (e.g., `"analzye"`) would create a new pipeline run record with the misspelled stage name, silently never completing the intended stage. No enum or check constraint prevents this.
- Safe modification: Add `Enum` type for `PipelineRun.stage`; align `SOURCE_TIERS` and stage names to a shared enum.
- Test coverage: No test validates that only expected stage name strings are used.

## Scaling Limits

**Fixed 6-asset seed list:**
- Current capacity: 3 IDX stocks + 3 crypto assets hardcoded in `src/db/models.py:179-224` (SEED_ASSETS).
- Limit: Adding assets requires a code change or manual DB insert; the `COINGECKO_ID_MAP` also limits crypto to 3 symbols.
- Scaling path: Asset management UI or admin command; move `COINGECKO_ID_MAP` to the `assets` table as a metadata column.

**No rate limiting on the bot FastAPI server:**
- Current capacity: Single `/health` endpoint today, no rate limiting configured.
- Limit: Once Telegram webhook handlers are added, unbounded concurrent requests could exhaust uvicorn workers.
- Scaling path: Add middleware rate limiting (e.g., `slowapi`) when webhook endpoints are implemented.

## Dependencies at Risk

**`yfinance` (no pinned upper bound):**
- Risk: yfinance has a history of breaking API changes with new releases; `pyproject.toml` specifies `>=1.2.0` with no upper bound. A breaking release would silently produce empty DataFrames (which validation catches) or raise exceptions that retry loops exhaust.
- Impact: All IDX stock data ingestion fails until fixed.
- Migration plan: Pin to a tested minor version range; add a yfinance integration smoke test to CI.

**`ccxt` (no pinned upper bound):**
- Risk: `>=4.5.44` with no upper bound. ccxt frequently changes exchange-specific behavior between minor versions.
- Impact: Binance OHLCV fetching could break silently.
- Migration plan: Pin to a tested minor version; test against Binance testnet in CI.

**`litellm` (no pinned upper bound):**
- Risk: `>=1.82.6` with no upper bound. litellm's provider integrations are tied to upstream provider API versions and change frequently.
- Impact: LLM calls return `LLM_UNAVAILABLE` sentinel on version-induced failures, producing silent degraded pipeline runs.
- Migration plan: Pin to a tested minor version.

## Missing Critical Features

**No scheduler integration:**
- Problem: The architecture document (`plan/ARCHITECTURE.md`) specifies APScheduler for cron-triggered daily pipeline runs, but `APScheduler` is not listed in `pyproject.toml` and no scheduler code exists.
- Blocks: Automated daily pipeline execution; the pipeline must be triggered manually via CLI.

**Telegram bot has no actual handlers:**
- Problem: `src/bot/main.py` is a FastAPI skeleton with only a `/health` endpoint. No Telegram webhook, command handlers, or reporting are implemented.
- Blocks: Any user-facing reporting or on-demand queries.

**No analyze/decide/report stage implementations:**
- Problem: The `engines/` directory and `SignalRepository` referenced in Phase 3 context (`src/engines/`, `src/db/signal_repo.py`) do not exist. The `analyze`, `decide`, and `report` stages are listed in the pipeline but have no implementations.
- Blocks: The core product value (trading signals and decisions) is entirely unimplemented.

## Test Coverage Gaps

**No integration tests for database operations:**
- What's not tested: All test files in `tests/test_db/` and `tests/test_data/` use mocked sessions and mock asyncpg connections. There are no integration tests that run against a real (or in-memory) TimescaleDB instance.
- Files: `tests/test_data/test_price_repo.py`, `tests/test_data/test_ingest.py`, `tests/test_db/test_models.py`
- Risk: Schema bugs, migration drift, and asyncpg-specific behaviors are invisible until production.
- Priority: High

**No tests for the bot process:**
- What's not tested: `src/bot/main.py` has no corresponding test file. The `tests/` tree has no `test_bot/` directory.
- Files: `src/bot/main.py`
- Risk: FastAPI route behavior unverified; regressions in future webhook handlers will not be caught.
- Priority: Medium

**No tests for `backfill.py` shared-connection concurrency issue:**
- What's not tested: The concurrency behavior of `run_backfill()` when multiple tasks share one asyncpg connection.
- Files: `src/data/backfill.py:114-179`
- Risk: Silent data corruption or asyncpg errors under concurrent backfill.
- Priority: High

**`validate_date_coverage` never invoked in pipeline:**
- What's not tested: The integration between gap detection and the ingest stage. The function is unit-tested in isolation but the end-to-end behavior (gap found → alert raised) is untested.
- Files: `src/data/validation.py:89-131`, `src/data/ingest.py`
- Risk: Date gaps in ingested data pass through without alerts.
- Priority: Medium

---

*Concerns audit: 2026-03-24*
