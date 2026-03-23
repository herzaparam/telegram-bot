# Technology Stack

**Project:** Trade Signal Agent (IDX Stocks + Global Crypto)
**Researched:** 2026-03-23
**Overall Confidence:** HIGH -- existing architecture plan is well-researched; this validates and pins versions.

## Context

The project already has a detailed architecture plan (`plan/ARCHITECTURE.md`) with strong technology choices. This research validates those choices against current (March 2026) ecosystem state, pins specific versions, flags risks, and makes corrections where needed.

## Recommended Stack

### Language & Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.13 | Core runtime | Best ecosystem for finance (pandas, pandas-ta), ML (scikit-learn, XGBoost), and LLM integrations. pyproject.toml already specifies `>=3.13`. | HIGH |
| uv | latest | Package manager | Already in use (uv.lock present). 10-100x faster than pip. Lockfile ensures reproducible builds. Use `uv add` instead of pip install. | HIGH |

### Web Framework & API

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| FastAPI | ~0.135 | Telegram webhook, health endpoints | Async-native, Pydantic v2 integration, minimal overhead. The bot only needs a webhook receiver and health check -- FastAPI is ideal for this lightweight role. | HIGH |
| uvicorn | latest | ASGI server | Standard FastAPI deployment server. Use `--workers 1` on VPS (single process is sufficient). | HIGH |

### Database

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PostgreSQL | 16 | Primary database | Mature, well-supported. PG 16 has improved query performance and logical replication. PG 17 is also supported by TimescaleDB but PG 16 is the safer choice for Docker image stability. | HIGH |
| TimescaleDB | 2.25+ | Time-series extension | Hypertables for OHLCV data with auto-partitioning, 90%+ compression on old data, `time_bucket()` queries. One DB for both relational and time-series -- avoids running a separate InfluxDB/QuestDB. | HIGH |

**Docker image:** `timescale/timescaledb:latest-pg16`

### Database Drivers & ORM

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| asyncpg | ~0.30 | Hot-path DB queries | Raw asyncpg for bulk OHLCV reads/writes (~0.1ms/query). 45% faster than SQLAlchemy async under load per recent benchmarks. Use for `price_history` hypertable operations. | HIGH |
| SQLAlchemy | ~2.0.48 | ORM for relational tables | Type-safe models, Alembic integration, async session support. Use for `assets`, `watchlist`, `signals`, `decisions`, `lessons` -- tables where query speed is not critical. | HIGH |
| Alembic | ~1.18 | Database migrations | Standard SQLAlchemy migration tool. v1.18 has O(1) bulk reflection for PostgreSQL -- faster autogenerate. Handles both regular tables and hypertables (manual SQL for `create_hypertable` calls). | HIGH |

### Scheduler

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| System cron + Docker Compose | -- | Trigger daily pipeline | APScheduler 4.x is still alpha (4.0.0a6, April 2025). APScheduler 3.x works but adds unnecessary complexity for a single daily cron job. Use host system cron to `docker compose run --rm pipeline` as the architecture already specifies. Simple, reliable, debuggable. | HIGH |

**Decision change:** The architecture plan says "APScheduler 4.x" but APScheduler 4 has been in alpha for over a year with no stable release. For a single daily pipeline trigger, system cron is strictly better -- zero dependencies, zero failure modes, log output to file. If you later need in-process scheduling (e.g., multiple intraday scans), add APScheduler 3.11.x at that point.

### Telegram Bot

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| python-telegram-bot | ~22.7 | Telegram Bot API | Async, well-maintained, full Bot API 9.5 support. v22.7 released March 16, 2026. Most popular Python Telegram library. Requires Python 3.10+. | HIGH |

### LLM Integration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| LiteLLM | ~1.82 | Model-agnostic LLM client | Call GPT-4o-mini, Gemini 2.0 Flash, DeepSeek V3 with one interface. Structured output via Pydantic models. Swap models by changing a string. Actively maintained (multiple releases per week). | HIGH |

