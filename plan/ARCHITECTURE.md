# Trade Signal Agent — Architecture & Technical Design

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.11+ | Best ecosystem for finance (pandas, ta-lib), ML (scikit-learn, pytorch), and API integrations |
| Web Framework | FastAPI | Async support, Telegram webhook, lightweight |
| Database | PostgreSQL | Relational data (assets, signals, decisions), JSON columns for flexible data |
| ORM | SQLAlchemy 2.0 + Alembic | Type-safe models, migration management |
| Scheduler | APScheduler | In-process scheduling, cron-like syntax, persistent job store |
| Telegram | python-telegram-bot v20+ | Async, well-maintained, full Bot API support |
| LLM | OpenAI GPT-4o-mini | Final decision maker, news analysis, PDF parsing. ~$1/month |
| ML | scikit-learn, XGBoost | Traditional ML models (Random Forest, gradient boosting) |
| Deep Learning | PyTorch | LSTM for time-series prediction |
| Technical Analysis | pandas-ta | 130+ indicators, runs locally, no API needed |
| Data Processing | pandas, numpy | Data manipulation, numerical computation |
| PDF Parsing | pdfplumber | Extract text from IDX financial report PDFs |
| HTTP Client | httpx (async) | Async API calls with retry/timeout support |
| Containerization | Docker + Docker Compose | PostgreSQL + app in single deployment |
| Environment | python-dotenv | API key management via .env |

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        VPS (Docker Compose)                      │
│                                                                  │
│  ┌────────────┐    ┌──────────────────────────────────────────┐ │
│  │ PostgreSQL  │◄──►│            FastAPI App                   │ │
│  │             │    │                                          │ │
│  │ • assets    │    │  ┌─────────┐  ┌──────────┐  ┌────────┐ │ │
│  │ • signals   │    │  │Scheduler│  │  Engines │  │Telegram│ │ │
│  │ • decisions │    │  │(APSched)│─►│  (14x)   │─►│  Bot   │ │ │
│  │ • lessons   │    │  └─────────┘  └──────────┘  └────────┘ │ │
│  │ • prices    │    │       │            │             ▲      │ │
│  │ • news      │    │       ▼            ▼             │      │ │
│  │ • docs      │    │  ┌─────────┐  ┌──────────┐      │      │ │
│  └────────────┘    │  │Evaluator│  │   LLM    │──────┘      │ │
│                     │  │(feedback│  │ Decision │              │ │
│                     │  │  loop) │  │  Maker   │              │ │
│                     │  └─────────┘  └──────────┘              │ │
│                     └──────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
   ┌─────────────┐    ┌──────────────┐    ┌──────────────┐
   │ Market Data  │    │   LLM API    │    │   Telegram   │
   │              │    │              │    │     API      │
   │ • yfinance   │    │ • OpenAI     │    │              │
   │ • Binance    │    │   GPT-4o-    │    │ • Send msgs  │
   │ • CoinGecko  │    │   mini       │    │ • Receive    │
   │ • DeFiLlama  │    │              │    │   commands   │
   │ • Etherscan  │    └──────────────┘    └──────────────┘
   │ • FRED       │
   │ • RSS feeds  │
   │ • Bank Indo  │
   │ • idx.co.id  │
   │ • Reddit     │
   │ • GitHub     │
   └─────────────┘
```

## Daily Execution Flow

```
06:00  ┌─ SELF-EVALUATE
       │   ├─ Fetch current prices for yesterday's decisions
       │   ├─ Compare verdict vs actual price movement
       │   ├─ LLM analyzes: what went right/wrong?
       │   ├─ Extract lessons → store in DB
       │   └─ Update accuracy stats
       │
