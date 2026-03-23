# Architecture Patterns

**Domain:** Daily trading signal system (IDX stocks + global crypto)
**Researched:** 2026-03-23

## Recommended Architecture

The system follows a **two-process batch pipeline** architecture, which is the correct pattern for a daily-cadence signal system on a 2GB VPS. This is not an HFT system -- latency is irrelevant, resource efficiency is everything.

```
                    ┌─────────────────────────────────┐
                    │          PostgreSQL 16           │
                    │         + TimescaleDB            │
                    │                                  │
                    │  Hypertables: price_history      │
                    │  Relational: assets, signals,    │
                    │    decisions, evaluations,       │
                    │    lessons, watchlist, news,     │
                    │    pipeline_runs                 │
                    └──────┬──────────────┬────────────┘
                           │              │
              ┌────────────┘              └────────────┐
              │                                        │
    ┌─────────▼──────────┐              ┌──────────────▼──────────┐
    │  PROCESS 1: BOT    │              │  PROCESS 2: PIPELINE    │
    │  (always-on ~100MB)│              │  (daily cron ~1GB peak) │
    │                    │              │                         │
    │  FastAPI webhook   │              │  Stage 1: Evaluate      │
    │  Telegram commands │              │  Stage 2: Ingest        │
    │  On-demand reports │              │  Stage 3: Analyze       │
    │  /health endpoint  │              │  Stage 4: Decide        │
    │                    │              │  Stage 5: Report        │
    └────────────────────┘              └─────────────────────────┘
              │                                   │
              ▼                                   ▼
    ┌────────────────┐              ┌──────────────────────────┐
    │  Telegram API  │              │  External APIs           │
    │  (send/receive)│              │  yfinance, ccxt, FRED,   │
    │                │              │  RSS, DeFiLlama, LLM     │
    └────────────────┘              └──────────────────────────┘
```

### Why Two Processes, Not One

This is the single most important architectural decision. Rationale:

1. **Memory isolation** -- The pipeline loads ML models, DataFrames, and ONNX runtimes that spike to ~1GB. The bot must remain responsive at ~100MB. Combining them risks OOM on a 2GB VPS.
2. **Failure isolation** -- If the pipeline crashes mid-analysis, the bot continues responding to `/report` commands with yesterday's data. No downtime for users.
3. **Scheduling simplicity** -- The pipeline runs via system cron or APScheduler. No complex process management within a single application.
4. **PostgreSQL as the integration bus** -- Both processes read/write the same database. No message queues, no IPC, no ZeroMQ. The database IS the shared state. This is the right call for a daily-cadence system where real-time communication between processes is unnecessary.

### Component Boundaries

| Component | Responsibility | Communicates With | Process |
|-----------|---------------|-------------------|---------|
| **Telegram Bot** | Receive commands, serve reports, manage watchlist | PostgreSQL, Telegram API | Bot |
| **FastAPI Webhook** | HTTP endpoint for Telegram updates + /health | Telegram Bot handlers | Bot |
| **Pipeline Orchestrator** | Stage sequencing, idempotent restart, progress tracking | All pipeline stages, PostgreSQL | Pipeline |
| **Data Fetchers** | Retrieve market data from external APIs | External APIs, PostgreSQL (write) | Pipeline |
| **Signal Engines (x15)** | Compute score/confidence/reasoning per asset | PostgreSQL (read data, write signals) | Pipeline |
| **LLM Decision Maker** | Synthesize 15 engine outputs into verdict | LiteLLM (external LLM), PostgreSQL | Pipeline |
| **Self-Evaluator** | Compare past decisions to actual outcomes | PostgreSQL, LiteLLM | Pipeline |
| **Report Generator** | Format daily report for Telegram delivery | PostgreSQL (read), Telegram API (send) | Pipeline |

### Data Flow

The daily pipeline follows a strict linear flow. Each stage writes to PostgreSQL before the next stage reads from it. This makes every stage independently restartable.

