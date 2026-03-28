# Trade Signal Agent

## What This Is

A daily trading signal system for Indonesian stocks (IDX/IHSG) and global crypto. Runs 15 analysis engines per asset, uses an LLM to synthesize a final verdict (STRONG BUY to STRONG SELL), evaluates its own past decisions to improve over time, and delivers reports via Telegram. Built for a small group of active traders.

## Core Value

The daily signal loop must work reliably: fetch data, run engines, produce LLM verdicts, and deliver a Telegram report every morning — even if only a few engines are active initially.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- [x] LLM final decision maker synthesizing all engine scores into a verdict — Validated in Phase 4: LLM Decision Maker
- [x] Watchlist management via Telegram commands (add/remove IDX stocks and crypto) — Validated in Phase 5: Telegram Bot & Daily Delivery
- [x] Daily Telegram report with signals and reasoning — Validated in Phase 5: Telegram Bot & Daily Delivery
- [x] Telegram bot commands (/start, /add, /remove, /watchlist, /report, /settings) — Validated in Phase 5: Telegram Bot & Daily Delivery

### Active

- [x] 15-category signal analysis engines (technical, fundamental, sentiment, on-chain, macro, etc.) — Validated in Phase 10: Remaining Specialized Engines
- [x] Each engine outputs score (-1 to +1), confidence (0-1), and reasoning — Validated in Phase 10: Remaining Specialized Engines
- [x] LLM final decision maker synthesizing all engine scores into a verdict (Phase 4)
- [x] Valuation engine with DCF, peer comparison, and fair value estimates — Validated in Phase 9: IDX Documents & Valuation Engine
- [x] Self-evaluation feedback loop — review yesterday's decisions, extract lessons, improve over time — Validated in Phase 7: Self-Evaluation Feedback Loop
- [x] Indonesian financial document (laporan keuangan) PDF parsing with GPT — Validated in Phase 9: IDX Documents & Valuation Engine
- [x] News-driven signals from Indonesian and global sources — Validated in Phase 8: Fundamental, Macro, Sentiment, and News Engines
- [ ] Asset discovery — scan IHSG and crypto for unusual volume, breakouts, anomalies
- [ ] Due diligence module (ownership, insider tracking, management quality, sector benchmarking)
- [ ] Portfolio risk monitor (correlation matrix, concentration risk, VaR, stress testing)
- [ ] Enhanced fundamental deep dive with ratio dashboards and earnings quality analysis

### Out of Scope

- Real-time / intraday trading signals — daily cadence only
- Mobile app — Telegram is the interface
- Multi-tenant SaaS with billing — small group, shared instance
- Automated trade execution — signals only, humans decide to act

## Context

- **Target markets:** IDX stocks (BBCA.JK, BBRI.JK, TLKM.JK, etc.) and global crypto (BTC/USDT, ETH/USDT, SOL/USDT)
- **Users:** Small group of active traders who want to systematize their analysis process
- **Priority:** Get the end-to-end daily signal loop working first, then deepen analysis engines incrementally
- **Infrastructure:** VPS ready, OpenAI API key available. Other API keys (Binance, FRED, Finnhub, Reddit, Etherscan, CoinGecko, Telegram) to be obtained as needed per phase
- **Existing work:** Detailed project plan and architecture docs in `plan/` directory — no implementation code yet

## Constraints

- **Tech stack:** Python 3.11+, FastAPI, PostgreSQL 16 + TimescaleDB, APScheduler, LiteLLM, pandas-ta, ccxt — as specified in `plan/ARCHITECTURE.md`
- **VPS budget:** 2GB RAM minimum, two-process model (bot always-on ~100MB, pipeline daily ~1GB peak)
- **LLM cost:** Target ~$0.50-1.00/month using GPT-4o-mini via LiteLLM
- **Data sources:** yfinance for IDX (.JK suffix), ccxt/Binance for crypto, RSS feeds for Indonesian news, FRED for macro
- **Sequential engine execution:** Process one asset through all engines, release memory, then next — keeps peak RAM under 1GB

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Two-process model (bot + pipeline) | Prevent ML model loading from blocking Telegram commands | — Pending |
| LiteLLM for model abstraction | Swap between GPT-4o-mini, Gemini Flash, DeepSeek without code changes | — Pending |
| TimescaleDB hypertables for price data | Auto-partitioning, compression (90%+ savings), time_bucket queries | — Pending |
| Sequential engine execution per asset | CPU-bound work on 1-2 vCPU, no parallelism gain, keeps RAM manageable | — Pending |
| ONNX Runtime for LSTM inference | ~50MB vs PyTorch's ~2GB, train offline and deploy lightweight | — Pending |
| asyncpg for hot paths, SQLAlchemy for relational | Raw asyncpg ~0.1ms/query for price reads, SQLAlchemy for type safety elsewhere | — Pending |

---
*Last updated: 2026-03-29 after Phase 14 (Pipeline Runner Wiring Fixes) completion*