06:05  ├─ INGEST DATA (parallel)
       │   ├─ IDX stock prices ──────── yfinance (.JK)
       │   ├─ Crypto prices ─────────── Binance API
       │   ├─ Indonesian news ───────── Kontan/CNBC ID RSS
       │   ├─ Global news ──────────── Finnhub
       │   ├─ Macro Indonesia ───────── Bank Indonesia / BPS
       │   ├─ Macro Global ─────────── FRED
       │   ├─ On-chain ─────────────── DeFiLlama + Etherscan
       │   ├─ Sentiment ────────────── Reddit + Fear & Greed
       │   └─ Alt data ─────────────── GitHub API
       │
06:15  ├─ RUN SIGNAL ENGINES (parallel per asset)
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
       │   └─ Engine 14: Emerging ───── score + confidence + reasoning
       │
06:30  ├─ LLM FINAL DECISION (per asset)
       │   ├─ Input: all 14 scores + lessons + accuracy stats + context
       │   ├─ Output: verdict + score + confidence + reasoning + risk
       │   └─ Store decision in DB
       │
06:35  └─ SEND TELEGRAM REPORT
           ├─ Yesterday's scorecard
           ├─ Today's signals per asset
           ├─ LLM reasoning
           ├─ Lessons applied
           └─ New opportunities
```

## Data Sources — Detailed

### Indonesian Stocks (IDX)

| Data Type | Source | Endpoint / Method | Rate Limit | Python Library |
|-----------|--------|-------------------|------------|----------------|
| Stock prices | Yahoo Finance | yfinance `.JK` suffix | ~2k req/hr | `yfinance` |
| IHSG index | Yahoo Finance | `^JKSE` | ~2k req/hr | `yfinance` |
| Financial reports | idx.co.id | PDF download (scrape) | — | `httpx` + `pdfplumber` |
| Fundamentals (backup) | Yahoo Finance | yfinance `.info` | ~2k req/hr | `yfinance` |
| News | Kontan.co.id | RSS feed | Unlimited | `feedparser` |
| News | CNBC Indonesia | RSS feed | Unlimited | `feedparser` |
| News | Bisnis.com | RSS feed | Unlimited | `feedparser` |
| Sentiment | Stockbit | Web scrape | Be polite | `httpx` + `beautifulsoup4` |
| Sentiment | Reddit r/finansial | PRAW API | 60 req/min | `praw` |
| Macro | Bank Indonesia | BI API / scrape | — | `httpx` |
| Macro | BPS (Badan Pusat Statistik) | BPS API | — | `httpx` |

### Global Crypto

| Data Type | Source | Endpoint / Method | Rate Limit | Python Library |
|-----------|--------|-------------------|------------|----------------|
| Prices (real-time) | Binance | REST + WebSocket | 1200 req/min | `python-binance` |
| Prices (backup) | CoinGecko | REST API | 10k calls/mo | `httpx` |
| On-chain (DeFi) | DeFiLlama | REST API | Free, no key | `httpx` |
| On-chain (ETH) | Etherscan | REST API | 5 calls/sec | `httpx` |
| On-chain (BTC) | Mempool.space | REST API | Free | `httpx` |
| Sentiment | alternative.me | Fear & Greed API | Free | `httpx` |
| Sentiment | Reddit (r/cryptocurrency) | PRAW API | 60 req/min | `praw` |
| News | Finnhub | REST API | 60 calls/min | `httpx` |
| Alt data | GitHub | REST API | 5k req/hr | `httpx` |

### Shared / Global

| Data Type | Source | Endpoint / Method | Rate Limit | Python Library |
|-----------|--------|-------------------|------------|----------------|
| US macro (Fed rate, CPI) | FRED | REST API | 120 req/min | `fredapi` |
| Google Trends | Google Trends API | Official API | Varies | `httpx` |
| Technical indicators | Local computation | pandas-ta | No limit | `pandas-ta` |

## Database Schema

```sql
-- Core asset tracking
CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,          -- e.g., "BBCA", "BTC"
    name VARCHAR(100),                     -- e.g., "Bank Central Asia", "Bitcoin"
    asset_type VARCHAR(10) NOT NULL,       -- "stock" or "crypto"
    exchange VARCHAR(20),                  -- "IDX", "binance", etc.
    yfinance_symbol VARCHAR(20),           -- "BBCA.JK", "BTC-USD"
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(symbol, asset_type)
);