```
EVALUATE (review yesterday)
    │
    ├─ Read: yesterday's decisions + current prices
    ├─ Call: LLM to analyze what went right/wrong
    ├─ Write: evaluations, lessons, accuracy_stats
    │
    ▼
INGEST (fetch fresh data)
    │
    ├─ Read: watchlist (which assets to fetch)
    ├─ Call: yfinance, ccxt, RSS, FRED, DeFiLlama, etc.
    ├─ Write: price_history, news_events, raw data tables
    │
    ▼
ANALYZE (run 15 engines sequentially per asset)
    │
    ├─ Read: price_history, news, macro data from DB
    ├─ Compute: technical indicators, ML predictions, sentiment scores
    ├─ Write: signals (one row per engine per asset per day)
    ├─ Memory: load one asset, run all engines, gc.collect(), next asset
    │
    ▼
DECIDE (LLM synthesis)
    │
    ├─ Read: all signals for today, lessons from evaluator
    ├─ Call: LiteLLM with structured prompt
    ├─ Write: daily_decisions (verdict, reasoning, confidence)
    │
    ▼
REPORT (deliver to users)
    │
    ├─ Read: decisions, evaluations, accuracy_stats
    ├─ Format: Markdown report with scorecard + signals
    ├─ Call: Telegram API (send message)
    └─ Write: pipeline_runs (stage=report, status=completed)
```

**Critical: Evaluate runs FIRST, before ingesting new data.** This ensures yesterday's decisions are reviewed against the most recent prices before new data overwrites context. This ordering is correct in the existing plan.

### Key Data Flow Rules

1. **Database as truth** -- No in-memory state survives between stages. If the pipeline crashes after INGEST, ANALYZE can restart by reading from the database.
2. **One asset at a time through engines** -- Load asset data into memory, run all 15 engines, write signals, release memory, gc.collect(). This caps peak RAM at ~1GB instead of loading all assets simultaneously.
3. **Async for I/O, sync for CPU** -- Data fetching and LLM calls use asyncio with semaphores. Engine execution is synchronous (CPU-bound work on 1-2 vCPU gains nothing from async).
4. **Idempotent stages** -- `pipeline_runs` table tracks which stage completed for which date. Re-running a completed stage is a no-op. Failed stages resume from the last successful asset.

## Patterns to Follow

### Pattern 1: Engine Interface Contract

Every signal engine implements the same interface. This is non-negotiable for the LLM synthesis step to work uniformly.

**What:** All 15 engines return identical output structure.
**When:** Every engine, no exceptions.
**Example:**
```python
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class EngineResult:
    score: float          # -1.0 (strong sell) to +1.0 (strong buy)
    confidence: float     # 0.0 (no data) to 1.0 (high confidence)
    reasoning: str        # Human-readable explanation
    indicators: dict      # Raw indicator values for auditability
    data_quality: dict    # Which sources were available vs failed

class BaseEngine(ABC):
    @abstractmethod
    async def analyze(self, asset_id: int, date: date) -> EngineResult:
        """Analyze a single asset. Read data from DB, return result."""
        ...

    def supports_asset_type(self, asset_type: str) -> bool:
        """Return False for engines that don't apply (e.g., on-chain for stocks)."""
        return True
```

### Pattern 2: Graceful Degradation Per Engine

**What:** If an engine fails or has no data, it returns score=0, confidence=0 instead of crashing the pipeline.
**When:** Always. A missing RSS feed should not prevent technical analysis from running.
**Example:**
```python
class TechnicalEngine(BaseEngine):
    async def analyze(self, asset_id: int, date: date) -> EngineResult:
        try:
            prices = await self.db.get_prices(asset_id, lookback=200)
            if len(prices) < 20:
                return EngineResult(
                    score=0.0, confidence=0.0,
                    reasoning="Insufficient price history",
                    indicators={}, data_quality={"status": "insufficient_data"}
                )
            # ... compute indicators ...
        except Exception as e:
            logger.error(f"Technical engine failed for asset {asset_id}: {e}")
            return EngineResult(
                score=0.0, confidence=0.0,
                reasoning=f"Engine error: {str(e)}",
                indicators={}, data_quality={"status": "error", "error": str(e)}
            )
```

### Pattern 3: Pipeline State Machine

**What:** Track pipeline progress in the database so stages are idempotent and restartable.
**When:** Every stage transition.
**Example:**
```python
class PipelineRunner:
    async def run_stage(self, stage: str, run_date: date):
        existing = await self.db.get_pipeline_run(run_date, stage)
        if existing and existing.status == "completed":
            logger.info(f"Stage {stage} already completed for {run_date}, skipping")
            return

        await self.db.upsert_pipeline_run(run_date, stage, status="running")
        try:
            await self.stages[stage].execute(run_date)
            await self.db.upsert_pipeline_run(run_date, stage, status="completed")
        except Exception as e:
            await self.db.upsert_pipeline_run(
                run_date, stage, status="failed",
                metadata={"error": str(e), "last_asset": self.current_asset}
            )
            raise
```

