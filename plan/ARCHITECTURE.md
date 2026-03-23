# Trade Signal Agent — Architecture & Technical Design

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.11+ | Best ecosystem for finance (pandas, pandas-ta), ML (scikit-learn, XGBoost), and API integrations |
| Web Framework | FastAPI | Async support, Telegram webhook, health/status endpoints |
| Database | PostgreSQL 16 + TimescaleDB | Hypertables for OHLCV time-series (auto-partitioning, compression, `time_bucket`), normal tables for relational data. One DB for everything |
| DB Driver | asyncpg (OHLCV hot paths) + SQLAlchemy 2.0 async (relational) | Raw asyncpg for bulk price reads/writes (~0.1ms/query), SQLAlchemy for type-safe relational operations |
| Migrations | Alembic | Migration management for both regular tables and hypertables |
| Scheduler | APScheduler 4.x | Async-native rewrite, built-in cron triggers, no broker required, missed-fire handling |
| Telegram | python-telegram-bot v20+ | Async, well-maintained, full Bot API support |
| LLM | LiteLLM (model-agnostic) | Swap between GPT-4o-mini, Gemini 2.0 Flash, DeepSeek V3 without code changes. Structured output via Pydantic |
| ML | scikit-learn, XGBoost | Traditional ML models (Random Forest, gradient boosting) |
| ML Inference | ONNX Runtime | LSTM inference via lightweight runtime (~50MB vs PyTorch's ~2GB). Train offline, deploy ONNX model |
| Technical Analysis | pandas-ta | 130+ indicators, pip-installable (no C deps), pandas-native. 14 indicators × 20 assets ~200-400ms |
| Data Processing | pandas, numpy | Data manipulation, numerical computation |
| PDF Parsing | PyMuPDF (pymupdf4llm) | Fastest Python PDF parser, LLM-optimized markdown output. Vision LLM fallback for complex/scanned pages |
| HTTP Client | httpx (async) | Single reused AsyncClient with connection pooling, HTTP/2 support, requests-compatible API |
| Crypto Exchange | ccxt | Unified API for 100+ exchanges (Binance, Tokocrypto, Bybit). Exchange-portable, actively maintained |
| RSS Parsing | feedparser | Stable, feature-complete, standard for RSS/Atom |
| Containerization | Docker + Docker Compose | PostgreSQL/TimescaleDB + bot + pipeline in managed deployment |
| Environment | pydantic-settings | Type-safe config with .env support, validation |

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         VPS (Docker Compose)                          │
│                                                                       │
│  ┌──────────────────┐    ┌───────────────────────────────────────┐   │
│  │ PostgreSQL 16     │    │         Telegram Bot (always-on)      │   │
│  │ + TimescaleDB     │◄──►│                                       │   │
│  │                   │    │  • Webhook handler (FastAPI)           │   │
│  │ Regular tables:   │    │  • Command handlers                   │   │
│  │ • assets          │    │  • On-demand reports (reads from DB)  │   │
│  │ • watchlist       │    │  • /health endpoint                   │   │
│  │ • signals         │    │  • ~100MB RAM                         │   │
│  │ • decisions       │    └───────────────────────────────────────┘   │
│  │ • evaluations     │                                                │
│  │ • lessons         │    ┌───────────────────────────────────────┐   │
│  │ • news_events     │    │     Pipeline (cron-triggered daily)   │   │
│  │ • financial_docs  │◄──►│                                       │   │
│  │ • pipeline_runs   │    │  Stage 1: FETCH (async I/O)           │   │
│  │                   │    │  Stage 2: STORE raw data              │   │
│  │ Hypertables:      │    │  Stage 3: ANALYZE (sequential CPU)    │   │
│  │ • price_history   │    │  Stage 4: DECIDE (LLM calls)          │   │
│  │                   │    │  Stage 5: REPORT (Telegram send)      │   │
│  └──────────────────┘    │  Stage 6: EVALUATE (self-review)       │   │
│                           │  • ~1GB RAM peak                       │   │
│                           └───────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
   ┌─────────────┐    ┌──────────────┐    ┌──────────────┐
   │ Market Data  │    │   LLM API    │    │   Telegram   │
   │              │    │              │    │     API      │
   │ • yfinance   │    │ • GPT-4o-   │    │              │
   │ • ccxt       │    │   mini      │    │ • Send msgs  │
   │   (Binance)  │    │ • Gemini    │    │ • Receive    │
   │ • CoinGecko  │    │   Flash     │    │   commands   │
   │ • DeFiLlama  │    │ • DeepSeek  │    └──────────────┘
   │ • Etherscan  │    │   V3        │
   │ • FRED       │    │ (via        │
   │ • RSS feeds  │    │  LiteLLM)   │
   │ • Bank Indo  │    └──────────────┘
   │ • idx.co.id  │
   │ • Reddit     │
   │ • GitHub     │
   └─────────────┘
```

### Key Architecture Decisions

**Two-process model:** The Telegram bot and pipeline are separate processes sharing PostgreSQL. The bot is lightweight and always-on (~100MB). The pipeline is heavy and runs once daily (~1GB peak). This prevents ML model loading from blocking Telegram commands.

**Decoupled pipeline stages:** Each stage (fetch → store → analyze → decide → report → evaluate) is idempotent and restartable. If stage 3 fails on asset 12, restart from asset 12 without re-fetching. Pipeline state tracked in `pipeline_runs` table.

**Sequential engine execution:** Engines run sequentially per asset (not 280 concurrent tasks). Process one asset through all 14 engines, release memory, then next asset. This keeps peak RAM under 1GB for the pipeline.

## Daily Execution Flow

```
06:00  ┌─ STAGE 1: SELF-EVALUATE (async I/O)
       │   ├─ Fetch current prices for yesterday's decisions
       │   ├─ Compare verdict vs actual price movement
       │   ├─ LLM analyzes: what went right/wrong?
       │   ├─ Extract lessons → store in DB
       │   └─ Update accuracy stats
       │
06:05  ├─ STAGE 2: INGEST DATA (async I/O, semaphore=5)
       │   ├─ IDX stock prices ──────── yfinance (.JK) + cache in DB
       │   ├─ Crypto prices ─────────── ccxt (Binance) + CoinGecko metadata
       │   ├─ Indonesian news ───────── Kontan/CNBC ID/Bisnis RSS
       │   ├─ Global news ──────────── Finnhub
       │   ├─ Macro Indonesia ───────── Bank Indonesia / BPS / World Bank
       │   ├─ Macro Global ─────────── FRED
       │   ├─ On-chain ─────────────── DeFiLlama + Etherscan
       │   ├─ Sentiment ────────────── Reddit + Fear & Greed
       │   └─ Alt data ─────────────── GitHub API
       │   All raw data stored to DB before proceeding
       │
06:15  ├─ STAGE 3: RUN SIGNAL ENGINES (sequential per asset, CPU-bound)
       │   For each asset (one at a time):
       │   ├─ Load data from DB into DataFrames
       │   ├─ Engine 1: Fundamental ─── score + confidence + reasoning
       │   ├─ Engine 2: Technical ───── score + confidence + reasoning
       │   ├─ Engine 3: Quantitative ── score + confidence + reasoning
       │   ├─ Engine 4: ML/AI ──────── score + confidence + reasoning
       │   ├─ Engine 5: Sentiment ───── score + confidence + reasoning
       │   ├─ Engine 6: On-Chain ────── score + confidence + reasoning (crypto only)
       │   ├─ Engine 7: Options ─────── score + confidence + reasoning (limited)
       │   ├─ Engine 8: Behavioral ──── score + confidence + reasoning
       │   ├─ Engine 9: Event-Driven ── score + confidence + reasoning
       │   ├─ Engine 10: Alt Data ───── score + confidence + reasoning
       │   ├─ Engine 11: Network ────── score + confidence + reasoning
       │   ├─ Engine 12: Macro ──────── score + confidence + reasoning
       │   ├─ Engine 13: Game Theory ── score + confidence + reasoning
       │   ├─ Engine 14: Emerging ───── score + confidence + reasoning
       │   ├─ Store all signals to DB
       │   └─ Release DataFrames + gc.collect()
       │
06:30  ├─ STAGE 4: LLM FINAL DECISION (async I/O, semaphore=2)
       │   ├─ Input: all 14 scores + lessons + accuracy stats + context
       │   ├─ Output: verdict + score + confidence + reasoning + risk
       │   └─ Store decision in DB
       │
06:35  └─ STAGE 5: SEND TELEGRAM REPORT
           ├─ Yesterday's scorecard
           ├─ Today's signals per asset
           ├─ LLM reasoning
           ├─ Lessons applied
           └─ New opportunities
```

### Concurrency Model

```
Phase         Nature        Strategy                  Why
─────         ──────        ────────                  ───
Data fetch    I/O-bound     asyncio.gather +          Network-limited, 10+ APIs
                            Semaphore(5)

Engine exec   CPU-bound     Sequential (sync)         ML inference + pandas-ta on
                                                      1-2 vCPU, no parallelism gain

LLM calls     I/O-bound     asyncio +                 Rate-limited by provider
                            Semaphore(2)

Telegram      I/O-bound     Single async call         One message
```

Do NOT use `asyncio.gather` for engine execution — CPU tasks starve the event loop. Run synchronously in the main thread, or use `loop.run_in_executor(ThreadPoolExecutor(1))` to keep the event loop responsive.

## Data Sources — Detailed

### Indonesian Stocks (IDX)

| Data Type | Source | Endpoint / Method | Rate Limit | Python Library |
|-----------|--------|-------------------|------------|----------------|
| Stock prices | Yahoo Finance | yfinance `.JK` suffix | ~few hundred/day (aggressive throttling) | `yfinance` |
| IHSG index | Yahoo Finance | `^JKSE` | Same as above | `yfinance` |
| Financial reports | idx.co.id | PDF download (scrape) | — | `httpx` + `pymupdf` |
| Fundamentals (backup) | Yahoo Finance | yfinance `.info` | Same as above | `yfinance` |
| News | Kontan.co.id | RSS feed (`rss.kontan.co.id`) | Unlimited | `feedparser` |
| News | CNBC Indonesia | RSS feed (`cnbcindonesia.com/news/rss`) | Unlimited | `feedparser` |
| News | Bisnis.com | RSS feed (`bisnis.com/rss`) | Unlimited | `feedparser` |
| Sentiment | Stockbit | Web scrape | Be polite | `httpx` + `beautifulsoup4` |
| Sentiment | Reddit r/finansial | PRAW API | 100 req/min (auth) | `praw` |
| Macro | Bank Indonesia | BI API / scrape | — | `httpx` |
| Macro | BPS (Badan Pusat Statistik) | BPS API | — | `httpx` |
| Macro | World Bank | REST API | Free | `wbgapi` |

**yfinance warning:** No official API — scrapes Yahoo Finance endpoints, breaks when Yahoo changes backend. Use aggressive caching (store in TimescaleDB, only fetch new days). Supplement with IDX's own data for reliability.

### Global Crypto

| Data Type | Source | Endpoint / Method | Rate Limit | Python Library |
|-----------|--------|-------------------|------------|----------------|
| Prices + OHLCV | Binance (via ccxt) | REST + WebSocket | 1200 req/min | `ccxt` |
| Prices (backup) | CoinGecko | REST API (metadata focus) | 10k calls/mo (free Demo key) | `httpx` |
| On-chain (DeFi) | DeFiLlama | REST API | Free, no key | `httpx` |
| On-chain (ETH) | Etherscan | REST API | 5 calls/sec, 100k/day | `httpx` |
| On-chain (BTC) | Mempool.space | REST API | Unpublished (be polite) | `httpx` |
| Sentiment | alternative.me | Fear & Greed API | Free | `httpx` |
| Sentiment | Reddit (r/cryptocurrency) | PRAW API | 100 req/min (auth) | `praw` |
| News | Finnhub | REST API | 60 calls/min | `httpx` |
| Alt data | GitHub | REST API | 5k req/hr | `httpx` |

**ccxt advantage:** Unified API across 100+ exchanges. If Binance faces regulatory issues, switch to Tokocrypto (Indonesian), Bybit, or OKX with zero code changes.

**CoinGecko strategy:** 10k calls/month is tight. Use CoinGecko for metadata only (coin info, market cap rankings). Use ccxt for OHLCV price data directly from exchanges.

### Shared / Global

| Data Type | Source | Endpoint / Method | Rate Limit | Python Library |
|-----------|--------|-------------------|------------|----------------|
| US macro (Fed rate, CPI) | FRED | REST API | 120 req/min | `fredapi` |
| Indonesian macro | World Bank | REST API | Free | `wbgapi` |
| Technical indicators | Local computation | pandas-ta | No limit | `pandas-ta` |

**Removed:** Google Trends (pytrends archived April 2025, library is dead). Indonesian social sentiment from Stockbit/Reddit is more actionable.

## Database Schema

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Core asset tracking
CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,          -- e.g., "BBCA", "BTC"
    name VARCHAR(100),                     -- e.g., "Bank Central Asia", "Bitcoin"
    asset_type VARCHAR(10) NOT NULL,       -- "stock" or "crypto"
    exchange VARCHAR(20),                  -- "IDX", "binance", etc.
    yfinance_symbol VARCHAR(20),           -- "BBCA.JK", "BTC-USD"
    ccxt_symbol VARCHAR(30),              -- "BTC/USDT", null for stocks
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, asset_type)
);

-- User watchlist
CREATE TABLE watchlist (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    asset_id INTEGER REFERENCES assets(id),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(telegram_user_id, asset_id)
);

-- Historical price data (TimescaleDB hypertable)
CREATE TABLE price_history (
    time TIMESTAMPTZ NOT NULL,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    UNIQUE(asset_id, time)
);
SELECT create_hypertable('price_history', 'time');

-- Enable compression for old data (90%+ storage reduction)
ALTER TABLE price_history SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'asset_id',
    timescaledb.compress_orderby = 'time DESC'
);
SELECT add_compression_policy('price_history', INTERVAL '30 days');

-- Individual engine signals
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id),
    date DATE NOT NULL,
    category VARCHAR(30) NOT NULL,         -- "technical", "fundamental", etc.
    score DECIMAL(4, 3),                   -- -1.000 to +1.000
    confidence DECIMAL(4, 3),              -- 0.000 to 1.000
    reasoning TEXT,
    indicators JSONB,                      -- raw indicator values
    data_quality JSONB,                    -- {"sources_available": [...], "sources_failed": [...]}
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(asset_id, date, category)
);

-- LLM final decisions
CREATE TABLE daily_decisions (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id),
    date DATE NOT NULL,
    verdict VARCHAR(15) NOT NULL,          -- STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    score DECIMAL(4, 3),
    confidence DECIMAL(4, 3),
    price_at_decision DECIMAL(20, 8),
    all_signals JSONB,                     -- snapshot of all 14 engine outputs
    reasoning TEXT,                         -- LLM explanation
    key_factors JSONB,                     -- top 3 factors
    risk_warning TEXT,
    wait_for TEXT,                          -- event to wait for, if any
    lessons_applied JSONB,                 -- which lessons informed this decision
    model_used VARCHAR(50),               -- "gpt-4o-mini", "gemini-2.0-flash", etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(asset_id, date)
);

-- Self-evaluation results
CREATE TABLE evaluations (
    id SERIAL PRIMARY KEY,
    decision_id INTEGER REFERENCES daily_decisions(id),
    price_after DECIMAL(20, 8),
    change_pct DECIMAL(8, 4),
    was_correct BOOLEAN,
    analysis TEXT,                          -- LLM self-analysis
    missed_signals JSONB,
    overweighted JSONB,
    underweighted JSONB,
    weight_adjustments JSONB,              -- suggested category weight changes
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Learned lessons from self-evaluation
CREATE TABLE lessons (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    asset_type VARCHAR(10),                -- "stock", "crypto", or "all"
    lesson TEXT NOT NULL,
    source_decision_id INTEGER REFERENCES daily_decisions(id),
    times_applied INTEGER DEFAULT 0,
    still_valid BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Accuracy tracking
CREATE TABLE accuracy_stats (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id),
    period VARCHAR(10),                    -- "7d", "30d", "90d", "all"
    total INTEGER,
    correct INTEGER,
    win_rate DECIMAL(5, 2),
    best_engine VARCHAR(30),
    worst_engine VARCHAR(30),
    computed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Parsed financial documents (IDX)
CREATE TABLE financial_docs (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id),
    doc_type VARCHAR(20),                  -- "quarterly", "annual"
    period VARCHAR(10),                    -- "Q1-2026", "2025"
    file_path TEXT,
    source_url TEXT,
    parsed_data JSONB,                     -- LLM-extracted financials
    parsed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- News events with impact scoring
CREATE TABLE news_events (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    headline TEXT NOT NULL,
    source VARCHAR(50),                    -- "kontan", "finnhub", "cnbc_id"
    url TEXT,
    impact_score DECIMAL(4, 3),            -- -1 to +1
    affected_assets JSONB,                 -- [{"asset_id": 1, "impact": 0.5}]
    category VARCHAR(30),                  -- "central_bank", "earnings", "regulation"
    raw_content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pipeline execution tracking (idempotent restart support)
CREATE TABLE pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_date DATE NOT NULL,
    stage VARCHAR(20) NOT NULL,            -- "fetch", "analyze", "decide", "report", "evaluate"
    status VARCHAR(20) NOT NULL,           -- "running", "completed", "failed", "partial"
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB,                        -- error details, asset progress, partial results
    UNIQUE(run_date, stage)
);

-- Indexes
CREATE INDEX idx_signals_asset_date ON signals(asset_id, date DESC);
CREATE INDEX idx_decisions_asset_date ON daily_decisions(asset_id, date DESC);
CREATE INDEX idx_lessons_valid ON lessons(still_valid, asset_type);
CREATE INDEX idx_news_date ON news_events(date DESC);
CREATE INDEX idx_pipeline_runs_date ON pipeline_runs(run_date DESC);
```

**Note:** `price_history` uses TimescaleDB hypertable — no manual index needed on `(asset_id, time)`, TimescaleDB handles partitioning and indexing automatically. Old price data auto-compressed after 30 days (90%+ storage reduction).

### Data Retention Policy

| Data Type | Retention | Rationale |
|-----------|-----------|-----------|
| Daily OHLCV (price_history) | 2 years (compressed after 30d) | 200-day MA + seasonal patterns. ~14,600 rows for 20 assets |
| Signals | 1 year | Self-evaluation and trend analysis |
| Decisions | Forever | Small data, valuable for backtesting |
| Evaluations | Forever | Accuracy tracking |
| Lessons | Forever (mark invalid) | Feedback loop memory |
| News events | 90 days | Short shelf life, prune old |
| Pipeline runs | 30 days | Debugging only |

## Project Structure

```
trade-agent/
├── plan/                              # Planning docs
│   ├── PROJECT-PLAN.md                # Overview + features
│   ├── ARCHITECTURE.md                # This document
│   └── price-prediction-methods.md    # Reference: all 215 methods
│
├── src/
│   ├── config.py                      # Settings via pydantic-settings
│   │
│   ├── bot/                           # Telegram bot (always-on process)
│   │   ├── main.py                    # Bot entry point + FastAPI webhook
│   │   ├── commands.py                # Command handlers
│   │   └── formatter.py              # Message formatting (markdown)
│   │
│   ├── pipeline/                      # Daily pipeline (cron-triggered process)
│   │   ├── main.py                    # Pipeline entry point + stage orchestration
│   │   ├── runner.py                  # Stage execution, idempotent restart
│   │   └── scheduler.py              # APScheduler 4.x cron trigger (alternative to system cron)
│   │
│   ├── db/
│   │   ├── models.py                  # SQLAlchemy ORM models
│   │   ├── database.py                # asyncpg pool + SQLAlchemy async session
│   │   └── migrations/               # Alembic migrations
│   │
│   ├── data/                          # Data fetchers (one per source)
│   │   ├── base.py                    # BaseFetcher abstract class
│   │   ├── idx_stocks.py             # IDX prices via yfinance .JK
│   │   ├── crypto.py                  # ccxt (Binance) + CoinGecko metadata
│   │   ├── idx_fundamentals.py        # IDX PDF reports from idx.co.id
│   │   ├── onchain.py                 # DeFiLlama + Etherscan + Mempool
│   │   ├── sentiment.py               # Reddit PRAW + Stockbit + Fear&Greed
│   │   ├── news_id.py                 # Kontan, CNBC ID, Bisnis RSS
│   │   ├── news_global.py             # Finnhub
│   │   ├── macro_id.py                # Bank Indonesia + BPS + World Bank
│   │   ├── macro_global.py            # FRED
│   │   └── options.py                 # CBOE (limited)
│   │
│   ├── engines/                       # Signal engines (one per category)
│   │   ├── base.py                    # BaseEngine abstract class
│   │   ├── fundamental.py             # 1. Fundamental analysis
│   │   ├── technical.py               # 2. Technical analysis
│   │   ├── quantitative.py            # 3. Quantitative/statistical
│   │   ├── ml_ai.py                   # 4. ML/AI (XGBoost + ONNX LSTM)
│   │   ├── sentiment.py               # 5. Sentiment
│   │   ├── onchain.py                 # 6. On-chain (crypto only)
│   │   ├── options.py                 # 7. Options
│   │   ├── behavioral.py              # 8. Behavioral finance
│   │   ├── event_driven.py            # 9. Event-driven
│   │   ├── alt_data.py                # 10. Alternative data
│   │   ├── network.py                 # 11. Network/graph
│   │   ├── macro.py                   # 12. Macro/economic
│   │   ├── game_theory.py             # 13. Game theory
│   │   └── emerging.py                # 14. Emerging methods
│   │
│   ├── llm/                           # LLM interactions (via LiteLLM)
│   │   ├── client.py                  # LiteLLM client wrapper + retry
│   │   ├── decision_maker.py          # Final verdict from all signals
│   │   ├── evaluator.py               # Self-evaluation of past decisions
│   │   ├── news_analyzer.py           # News headline → impact score
│   │   ├── doc_parser.py              # IDX PDF → structured financials
│   │   └── prompts.py                 # All prompt templates
│   │
│   ├── feedback/                      # Self-evaluation feedback loop
│   │   ├── tracker.py                 # Store/retrieve decisions
│   │   ├── lesson_store.py            # Lesson CRUD + retrieval
│   │   └── accuracy.py                # Win rate + stats computation
│   │
│   ├── discovery/                     # Asset screening + opportunities
│   │   ├── screener.py                # Filter by criteria
│   │   └── scanner.py                 # Top movers / anomaly detection
│   │
│   └── models/                        # Pre-trained ML model files
│       └── lstm/                      # ONNX-exported LSTM models
│
├── tests/
│   ├── test_engines/
│   ├── test_data/
│   ├── test_llm/
│   ├── test_pipeline/
│   └── test_bot/
│
├── docker-compose.yml                 # TimescaleDB + bot + pipeline
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## Core Interfaces

### Signal (Engine Output)

```python
@dataclass
class Signal:
    category: str          # e.g., "technical", "fundamental"
    score: float           # -1.0 (strong sell) to +1.0 (strong buy)
    confidence: float      # 0.0 (no confidence) to 1.0 (certain)
    reasoning: str         # human-readable explanation
    indicators: dict       # raw values, e.g., {"rsi": 28, "macd": "bullish_cross"}
    data_quality: dict     # {"sources_available": [...], "sources_failed": [...]}
```

### Decision (LLM Output)

```python
@dataclass
class Decision:
    verdict: str           # STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL
    score: float           # -1.0 to +1.0
    confidence: float      # 0.0 to 1.0
    reasoning: str         # 2-3 sentence explanation
    key_factors: list[str] # top 3 factors driving decision
    risk_warning: str      # main risk to watch
    wait_for: str | None   # event to wait for before acting
    model_used: str        # "gpt-4o-mini", "gemini-2.0-flash", etc.
```

### BaseEngine Interface

```python
from abc import ABC, abstractmethod

class BaseEngine(ABC):
    @abstractmethod
    def analyze(self, asset: Asset, data: dict) -> Signal:
        """Run analysis and return a signal. Synchronous (CPU-bound)."""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """Engine category name."""
        pass

    @property
    def supports_stocks(self) -> bool:
        return True

    @property
    def supports_crypto(self) -> bool:
        return True

    @property
    def required_sources(self) -> set[str]:
        """Data sources this engine needs. Used for graceful degradation."""
        return set()
```

### BaseFetcher Interface

```python
from abc import ABC, abstractmethod

class BaseFetcher(ABC):
    @abstractmethod
    async def fetch(self, asset: Asset, **kwargs) -> dict:
        """Fetch data for an asset. Returns raw data dict."""
        pass

    async def fetch_with_retry(self, asset: Asset, retries: int = 3, **kwargs) -> dict:
        """Fetch with exponential backoff retry (via tenacity)."""
        ...
```

## LLM Integration Design

### Model Selection Strategy

```
Task                    Primary Model         Fallback            Why
────                    ─────────────         ────────            ───
Final decision          GPT-4o-mini           Gemini 2.0 Flash    Best cost/quality for structured analysis
Self-evaluation         GPT-4o-mini           DeepSeek V3         Nuanced reasoning needed
News classification     Gemini 2.0 Flash      GPT-4o-mini         Cheapest, adequate for sentiment scoring
PDF parsing (IDX)       GPT-4o-mini           Vision LLM          Indonesian language understanding
```

All models accessed via LiteLLM — single interface, swap models by changing a string. Model used is tracked in `daily_decisions.model_used` for accuracy comparison.

### Decision Maker Flow

```
                All 14 Signals
                     │
                     ▼
┌──────────────────────────────────────┐
│         PROMPT BUILDER               │
│                                      │
│  1. Format signal table              │
│  2. Add current price + context      │
│  3. Add upcoming events              │
│  4. Add recent lessons (top 20)      │
│  5. Add accuracy stats (30d)         │
│  6. Add asset-specific rules         │
│     (stock vs crypto)                │
│  7. Add data quality report          │
│     (which sources failed today)     │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│         LLM (via LiteLLM)            │
│                                      │
│  System: "You are a senior trading   │
│  analyst..."                         │
│                                      │
│  Response format: Pydantic schema    │
│  Temperature: 0.3 (consistent)       │
└──────────────┬───────────────────────┘
               │
               ▼
        Parse → Decision (typed)
```

### Self-Evaluation Flow

```
Yesterday's Decision + Today's Price
               │
               ▼
┌──────────────────────────────────────┐
│         EVALUATION PROMPT            │
│                                      │
│  1. Original decision + reasoning    │
│  2. All signals at time of decision  │
│  3. Actual price outcome             │
│  4. News that happened since         │
│  5. Ask: what went right/wrong?      │
│  6. Ask: extract a reusable lesson   │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│         LLM (via LiteLLM)            │
│                                      │
│  Output:                             │
│  • analysis (what happened)          │
│  • missed_signals                    │
│  • overweighted / underweighted      │
│  • lesson (reusable rule)            │
│  • weight_adjustments (suggestions)  │
└──────────────┬───────────────────────┘
               │
               ▼
        Store evaluation + lesson in DB
```

### News Analyzer Flow

```
Raw headlines (ID + global)
               │
               ▼
┌──────────────────────────────────────┐
│         NEWS ANALYSIS PROMPT         │
│                                      │
│  For each watchlist asset:           │
│  "How does this news affect {asset}?"│
│                                      │
│  Output per headline:                │
│  • impact_score (-1 to +1)           │
│  • affected assets + direction       │
│  • category (central_bank, earnings) │
│  • reasoning                         │
└──────────────────────────────────────┘
```

### IDX Financial Doc Parser Flow

```
PDF (Bahasa Indonesia)
        │
        ▼
  PyMuPDF (pymupdf4llm) → LLM-optimized markdown
        │
        ├─ If tables extracted cleanly → proceed
        │
        ├─ If complex/scanned → Vision LLM fallback
        │
        ▼
┌──────────────────────────────────────┐
│         DOC PARSER PROMPT            │
│                                      │
│  "Extract from this laporan          │
│   keuangan:                          │
│   - Pendapatan (revenue)             │
│   - Laba bersih (net profit)         │
│   - Total utang (debt)              │
│   - Arus kas operasi (op. CF)        │
│   - Ekuitas (equity)                │
│   - ROE, ROA                         │
│   - YoY growth rates                 │
│   - Key risks mentioned              │
│   - Management outlook"              │
└──────────────────────────────────────┘
        │
        ▼
  Structured JSON → DB
```

## LLM Cost Estimate

| Usage | Calls/day | Input tokens | Output tokens | Est. cost/month |
|-------|-----------|-------------|---------------|-----------------|
| Final decision (per asset x 20) | 20 | ~2k each | ~300 each | $0.20 |
| Self-evaluation (per asset x 20) | 20 | ~1.5k each | ~400 each | $0.15 |
| News analysis (batch) | 5 | ~3k each | ~500 each | $0.08 |
| PDF parsing (quarterly) | ~2/quarter | ~5k each | ~1k each | $0.03 |
| Report generation | 1 | ~2k | ~500 | $0.03 |
| **Total** | | | | **~$0.50 - $1.00/mo** |

Prices based on GPT-4o-mini ($0.15/$0.60 per 1M tokens). Gemini 2.0 Flash would be ~30% cheaper.

## Error Handling Strategy

### Data Source Classification

```python
class DataTier:
    CRITICAL = "critical"          # Pipeline cannot produce useful output without this
    IMPORTANT = "important"        # Degrades quality significantly
    SUPPLEMENTARY = "supplementary" # Nice to have

SOURCE_TIERS = {
    "price_ohlcv":     DataTier.CRITICAL,       # Can't analyze without prices
    "orderbook":       DataTier.IMPORTANT,
    "news_sentiment":  DataTier.SUPPLEMENTARY,
    "social_metrics":  DataTier.SUPPLEMENTARY,
    "onchain_data":    DataTier.SUPPLEMENTARY,
    "macro_data":      DataTier.IMPORTANT,
    "alt_data":        DataTier.SUPPLEMENTARY,
}
```

### Failure Policy

```
API call fails
     │
     ├─ Retry with exponential backoff (3 attempts, via tenacity)
     │   Only retry transient errors (HTTP 429, 503, timeouts)
     │   Don't retry permanent errors (HTTP 401, 404)
     │
     ├─ Check data tier:
     │   ├─ CRITICAL fails → skip this asset entirely, alert via Telegram
     │   ├─ IMPORTANT fails → continue with degraded quality, log warning
     │   └─ SUPPLEMENTARY fails → continue, log info
     │
     ├─ If primary fails → try backup API
     │   (e.g., ccxt/Binance fails → CoinGecko; yfinance fails → log + skip)
     │
     ├─ Engine missing required data → return Signal with confidence=0
     │   and note="Skipped: missing {sources}"
     │
     ├─ Pass data quality metadata to LLM
     │   (LLM factors data completeness into confidence)
     │
     └─ Log error + alert via Telegram if critical
```

## Deployment Architecture (VPS)

```yaml
# docker-compose.yml
services:
  db:
    image: timescale/timescaledb:latest-pg16
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.5"
        reservations:
          memory: 128M
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: trade_agent
      POSTGRES_USER: trade
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    shm_size: "64mb"
    ports:
      - "5432:5432"

  bot:
    build: .
    command: python -m src.bot.main
    deploy:
      resources:
        limits:
          memory: 192M
          cpus: "0.25"
        reservations:
          memory: 96M
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql+asyncpg://trade:${DB_PASSWORD}@db:5432/trade_agent
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      TELEGRAM_CHAT_ID: ${TELEGRAM_CHAT_ID}
    restart: unless-stopped

  pipeline:
    build: .
    command: python -m src.pipeline.main
    deploy:
      resources:
        limits:
          memory: 1280M
          cpus: "1.5"
        reservations:
          memory: 512M
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql+asyncpg://trade:${DB_PASSWORD}@db:5432/trade_agent
      LITELLM_API_KEY: ${OPENAI_API_KEY}
      BINANCE_API_KEY: ${BINANCE_API_KEY}
      FRED_API_KEY: ${FRED_API_KEY}
      FINNHUB_API_KEY: ${FINNHUB_API_KEY}
      REDDIT_CLIENT_ID: ${REDDIT_CLIENT_ID}
      REDDIT_CLIENT_SECRET: ${REDDIT_CLIENT_SECRET}
      ETHERSCAN_API_KEY: ${ETHERSCAN_API_KEY}
    profiles: ["pipeline"]  # Only run when triggered

volumes:
  pgdata:
```

**Trigger pipeline via host cron:**
```bash
# /etc/cron.d/trade-pipeline
0 6 * * * root docker compose --profile pipeline run --rm pipeline >> /var/log/trade-pipeline.log 2>&1
```

### Memory Budget (2GB VPS)

| Component | Limit | Typical Usage |
|-----------|-------|---------------|
| OS + Docker daemon | ~200 MB | Reserved |
| PostgreSQL + TimescaleDB | 256 MB | Shared buffers + connections |
| Telegram bot (always-on) | 192 MB | Idle most of the time |
| Pipeline (when running) | 1280 MB | ML models + DataFrames + API buffers |
| **Total** | **~1928 MB** | Fits in 2 GB |

Add 1GB swap as safety net:
```bash
fallocate -l 1G /swapfile && chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo 'vm.swappiness=10' >> /etc/sysctl.conf  # Only use swap under pressure
```

### Required API Keys

| Service | Key | How to Get | Required Phase |
|---------|-----|------------|----------------|
| OpenAI | `OPENAI_API_KEY` | platform.openai.com | Phase 2 |
| Telegram | `TELEGRAM_BOT_TOKEN` | @BotFather on Telegram | Phase 1 |
| Binance | `BINANCE_API_KEY` | binance.com/en/my/settings/api-management | Phase 1 |
| FRED | `FRED_API_KEY` | fred.stlouisfed.org/docs/api/api_key.html | Phase 3 |
| Finnhub | `FINNHUB_API_KEY` | finnhub.io/register | Phase 4 |
| Reddit | `REDDIT_CLIENT_ID/SECRET` | reddit.com/prefs/apps | Phase 4 |
| Etherscan | `ETHERSCAN_API_KEY` | etherscan.io/myapikey | Phase 5 |
| GitHub | `GITHUB_TOKEN` | github.com/settings/tokens (optional) | Phase 5 |
| CoinGecko | `COINGECKO_API_KEY` | coingecko.com (free Demo key) | Phase 1 |

### VPS Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 2 GB | 4 GB |
| Storage | 10 GB | 20 GB (price history grows, but TimescaleDB compression helps) |
| OS | Ubuntu 22.04+ | Ubuntu 24.04 |
| Cost | ~$5-6/mo (Hetzner) | ~$10/mo |

**Note:** 1GB RAM is NOT sufficient. ML models (XGBoost + ONNX) + pandas DataFrames + API buffers require 2GB minimum.

## Rate Limit Management Strategy

```python
class RateLimiter:
    """Per-API rate limit tracking with exponential backoff."""

    limits = {
        "yfinance":    {"calls": 200,  "period": 3600},     # Conservative — Yahoo throttles aggressively
        "ccxt":        {"calls": 1200, "period": 60},        # Binance: 1200/min
        "coingecko":   {"calls": 330,  "period": 86400},     # 10k/mo ÷ 30 (free Demo tier)
        "finnhub":     {"calls": 60,   "period": 60},        # 60/min
        "fred":        {"calls": 120,  "period": 60},        # 120/min
        "etherscan":   {"calls": 5,    "period": 1},         # 5/sec, 100k/day
        "litellm":     {"calls": 500,  "period": 60},        # Varies by provider
        "reddit":      {"calls": 100,  "period": 60},        # 100/min (authenticated)
        "github":      {"calls": 5000, "period": 3600},      # 5k/hr
    }
```

## Telegram Message Format

```
📊 *Daily Signal Report — 2026-03-23*

📋 *YESTERDAY'S SCORECARD:*
  BTC: Said BUY at $67,000 → $69,100 (+3.1%) ✅
  BBCA: Said HOLD at Rp9,850 → Rp9,825 (-0.3%) ✅
  ETH: Said SELL at $3,400 → $3,500 (+2.9%) ❌
  _Accuracy (30d): 68% | Streak: 4 correct_

━━━━━━━━━━━━━━━━━━

📈 *TODAY'S SIGNALS:*

*BTC/USDT — 🟢 STRONG BUY (0.72)*
├─ Technical: +0.8 _(bullish breakout)_
├─ On-Chain: +0.7 _(whale accumulation)_
├─ Sentiment: +0.6 _(greed, but not extreme)_
├─ Macro: +0.5 _(Fed dovish tone)_
├─ ML/AI: +0.6 _(XGBoost bullish)_
└─ _10 more categories..._
💬 _"Strong confluence. On-chain whale accumulation
confirms the technical breakout. No major risk events
in next 48h."_
⚠️ _Risk: BTC at resistance $70k, could reject._

*BBCA.JK — 🟡 HOLD (0.15)*
├─ Fundamental: +0.6 _(Q4 revenue +12% YoY)_
├─ Technical: -0.1 _(consolidating near MA50)_
├─ Macro: +0.4 _(BI rate stable at 5.75%)_
└─ _11 more categories..._
💬 _"Fundamentals are strong but waiting for breakout
above Rp10,200 resistance. BI meeting on Thursday —
holding until clarity."_
⏳ _Wait for: BI rate decision (2026-03-26)_

━━━━━━━━━━━━━━━━━━

💡 *LESSON APPLIED TODAY:*
_"When BI rate decision is within 48h, hold IDX
positions regardless of other signals."_
(Learned: 2026-03-10, applied 3 times, accuracy: 100%)

🔍 *NEW OPPORTUNITIES:*
• TLKM.JK — Volume surge +340%, momentum breakout
• SOL/USDT — On-chain TVL +25% this week
```
