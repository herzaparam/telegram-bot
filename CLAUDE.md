# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**trade-agent** is an async Python trading-analysis system for IDX (Indonesia Stock Exchange) stocks and crypto. It runs as **two independent processes**:

1. **Pipeline** (`src/pipeline`) — a batch job that fetches market data, runs a fleet of analysis engines, produces LLM-backed trading decisions, evaluates past decisions, and pushes a daily Telegram report.
2. **Bot** (`src/bot`) — a long-running FastAPI + python-telegram-bot (PTB) webhook service that answers on-demand user commands (watchlist, reports, valuation, backtests, etc.).

Both processes share the database (`src/db`) and configuration (`src/config.py`) but **must never import each other's orchestration code** (see [Two-Process Boundary](#two-process-boundary)).

Data flows into **TimescaleDB** (PostgreSQL 16 + time-series hypertables). LLM calls go through **litellm** (OpenAI `gpt-4o-mini` primary, Gemini `gemini-2.0-flash` fallback) and are engineered to *never raise* — they degrade to a sentinel result instead.

## Tech Stack

- **Language/runtime:** Python 3.13 (pinned in `.python-version`), fully async (`asyncio`)
- **Package manager:** `uv` (lockfile `uv.lock` committed) — the project is a package (`[tool.uv] package = true`)
- **Web/bot:** FastAPI + uvicorn, python-telegram-bot 22.x (webhook mode)
- **DB:** SQLAlchemy 2.x async ORM + Alembic migrations; raw `asyncpg` for hot-path OHLCV upserts; TimescaleDB
- **Data:** yfinance (IDX stocks, `.JK` tickers), ccxt/Binance + CoinGecko fallback (crypto), pandas, pandas-ta-classic, pmdarima
- **LLM:** litellm; **ML:** xgboost, onnxmltools, pywavelets
- **External data:** FRED (macro), Finnhub, Reddit (asyncpraw), feedparser (news RSS), pymupdf4llm (financial-doc parsing)
- **Observability:** structlog (JSON logs), prometheus-client, Pushgateway, Grafana
- **Resilience:** tenacity (retry/backoff)
- **Tooling:** ruff (lint + format), mypy (strict), pre-commit, pytest + pytest-asyncio

## Development Commands

All commands run through `uv`. Install deps with `uv sync`.

```bash
# Run the pipeline (batch)
uv run python -m src.pipeline.main                     # full run for today
uv run python -m src.pipeline.main --stage fetch       # single stage
uv run python -m src.pipeline.main --date 2026-03-23 --rerun-failed
uv run python -m src.pipeline.main --skip-global-fetch # skip macro/news/sentiment
uv run pipeline                                        # console-script alias

# Run the bot (webhook service on :8000)
uv run python -m src.bot.main                          # production
uv run bot                                             # console-script alias
uv run bot-dev                                         # hot-reload dev server

# Historical backfill
uv run python -m src.data.backfill --from 2024-01-01 --to 2026-01-01

# Tests
uv run pytest                                          # all tests
uv run pytest tests/test_bot/                          # one module
uv run pytest -x -vv                                   # stop on first failure, verbose
uv run pytest --cov=src --cov-report=term-missing      # coverage (not enforced)

# Lint / format / type-check
uv run ruff check --fix .
uv run ruff format .
uv run mypy src

# Pre-commit (ruff lint + format on commit)
uv run pre-commit install
uv run pre-commit run --all-files

# Database migrations (Alembic)
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"
uv run alembic downgrade -1

# Local infra (TimescaleDB only, for dev)
docker compose up -d db
```

> **Note:** root `main.py` is an unused stub. Real entry points live under `src/`.

## Architecture

### Two-Process Boundary

- The **bot** process (`src/bot/`) MUST NOT import from `src/pipeline` or `src/llm`. Bot handlers read from the DB (and call read-only helpers), they do not trigger analysis. Keep this boundary intact — it exists so the always-on bot can never be taken down by pipeline/LLM code paths.
- Shared, safe-to-import layers: `src/config.py`, `src/logging.py`, `src/db/`, `src/monitoring/`, `src/risk/`, `src/report/`.

### Pipeline stages