-- User watchlist
CREATE TABLE watchlist (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    asset_id INTEGER REFERENCES assets(id),
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(telegram_user_id, asset_id)
);

-- Historical price data (cached locally)
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id),
    date DATE NOT NULL,
    open DECIMAL(20, 8),
    high DECIMAL(20, 8),
    low DECIMAL(20, 8),
    close DECIMAL(20, 8),
    volume DECIMAL(20, 2),
    UNIQUE(asset_id, date)
);

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
    created_at TIMESTAMP DEFAULT NOW(),
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
    created_at TIMESTAMP DEFAULT NOW(),
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
    created_at TIMESTAMP DEFAULT NOW()
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
    created_at TIMESTAMP DEFAULT NOW()
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
    computed_at TIMESTAMP DEFAULT NOW()
);

-- Parsed financial documents (IDX)
CREATE TABLE financial_docs (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id),
    doc_type VARCHAR(20),                  -- "quarterly", "annual"
    period VARCHAR(10),                    -- "Q1-2026", "2025"
    file_path TEXT,
    source_url TEXT,
    parsed_data JSONB,                     -- GPT-extracted financials
    parsed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
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
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_price_history_asset_date ON price_history(asset_id, date DESC);
CREATE INDEX idx_signals_asset_date ON signals(asset_id, date DESC);
CREATE INDEX idx_decisions_asset_date ON daily_decisions(asset_id, date DESC);
CREATE INDEX idx_lessons_valid ON lessons(still_valid, asset_type);
CREATE INDEX idx_news_date ON news_events(date DESC);
```

## Project Structure

```
trade-agent/
├── plan/                              # Planning docs
│   ├── PROJECT-PLAN.md                # Overview + features
│   ├── ARCHITECTURE.md                # This document
│   └── price-prediction-methods.md    # Reference: all 215 methods
│
├── src/
│   ├── main.py                        # FastAPI entry point
│   ├── config.py                      # Settings via pydantic-settings
│   ├── scheduler.py                   # APScheduler daily jobs
│   │
│   ├── db/
│   │   ├── models.py                  # SQLAlchemy ORM models
│   │   ├── database.py                # Engine + session factory
│   │   └── migrations/               # Alembic migrations
│   │
│   ├── data/                          # Data fetchers (one per source)
│   │   ├── base.py                    # BaseFetcher abstract class
│   │   ├── idx_stocks.py             # IDX prices via yfinance .JK
│   │   ├── crypto.py                  # Binance + CoinGecko
│   │   ├── idx_fundamentals.py        # IDX PDF reports from idx.co.id
│   │   ├── onchain.py                 # DeFiLlama + Etherscan + Mempool
│   │   ├── sentiment.py               # Reddit PRAW + Stockbit + Fear&Greed
│   │   ├── news_id.py                 # Kontan, CNBC ID, Bisnis RSS
│   │   ├── news_global.py             # Finnhub
│   │   ├── macro_id.py                # Bank Indonesia + BPS
│   │   ├── macro_global.py            # FRED
│   │   └── options.py                 # CBOE (limited)
│   │
│   ├── engines/                       # Signal engines (one per category)
│   │   ├── base.py                    # BaseEngine abstract class
│   │   ├── fundamental.py             # 1. Fundamental analysis
│   │   ├── technical.py               # 2. Technical analysis
│   │   ├── quantitative.py            # 3. Quantitative/statistical
│   │   ├── ml_ai.py                   # 4. ML/AI (XGBoost + LSTM)
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
│   ├── llm/                           # All OpenAI GPT interactions
│   │   ├── client.py                  # OpenAI client wrapper + retry
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
│   └── bot/                           # Telegram interface
│       ├── telegram.py                # Bot initialization + webhook
│       ├── commands.py                # Command handlers
│       └── formatter.py               # Message formatting (markdown)
│
├── tests/
│   ├── test_engines/
│   ├── test_data/
│   ├── test_llm/
│   └── test_bot/
│
├── docker-compose.yml                 # PostgreSQL + app
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
```

### BaseEngine Interface

```python
from abc import ABC, abstractmethod