### Pattern 4: LLM Structured Output via Pydantic

**What:** Use LiteLLM's structured output to guarantee the LLM returns parseable decisions, not free-form text.
**When:** All LLM calls that produce data (decisions, evaluations, news scores).
**Example:**
```python
from pydantic import BaseModel
from enum import Enum

class Verdict(str, Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

class LLMDecision(BaseModel):
    verdict: Verdict
    score: float
    confidence: float
    reasoning: str
    key_factors: list[str]
    risk_warning: str
    wait_for: str | None = None

# LiteLLM call with response_format
response = await litellm.acompletion(
    model="gpt-4o-mini",
    messages=[...],
    response_format=LLMDecision,
)
```

### Pattern 5: Lesson Injection into LLM Context

**What:** Feed past lessons into the decision-making prompt so the system improves over time.
**When:** Every decision call.
**Architecture implication:** The self-evaluation loop is not cosmetic -- it produces structured lessons stored in DB that are retrieved and injected into the next day's LLM prompt.

```
PROMPT = """
You are a trading analyst. Given these 15 engine signals for {asset}:

{engine_signals}

And these lessons from past mistakes:
{lessons}

Recent accuracy: {accuracy_stats}

Produce a trading verdict.
"""
```

This is the "self-improving" mechanism. It relies on:
- Evaluation running before decisions (correct stage order)
- Lessons being stored with asset_type tags for relevance filtering
- A lesson pruning mechanism (mark `still_valid=False` for outdated lessons)

## Anti-Patterns to Avoid

### Anti-Pattern 1: Microservices for a Single-User System
**What:** Splitting engines, fetchers, LLM calls into separate services with REST APIs between them.
**Why bad:** On a 2GB VPS with one daily run, the overhead of HTTP serialization, service discovery, and container orchestration vastly exceeds any benefit. You have one user group, one database, and 30 minutes of daily compute.
**Instead:** Monorepo with clear module boundaries. Import, don't HTTP call.

### Anti-Pattern 2: Real-Time Event Streaming
**What:** Using Kafka, Redis Streams, or WebSockets for data flow between pipeline stages.
**Why bad:** This is a batch system that runs once a day. Streaming infrastructure adds complexity and memory overhead for zero benefit.
**Instead:** PostgreSQL as the integration layer. Write to a table, read from a table.

### Anti-Pattern 3: Loading All Assets Into Memory Simultaneously
**What:** `all_data = [fetch(asset) for asset in watchlist]` followed by parallel engine execution.
**Why bad:** 20 assets x 200 days x OHLCV + indicators can exceed 1GB easily. On a 2GB VPS (minus OS, DB, bot), this causes OOM kills.
**Instead:** Sequential per-asset processing with explicit `gc.collect()` between assets.

### Anti-Pattern 4: Storing LLM Prompts Inline
**What:** Building prompts with f-strings scattered across engine and decision-maker code.
**Why bad:** Prompt engineering is the most iterative part of this system. Buried prompts are hard to find, test, and version.
**Instead:** Centralized `prompts.py` module with named prompt templates. Version prompts alongside code.

### Anti-Pattern 5: Coupling the Bot to Pipeline Internals
**What:** Bot directly calling engine functions or importing pipeline modules.
**Why bad:** The bot must remain lightweight (~100MB). Importing engine dependencies (pandas, pandas-ta, onnxruntime) defeats the two-process isolation.
**Instead:** Bot reads only from PostgreSQL. All "smart" work happens in the pipeline process.

## Scalability Considerations

| Concern | At 5 assets | At 20 assets | At 100 assets |
|---------|-------------|--------------|---------------|
| Pipeline duration | ~5 min | ~20-30 min | ~2-3 hours |
| Peak RAM | ~300MB | ~1GB | Need 4GB+ VPS |
| LLM cost/day | ~$0.01 | ~$0.03-0.05 | ~$0.15-0.25 |
| DB storage/year | ~50MB | ~200MB | ~1GB |
| Telegram report | 1 message | 2-3 messages | Split by category |

**Scaling inflection points:**
- **>20 assets:** Consider parallel engine execution with `ProcessPoolExecutor` (uses multiple cores)
- **>50 assets:** Need to batch LLM calls or switch to cheaper models for lower-priority assets
- **>100 assets:** Split into asset tiers (full analysis vs lightweight screening)
- **Never needed:** Microservices, Kubernetes, message queues. This system tops out well before those are justified.

## Suggested Build Order (Dependencies)

The architecture has clear dependency chains that dictate build order:

```
Phase 1: Foundation (nothing depends on, everything depends on this)
├── Database schema + TimescaleDB setup
├── Config management (pydantic-settings)
├── Project structure (src/ layout)
└── Docker Compose (postgres + app)

Phase 2: Data Layer (Pipeline needs data before analysis)
├── Base fetcher interface
├── IDX stock fetcher (yfinance)
├── Crypto fetcher (ccxt)
└── Price storage in TimescaleDB

Phase 3: First Engine + Pipeline Shell
├── Pipeline orchestrator (stage runner, idempotent restart)
├── Base engine interface
├── Technical engine (easiest, pure computation, no external API)
└── End-to-end: fetch → store → analyze (1 engine) → store signal

Phase 4: LLM Integration
├── LiteLLM client wrapper
├── Decision maker (works even with 1 engine)
├── Structured output parsing
└── End-to-end: fetch → analyze → decide → store decision

Phase 5: Telegram Bot
├── FastAPI webhook
├── Watchlist commands (/add, /remove, /watchlist)
├── Report command (/report) reading from DB
├── Daily report delivery (triggered after pipeline Stage 5)
└── Two-process deployment verified

Phase 6: Self-Evaluation Loop
├── Evaluator (compare decision vs actual price)
├── Lesson extraction via LLM
├── Lesson injection into decision prompts
└── Accuracy stats computation

Phase 7+: Additional Engines (incremental, order flexible)
├── Fundamental engine (needs IDX financial data)
├── Sentiment engine (needs Reddit/RSS integration)
├── Macro engine (needs FRED integration)
├── ML/AI engine (needs training pipeline, ONNX export)
├── On-chain engine (needs DeFiLlama/Etherscan)
└── ... remaining engines
```

**Why this order:**
1. **Database first** because every other component reads/writes to it
2. **Data fetchers before engines** because engines need data to analyze
3. **One engine before LLM** because you need signal output to test LLM integration
4. **LLM before Telegram** because the report needs decisions to display
5. **Telegram before self-evaluation** because you want a working daily loop before adding the feedback mechanism
6. **Additional engines last** because each is independently valuable and the system works with even one engine

## Infrastructure Architecture

### Docker Compose Layout

```yaml
services:
  db:
    image: timescale/timescaledb:latest-pg16
    volumes: [pgdata:/var/lib/postgresql/data]
    # 512MB shared_buffers for 2GB VPS

  bot:
    build: .
    command: python -m src.bot.main
    depends_on: [db]
    restart: always
    # Always running, ~100MB

  pipeline:
    build: .
    command: python -m src.pipeline.main
    depends_on: [db]
    restart: "no"
    # Triggered by cron or APScheduler inside bot
```

**Open question:** Whether the pipeline should be triggered by system cron (simpler, external) or APScheduler inside the bot process (more observable, but couples bot to pipeline lifecycle). Recommendation: Start with system cron (`0 6 * * * docker compose run pipeline`), migrate to APScheduler if observability becomes important.

### Memory Budget (2GB VPS)

| Component | Idle | Peak | Notes |
|-----------|------|------|-------|
| Linux OS + Docker | ~200MB | ~300MB | Baseline |
| PostgreSQL + TimescaleDB | ~150MB | ~400MB | shared_buffers=128MB |
| Telegram Bot | ~80MB | ~120MB | FastAPI + python-telegram-bot |
| Pipeline | 0 (not running) | ~1GB | One asset at a time, gc.collect() |
| **Total** | ~430MB | ~1.8GB | Fits in 2GB with ~200MB headroom |

This is tight. The sequential-per-asset pattern is mandatory, not optional.

## Sources

- [Quant Trading Systems: Architecture & Infrastructure](https://mbrenndoerfer.com/writing/quant-trading-system-architecture-infrastructure)
- [Trading System Architecture Guide](https://gegobyteapps.com/resources/trading-system-architecture)
- [TradingAgents: Multi-Agents LLM Financial Trading Framework](https://arxiv.org/abs/2412.20138)
- [TradingGroup: Multi-Agent Trading with Self-Reflection](https://arxiv.org/html/2508.17565v1)
- [Scaling a trading bot with a time-series database (QuestDB)](https://questdb.com/blog/scaling-trading-bot-with-time-series-database/)
- [Algorithmic Trading System Architecture (Turing Finance)](https://www.turingfinance.com/algorithmic-trading-system-architecture-post/)
- Existing project plan: `plan/ARCHITECTURE.md`, `plan/PROJECT-PLAN.md`