`src/pipeline/main.py` wires an ordered `stage_funcs` dict handed to `PipelineRunner` (`src/pipeline/runner.py`). Order matters:

1. **`evaluate`** (`src/data/evaluate.py`) — score prior decisions against realized prices.
2. **`reflect`** (`src/data/reflect.py`) — extract lessons from past decisions (stored in `lessons`).
3. **`fetch`** (`_enhanced_ingest_stage` → `src/data/ingest.py` + `fundamental_fetcher` + `due_diligence`) — OHLCV price ingest plus per-asset fundamentals and DD report.
4. **`analyze`** (`src/data/analyze.py`) — run all applicable engines, persist `SignalRecord` rows.
5. **`decide`** (`src/data/decide.py`) — LLM verdict (STRONG BUY … STRONG SELL) with deterministic fallback.

Before per-asset stages, `fetch_global_data()` fetches macro/news/sentiment once and scores news impact via LLM. After stages: batch cross-cutting reflection, a discovery scan (`src/data/discovery.py`), a daily portfolio risk snapshot, and the daily Telegram report (`src/data/report.py`), then Prometheus metrics are pushed.

**Checkpointing:** `PipelineRunner` writes a `PipelineRun` per (date, stage) and a `PipelineAssetRun` per asset. Completed work is skipped on re-run; failed assets don't block others; the pipeline is kill/restart-safe. Each stage call is wrapped in `asyncio.wait_for` with per-stage timeouts from `settings`.

**Failure tiers** (`src/pipeline/tiers.py`): data sources are `CRITICAL` (raise `SourceCriticalError` → skip asset), `IMPORTANT` (`DegradedResult` → continue degraded), or `SUPPLEMENTARY` (`SkippedResult` → ignore). `SOURCE_TIERS` maps source names to tiers.

### Analysis engines

`src/engines/` holds 15 engines, all subclassing `BaseEngine` (`src/engines/base.py`) and returning a frozen `Signal(category, score, confidence, reasoning, indicators, data_quality)`. `analyze()` is **synchronous, CPU-bound, and must never raise**. Engines declare `supports_stocks` / `supports_crypto`; `analyze_stage` picks the applicable set per asset.

Engines: `technical`, `quantitative`, `fundamental`, `macro`, `sentiment`, `valuation`, `event`, `ml_ai`, `onchain`, `options`, `behavioral`, `alternative`, `network`, `game_theory`, `emerging`. Indicator/component weights are tunable via `settings` (`weight_*` fields).

### Data layer

- `src/data/base.py` — `BaseFetcher` ABC + `OHLCVRow` dataclass (the fetcher↔DB contract).
- Fetchers: `idx_stocks.py` (yfinance, blocking calls wrapped in `run_in_executor`), `crypto.py` (ccxt/Binance → CoinGecko fallback), plus `macro_fetcher`, `news_fetcher`, `sentiment_fetcher`, `fundamental_fetcher`, `onchain_fetcher`, `github_fetcher`, `ownership_fetcher`, `idx_doc_fetcher`.
- Processing: `validation.py`, `staleness.py`, `alerts.py` (batched `AlertCollector`).
- Higher-level stage modules: `analyze`, `decide`, `evaluate`, `reflect`, `report`, `discovery`, `due_diligence`, `backtest`, `backfill`.

### Bot layer

`src/bot/main.py` builds a PTB `Application` (updater=None, webhook mode) inside a FastAPI `lifespan`, registers `CommandHandler`s, and exposes `POST /telegram/webhook`, `GET /health`, and `/metrics` (Prometheus ASGI mount). Every incoming HTTP request is counted via `MetricsMiddleware`. Authorization is a chat-ID whitelist (`src/bot/auth.py`, `is_authorized`, comma-separated `TELEGRAM_CHAT_ID`); unauthorized messages are silently ignored.

Handlers live in `src/bot/handlers/`: `start`, `watchlist` (`/add`, `/remove`, `/watchlist`), `report`, `scorecard`, `lessons`, `settings`, `valuation`, `fundamentals`, `discover`, `duediligence` (`/dd` alias), `compare`, `portfolio`, `backtest`.

### Supporting modules