**LLM model strategy:**

| Task | Primary | Fallback | Est. Cost |
|------|---------|----------|-----------|
| Final decision (per asset) | GPT-4o-mini | Gemini 2.0 Flash | ~$0.20/mo |
| Self-evaluation | GPT-4o-mini | DeepSeek V3 | ~$0.15/mo |
| News classification (batch) | Gemini 2.0 Flash | GPT-4o-mini | ~$0.08/mo |
| PDF parsing (IDX quarterly) | GPT-4o-mini | Vision fallback | ~$0.03/mo |
| **Total** | | | **~$0.50/mo** |

### Technical Analysis

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pandas-ta (original) | ~0.3.14b1 | 130+ technical indicators | Calculate RSI, MACD, Bollinger Bands, etc. locally from OHLCV data. No API calls needed. Pandas-native. | MEDIUM |

**Risk flag:** The original `pandas-ta` maintainer has warned the library will be archived by July 2026 unless more sponsorship materializes. Two forks exist:
- `pandas-ta-classic` (v0.4.47, actively maintained, March 2026) -- community fork, drop-in compatible
- `pandas-ta-openbb` -- OpenBB's fork

**Recommendation:** Start with the original `pandas-ta`. If it gets archived, switch to `pandas-ta-classic` -- the API is identical. Pin version in pyproject.toml to avoid surprises.

**Alternative considered:** TA-Lib is faster (C-based) but painful to install in Docker (requires compiling C library). pandas-ta's pure Python is adequate for 14 indicators x 20 assets (~200-400ms).

### ML & Inference

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| scikit-learn | latest | Feature engineering, Random Forest | Standard ML toolkit. Feature scaling, train/test splitting, ensemble models. | HIGH |
| XGBoost | latest | Gradient boosting classifier | Best tabular data classifier. Train offline, export to ONNX for lightweight inference. | HIGH |
| ONNX Runtime | ~1.24 | LSTM + XGBoost inference | ~50MB vs PyTorch's ~2GB. Train LSTM offline (on laptop/Colab with PyTorch), export to ONNX, deploy lightweight runtime on VPS. Critical for staying within 1GB pipeline RAM budget. Requires Python >=3.11. | HIGH |
| onnxmltools | latest | Model conversion | Convert XGBoost models to ONNX format for inference. | HIGH |

### Data Processing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pandas | latest | DataFrame operations | Core data manipulation for all engines. | HIGH |
| numpy | latest | Numerical computation | Array operations, statistics, linear algebra. | HIGH |

### Market Data Sources

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| yfinance | ~0.2.x | IDX stock prices (.JK suffix) | Free, no API key. **WARNING:** Unreliable for production -- Yahoo aggressively rate-limits, frequently changes backend (Feb 2025 major breakage, Sep 2025 data gaps reported). Cache aggressively in TimescaleDB, only fetch new days. No better free alternative for IDX .JK data exists. | MEDIUM |
| ccxt | latest | Crypto OHLCV from Binance | Unified API for 100+ exchanges. Exchange-portable -- if Binance faces issues, switch to Tokocrypto/Bybit/OKX with zero code changes. Actively maintained (releases weekly). | HIGH |
| fredapi | latest | US macro data (Fed rate, CPI, VIX) | Official FRED API wrapper. 120 req/min, free. Government API -- will not disappear or paywall. | HIGH |
| feedparser | latest | Indonesian news RSS | Kontan, CNBC Indonesia, Bisnis RSS feeds. Stable, feature-complete library. Unlimited, no API key. | HIGH |
| praw | latest | Reddit sentiment | r/cryptocurrency, r/finansial. 100 req/min with OAuth. | HIGH |

### HTTP Client

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| httpx | ~0.28 | Async HTTP for all API calls | Single reused `AsyncClient` with connection pooling, HTTP/2 support. Used for CoinGecko, DeFiLlama, Etherscan, Mempool.space, Finnhub, Bank Indonesia, GitHub -- all sources that don't have dedicated Python libraries worth adding. | HIGH |