class BaseEngine(ABC):
    @abstractmethod
    async def analyze(self, asset: Asset, data: dict) -> Signal:
        """Run analysis and return a signal."""
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
        """Fetch with exponential backoff retry."""
        ...
```

## LLM Integration Design

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
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│         OpenAI GPT-4o-mini           │
│                                      │
│  System: "You are a senior trading   │
│  analyst..."                         │
│                                      │
│  Response format: JSON               │
│  Temperature: 0.3 (consistent)       │
└──────────────┬───────────────────────┘
               │
               ▼
        Parse JSON → Decision
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
│         OpenAI GPT-4o-mini           │
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
  pdfplumber → raw text
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

## LLM Cost Estimate (GPT-4o-mini)

| Usage | Calls/day | Input tokens | Output tokens | Est. cost/month |
|-------|-----------|-------------|---------------|-----------------|
| Final decision (per asset × 20) | 20 | ~2k each | ~300 each | $0.30 |
| Self-evaluation (per asset × 20) | 20 | ~1.5k each | ~400 each | $0.20 |
| News analysis (batch) | 5 | ~3k each | ~500 each | $0.10 |
| PDF parsing (quarterly) | ~2/quarter | ~5k each | ~1k each | $0.05 |
| Report generation | 1 | ~2k | ~500 | $0.05 |
| **Total** | | | | **~$0.70 - $1.50/mo** |

## Deployment Architecture (VPS)

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: trade_agent
      POSTGRES_USER: trade
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"

  app:
    build: .
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql+asyncpg://trade:${DB_PASSWORD}@db:5432/trade_agent
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      TELEGRAM_CHAT_ID: ${TELEGRAM_CHAT_ID}
      BINANCE_API_KEY: ${BINANCE_API_KEY}
      FRED_API_KEY: ${FRED_API_KEY}
      FINNHUB_API_KEY: ${FINNHUB_API_KEY}
      REDDIT_CLIENT_ID: ${REDDIT_CLIENT_ID}
      REDDIT_CLIENT_SECRET: ${REDDIT_CLIENT_SECRET}
      ETHERSCAN_API_KEY: ${ETHERSCAN_API_KEY}
    ports:
      - "8000:8000"

volumes:
  pgdata:
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

### VPS Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Storage | 10 GB | 20 GB (price history grows) |
| OS | Ubuntu 22.04+ | Ubuntu 24.04 |
| Cost | ~$5/mo (DigitalOcean, Hetzner) | ~$10/mo |

## Rate Limit Management Strategy

```python
class RateLimiter:
    """Per-API rate limit tracking with exponential backoff."""

    limits = {
        "yfinance":    {"calls": 2000, "period": 3600},    # ~2k/hr
        "binance":     {"calls": 1200, "period": 60},       # 1200/min
        "coingecko":   {"calls": 330,  "period": 86400},    # 10k/mo ÷ 30
        "finnhub":     {"calls": 60,   "period": 60},       # 60/min
        "fred":        {"calls": 120,  "period": 60},       # 120/min
        "etherscan":   {"calls": 5,    "period": 1},        # 5/sec
        "openai":      {"calls": 500,  "period": 60},       # varies by tier
        "reddit":      {"calls": 60,   "period": 60},       # 60/min
        "github":      {"calls": 5000, "period": 3600},     # 5k/hr
    }
```

## Error Handling Strategy

```
API call fails
     │
     ├─ Retry with exponential backoff (3 attempts)
     │
     ├─ If primary fails → try backup API
     │   (e.g., yfinance fails → skip; Binance fails → CoinGecko)
     │
     ├─ If all fail → engine returns Signal with confidence=0
     │   (LLM will see low confidence and downweight)
     │
     └─ Log error + alert via Telegram if critical
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
