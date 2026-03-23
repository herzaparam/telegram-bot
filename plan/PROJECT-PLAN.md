# Trade Signal Agent — Project Plan

## Overview
Daily trading signal system that analyzes Indonesian stocks (IDX/IHSG) and global crypto across 14 categories, with LLM-powered final decisions and self-evaluation feedback loop. Sends buy/sell/hold recommendations via Telegram.

## Market Scope

| Market | Scope | Examples |
|--------|-------|---------|
| Indonesian Stocks (IDX) | IHSG index + individual stocks | BBCA.JK, BBRI.JK, TLKM.JK, ASII.JK, UNVR.JK |
| Global Crypto | All major coins, global pairs | BTC/USDT, ETH/USDT, SOL/USDT |

## Features

### F1 — Watchlist Management
- Add/remove Indonesian stocks and crypto assets
- Manage personal watchlist via Telegram commands
- Support IDX symbols (BBCA, BBRI) and crypto symbols (BTC, ETH)

### F2 — 14-Category Signal Analysis
Run all 14 analysis categories daily for each watchlist asset:

| # | Category | Stock (IDX) | Crypto |
|---|----------|:-----------:|:------:|
| 1 | Fundamental Analysis (P/E, P/B, revenue growth, ROE) | ✅ | — |
| 2 | Technical Analysis (RSI, MACD, Bollinger, MA, volume) | ✅ | ✅ |
| 3 | Quantitative/Statistical (momentum, mean reversion, ARIMA) | ✅ | ✅ |
| 4 | ML/AI (XGBoost, LSTM, ensemble) | ✅ | ✅ |
| 5 | Sentiment (Reddit, Stockbit, Fear & Greed, Google Trends) | ✅ | ✅ |
| 6 | On-Chain (TVL, whale tracking, exchange flows, NVT) | — | ✅ |
| 7 | Options (put/call ratio, max pain) | Limited | — |
| 8 | Behavioral (volume anomaly, herding detection) | ✅ | ✅ |
| 9 | Event-Driven (earnings calendar, BI meetings, halving) | ✅ | ✅ |
| 10 | Alternative Data (GitHub activity, Google Trends) | — | ✅ |
| 11 | Network/Graph (correlation analysis between assets) | ✅ | ✅ |
| 12 | Macro/Economic (BI rate, Fed rate, CPI, DXY, rupiah) | ✅ | ✅ |
| 13 | Game Theory (order book imbalance, whale patterns) | ✅ | ✅ |
| 14 | Emerging (fractal dimension, wavelet analysis) | ✅ | ✅ |

Each engine outputs a score (-1 to +1), confidence (0 to 1), and reasoning text.

### F3 — LLM Final Decision Maker
- OpenAI GPT reads all 14 engine scores + context
- Detects contradictions between signals
- Considers upcoming events that could invalidate signals
- Applies lessons learned from past mistakes
- Outputs: STRONG BUY / BUY / HOLD / SELL / STRONG SELL + reasoning

### F4 — Self-Evaluation Feedback Loop
- Every morning, review yesterday's decisions against actual prices
- LLM analyzes what it got right/wrong and why
- Extracts concrete lessons (e.g., "downweight signals 24h before BI meeting")
- Stores lessons in database, feeds them into future decisions
- Tracks accuracy stats over time (win rate, best/worst engine)
- System gets smarter over time

### F5 — Indonesian Financial Document Analysis
- Download laporan keuangan (quarterly/annual) from idx.co.id
- GPT parses PDF reports in Bahasa Indonesia
- Extracts revenue, net profit, debt, cash flow, management outlook
- Feeds into fundamental engine for IDX stocks

### F6 — News-Driven Signals
- Ingest Indonesian financial news (Kontan, CNBC Indonesia, Bisnis)
- Ingest global crypto/financial news (Finnhub)
- LLM scores news impact per asset (e.g., "BI cuts rate → bullish for IDX")
- Daily digest included in report
- (Later) Real-time alerts for high-impact events

### F7 — Daily Telegram Report
Daily notification containing:
- Yesterday's scorecard (was I right or wrong? accuracy stats)
- Today's signal for each watchlist asset (all 14 categories + LLM verdict)
- LLM reasoning for each decision
- Lessons applied today
- New opportunities discovered

### F8 — Asset Discovery
- Scan all IHSG stocks for opportunities (unusual volume, breakouts)
- Scan crypto market for top movers, anomalies
- Recommend new assets based on signal strength
- "New Opportunities" section in daily report

### F9 — Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome + setup |
| `/watchlist` | Show current watchlist |
| `/add BBCA` or `/add BTC` | Add asset to watchlist |
| `/remove BBCA` | Remove asset |
| `/report` | Get today's full report on demand |
| `/report BTC` | Get detailed report for one asset |
| `/scorecard` | Show accuracy stats + recent results |
| `/lessons` | Show learned lessons |
| `/discover` | Show today's opportunities |
| `/settings` | Configure notification time, categories |
| `/backtest BTC 30d` | Run backtest on signals |

## Build Phases

### Phase 1 — Foundation (Week 1)
Project setup, database, IDX/crypto price fetchers, basic Telegram bot, scheduler.

### Phase 2 — Technical Engine + First Signal (Week 2)
Technical analysis engine (pandas-ta), first daily notification with technical signals.

### Phase 3 — Fundamental + Macro + IDX Docs (Week 3)
IDX PDF parser with GPT, fundamental engine, macro engine (BI + FRED).

### Phase 4 — Sentiment + News (Week 4)
Indonesian + global news fetchers, LLM news analyzer, sentiment engine.

### Phase 5 — On-Chain + Alt Data (Week 5)
On-chain engine for crypto, alt data engine (GitHub activity).

### Phase 6 — Quantitative + Options (Week 6)
Quantitative engine (momentum, ARIMA), options engine.

### Phase 7 — Remaining Engines (Week 7)
Behavioral, event-driven, network, game theory, emerging methods engines.

### Phase 8 — ML/AI Engine (Week 8)
Feature engineering, XGBoost, LSTM, ensemble model, backtesting.

### Phase 9 — Self-Evaluation Feedback Loop (Week 9)
Decision tracking, self-evaluation, lesson extraction, accuracy stats.

### Phase 10 — Asset Discovery (Week 10)
IDX screener, crypto screener, anomaly detection, opportunity recommendations.

### Phase 11 — Production Hardening (Week 11)
Error handling, rate limits, logging, VPS deployment, real-time alerts.