### PDF Parsing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pymupdf4llm | ~1.27 | IDX financial report parsing | Fastest Python PDF parser. Outputs LLM-optimized markdown. Layout analysis without GPU. v1.27.2.2 released March 20, 2026. Handles Indonesian laporan keuangan tables well. Vision LLM fallback for scanned/complex pages. | HIGH |

### Retry & Resilience

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| tenacity | ~9.1 | Exponential backoff retry | Standard retry library. Use for all API calls with transient error handling (429, 503, timeouts). v9.1.4 released Feb 2026. | HIGH |

### Configuration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pydantic-settings | ~2.13 | Type-safe config from .env | Validates environment variables at startup. Catches missing API keys before pipeline runs. Integrates with Pydantic v2 used by FastAPI and LiteLLM structured output. | HIGH |

### Web Scraping (Limited Use)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| beautifulsoup4 | latest | Stockbit sentiment scraping | Only needed for Stockbit.com Indonesian sentiment. Pair with httpx for fetching. | MEDIUM |

### Containerization

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Docker | latest | Container runtime | Standard containerization. | HIGH |
| Docker Compose | v2 | Multi-service orchestration | TimescaleDB + bot + pipeline in managed deployment. Compose profiles for on-demand pipeline execution. | HIGH |

### Testing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pytest | latest | Test framework | Standard Python testing. | HIGH |
| pytest-asyncio | latest | Async test support | Test async data fetchers and httpx calls. | HIGH |
| pytest-cov | latest | Coverage reporting | Track test coverage across engines. | HIGH |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Scheduler | System cron | APScheduler 4.x | APScheduler 4 still in alpha (1+ year). Overkill for single daily trigger. |
| Scheduler | System cron | APScheduler 3.11 | Works but adds a dependency for something cron does natively. |
| Technical Analysis | pandas-ta | TA-Lib | C library compilation in Docker is painful. pandas-ta is fast enough for daily batch. |
| HTTP Client | httpx | aiohttp | httpx has cleaner API, HTTP/2 support, sync+async in one library. |
| DB Driver | asyncpg + SQLAlchemy | SQLAlchemy only | asyncpg is 45% faster for hot-path OHLCV queries. Worth the dual-driver complexity. |
| Time-series DB | TimescaleDB (PG extension) | InfluxDB / QuestDB | One database (PG) for everything. No need to run and maintain a separate TSDB. |
| IDX Data | yfinance | Twelve Data | Twelve Data has better reliability but 800 req/day free tier is tight for IDX + crypto + fundamentals. yfinance is sufficient with aggressive caching. |
| Package Manager | uv | pip / poetry | uv is 10-100x faster, already in use (uv.lock present), excellent lockfile support. |
| PDF Parser | pymupdf4llm | pdfplumber / pdfminer | pymupdf4llm is fastest and outputs LLM-optimized markdown directly. Purpose-built for LLM pipelines. |
| Telegram | python-telegram-bot | aiogram | python-telegram-bot has larger community, better docs, same async capability. |
| LLM Client | LiteLLM | OpenAI SDK directly | LiteLLM enables model swapping (GPT/Gemini/DeepSeek) without code changes. Critical for cost optimization. |

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| PyTorch (on VPS) | ~2GB RAM. Use ONNX Runtime (~50MB) for inference. Train offline on laptop/Colab. |
| Celery / Redis | Overkill for a single daily pipeline. System cron + Docker Compose profiles is simpler. |
| APScheduler 4.x | Alpha for 1+ year. Not production-ready. |
| pytrends | Archived April 2025. Library is dead. Google may have an official Trends API (July 2025) but unverified for free access. |
| snscrape / twscrape | X/Twitter killed free read API. Scrapers break frequently. Not worth the maintenance burden. |
| Glassnode API | API requires $799/mo Professional plan. Free tier is web-only, not programmatic. |
| InfluxDB / QuestDB | Adding a separate TSDB when TimescaleDB handles time-series as a PG extension is unnecessary complexity. |
| Django / Flask | Overkill. FastAPI is lighter, async-native, perfect for webhook + health check endpoints. |