- `src/db/` — `models.py` (all ORM models + `SEED_ASSETS`), `database.py` (async engine/session factory, pool 5+10), `price_repo.py` (raw asyncpg upsert), typed repositories (`signal_repo`, `decision_repo`, `evaluation_repo`, `lesson_repo`), and `migrations/`.
- `src/llm/` — `client.py` (`llm_completion()` never raises, returns `LLM_UNAVAILABLE` sentinel), `prompts.py`, `news_analyzer.py`, `doc_parser.py`.
- `src/risk/` — `metrics` (Sharpe/Sortino), `var`, `concentration`, `correlation`, `stress`.
- `src/ml/` — `features.py`, `train_xgboost.py`, `train_lstm.py`, model artifacts in `models/`.
- `src/report/formatter.py` — Telegram message formatting.
- `src/monitoring/` — Prometheus `metrics.py` + `pushgateway.py`.

## Database & Migrations

- Async URL `DATABASE_URL` (`postgresql+asyncpg://…`) for the app; sync URL `DATABASE_URL_SYNC` for Alembic. Some hot paths derive a raw asyncpg URL by stripping the `+asyncpg` dialect prefix.
- Migrations live in `src/db/migrations/versions/` as `NNN_slug.py` (currently through `014_portfolio_risk`). Config in `alembic.ini` (`file_template = %%(rev)s_%%(slug)s`).
- `price_history` / `price_history_hourly` are TimescaleDB hypertables (hourly has ~7-day retention; daily is compressed after 30 days).
- ~25 ORM models (`assets`, `pipeline_runs`, `pipeline_asset_runs`, `daily_decisions`, `signals`, `watchlist`, `bot_settings`, `evaluations`, `accuracy_stats`, `lessons`, `news_events`, `macro_data`, `stock_fundamentals`, `financial_docs`, `financial_data`, `discovery_candidates`, `ownership_snapshots`, `due_diligence_reports`, `on_chain_data`, `github_activity`, `ml_predictions`, `portfolio_risk_snapshots`, `backtest_results`, `idx_holidays`, `backoff_state`).

**Adding a model:** add to `src/db/models.py`, then `alembic revision --autogenerate` and review the generated migration.

## Conventions

- **Formatting/linting:** ruff (`.ruff.toml` — line length 120, target py313, rulesets `E,F,I,W,UP,B,SIM`). Run before committing; pre-commit enforces it.
- **Types:** mypy strict + pydantic plugin. Untyped third-party libs are allowlisted under `[[tool.mypy.overrides]]` in `pyproject.toml`.
- **Naming:** `snake_case` files/functions/vars, `PascalCase` classes/dataclasses, `UPPER_SNAKE` constants/sentinels, private module helpers prefixed `_`. Enums are `StrEnum` with `UPPER_CASE` members.
- **Imports:** full `src.*` paths (no aliases); `from __future__ import annotations` is used across `src/data/` and newer modules. Third-party before internal.
- **Logging:** module-level `logger = structlog.get_logger(__name__)`; bind context (`component`, `asset`, `stage`); snake_case event names as the first positional arg, structured kwargs after. JSON in prod, console in dev — configured once via `setup_logging()`.
- **Return values:** frozen dataclasses for structured results (`Signal`, `StageResult`, `LLMResult`, `DecisionResult`, tier results); empty `list`/`None` over exceptions for "no data".
- **Error handling:** the pipeline runner catches per-asset exceptions so one failure never blocks others; LLM calls never raise; fetchers use tenacity for transient network errors; source failures route through `handle_source_failure()`.
- `__init__.py` files are empty package markers — no re-exports.

## Testing

- pytest with `asyncio_mode = "auto"` (no `@pytest.mark.asyncio` needed). `testpaths = ["tests"]`, `pythonpath = ["."]`. ~80 test files.
- `tests/` mirrors `src/` (`tests/test_bot/`, `test_db/`, `test_risk/`, `test_ml/`, `test_monitoring/`, `test_report/`, …). Test files `test_<module>.py`, classes `Test<Thing>`, methods `test_<behavior>` with `-> None` annotations.
- Mock external I/O (yfinance, ccxt, litellm, asyncpg, Telegram) with `unittest.mock` (`AsyncMock`/`patch` by import path). Use in-memory `aiosqlite` for DB integration; use `structlog.testing.capture_logs()` instead of mocking structlog. Don't mock pure internal functions — test them directly.
- Coverage is not enforced (no threshold in config).