## Installation

```bash
# Core framework
uv add fastapi uvicorn python-telegram-bot pydantic-settings

# Database
uv add sqlalchemy asyncpg alembic

# LLM
uv add litellm

# Market data
uv add yfinance ccxt fredapi feedparser praw httpx

# Analysis
uv add pandas numpy pandas-ta scikit-learn xgboost

# ML inference
uv add onnxruntime onnxmltools

# PDF parsing
uv add pymupdf4llm

# Resilience
uv add tenacity

# Web scraping (Stockbit)
uv add beautifulsoup4

# Dev dependencies
uv add --dev pytest pytest-asyncio pytest-cov ruff mypy
```

## Data Source API Keys Required

| Service | Env Variable | Free Tier | Phase Needed |
|---------|-------------|-----------|--------------|
| Telegram | `TELEGRAM_BOT_TOKEN` | Free (@BotFather) | Phase 1 |
| OpenAI | `OPENAI_API_KEY` | Pay-per-use (~$0.50/mo) | Phase 2 |
| Binance | `BINANCE_API_KEY` | Free (account required) | Phase 1 |
| CoinGecko | `COINGECKO_API_KEY` | Free Demo (10k/mo) | Phase 1 |
| FRED | `FRED_API_KEY` | Free (120 req/min) | Phase 3 |
| Finnhub | `FINNHUB_API_KEY` | Free (60 req/min) | Phase 4 |
| Reddit | `REDDIT_CLIENT_ID/SECRET` | Free (100 req/min) | Phase 4 |
| Etherscan | `ETHERSCAN_API_KEY` | Free (5/sec, 100k/day) | Phase 5 |
| GitHub | `GITHUB_TOKEN` | Free (5k/hr, optional) | Phase 5 |

## VPS Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 2 GB | 4 GB |
| Storage | 10 GB | 20 GB |
| OS | Ubuntu 22.04+ | Ubuntu 24.04 |
| Est. Cost | ~$5-6/mo (Hetzner) | ~$10/mo |

## Sources

- [python-telegram-bot v22.7 docs](https://docs.python-telegram-bot.org/) -- HIGH confidence
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) -- 4.0.0a6 alpha confirmed
- [APScheduler 3.11.2 stable](https://apscheduler.readthedocs.io/en/3.x/) -- HIGH confidence
- [LiteLLM PyPI](https://pypi.org/project/litellm/) -- v1.82.4, HIGH confidence
- [pandas-ta PyPI](https://pypi.org/project/pandas-ta/) -- archival risk flagged
- [pandas-ta-classic PyPI](https://pypi.org/project/pandas-ta-classic/) -- v0.4.47 actively maintained
- [FastAPI PyPI](https://pypi.org/project/fastapi/) -- v0.135.1
- [SQLAlchemy 2.0 changelog](https://docs.sqlalchemy.org/en/20/changelog/changelog_20.html) -- v2.0.48
- [Alembic docs](https://alembic.sqlalchemy.org/) -- v1.18.4
- [TimescaleDB releases](https://github.com/timescale/timescaledb/releases) -- v2.25.2
- [ONNX Runtime PyPI](https://pypi.org/project/onnxruntime/) -- v1.24.4, requires Python >=3.11
- [pymupdf4llm PyPI](https://pypi.org/project/pymupdf4llm/) -- v1.27.2.2
- [httpx PyPI](https://pypi.org/project/httpx/) -- v0.28.1
- [tenacity PyPI](https://pypi.org/project/tenacity/) -- v9.1.4
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) -- v2.13.1
- [ccxt GitHub](https://github.com/ccxt/ccxt) -- actively maintained, weekly releases
- [yfinance issues](https://github.com/ranaroussi/yfinance/issues) -- reliability concerns documented
- [uv docs](https://docs.astral.sh/uv/guides/projects/) -- modern Python package management