## Configuration

All settings are in `src/config.py` (`Settings(BaseSettings)`, pydantic-settings, loaded from `.env`; secrets typed `SecretStr`). Copy `.env.example` → `.env`. Key vars:

- **DB:** `DATABASE_URL`, `DATABASE_URL_SYNC`, `DB_PASSWORD`
- **LLM:** `OPENAI_API_KEY`, `LLM_PRIMARY_MODEL`, `LLM_FALLBACK_MODEL`, `LLM_MAX_RETRIES`, `LLM_TIMEOUT`
- **Telegram:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (whitelist), `WEBHOOK_BASE_URL`, `TELEGRAM_WEBHOOK_SECRET`
- **Logging:** `LOG_LEVEL`, `LOG_FORMAT` (`json`|`console`)
- **Pipeline timeouts:** `TIMEOUT_FETCH`, `TIMEOUT_ANALYZE`, `TIMEOUT_LLM`, `TIMEOUT_DECIDE_PER_CALL`, `TIMEOUT_EVALUATE`, `TIMEOUT_REFLECT`, `TIMEOUT_REPORT`
- **Optional external APIs (engines degrade gracefully if absent):** `FRED_API_KEY`, `FINNHUB_API_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `GITHUB_TOKEN`
- **Engine weights:** many `WEIGHT_*` fields (technical, quantitative, fundamental, macro, sentiment)
- **Monitoring:** `PROMETHEUS_PUSHGATEWAY_URL`, `GRAFANA_ADMIN_PASSWORD`, `TELEGRAM_MONITORING_BOT_TOKEN`, `TELEGRAM_MONITORING_CHAT_ID`

## Deployment & Monitoring

- **Local dev:** `docker-compose.yml` runs TimescaleDB (and optionally `bot`/`pipeline` images).
- **Production:** `docker-compose.prod.yml` runs `db`, `bot`, `pipeline` (profile-gated), plus `prometheus`, `grafana`, `node_exporter`, `pushgateway`, each with memory/CPU limits. The `pipeline` service is behind `profiles: ["pipeline"]` (batch, not always-on).
- **Image:** `Dockerfile` (python:3.13-slim, `uv sync --frozen --no-dev`, no CMD — command set per compose service).
- **CI/CD:** `.github/workflows/deploy.yml` builds and deploys `bot` over SSH to a VPS on push to `main` (skips doc/planning-only changes) and sends Telegram deploy notifications.
- **Metrics:** pipeline pushes to Pushgateway on completion; bot exposes `/metrics`; Grafana dashboards + alerting provisioned under `monitoring/`.

## Adding New Code

- **New pipeline stage:** implement `async def <stage>_stage(session, asset)` in `src/data/`, register it in the `stage_funcs` dict in `src/pipeline/main.py`. Runner validates that every requested stage name has a function (unknown names raise `ValueError`).
- **New engine:** subclass `BaseEngine` in `src/engines/<name>.py`, implement `analyze()` (sync, never raises) and `category`, set `supports_stocks`/`supports_crypto`, then add it in `_get_engines_for_asset` in `src/data/analyze.py`. Add tunable weights to `settings` if needed.
- **New fetcher:** subclass `BaseFetcher` in `src/data/`, add its source to `SOURCE_TIERS` in `src/pipeline/tiers.py`.
- **New bot command:** add a handler in `src/bot/handlers/`, register a `CommandHandler` in `src/bot/main.py`, gate with `is_authorized`. Do not import pipeline/LLM code.
- **New config value:** add a typed field with default to `Settings` in `src/config.py` (and to `.env.example`).

## Additional References

- `.planning/codebase/` holds deeper analysis docs (STACK/ARCHITECTURE/STRUCTURE/CONVENTIONS/TESTING/INTEGRATIONS/CONCERNS). **These were generated 2026-03-24 against a much smaller version of the codebase and are now partially stale** — trust this file and the actual source first; use those docs only for background.
- `plan/` holds early design notes (`ARCHITECTURE.md`, `PROJECT-PLAN.md`, API research).
- `AGENTS.md` mirrors this guidance for Codex; keep the two roughly in sync when project-wide facts change.
