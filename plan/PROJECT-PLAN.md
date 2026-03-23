# Trade Signal Agent — Project Plan

## Overview
Daily trading signal system that analyzes Indonesian stocks (IDX/IHSG) and global crypto across 15 categories, with LLM-powered final decisions, valuation analysis, portfolio risk monitoring, and self-evaluation feedback loop. Sends buy/sell/hold recommendations with fair value estimates via Telegram.

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
| 15 | Valuation (DCF, peer multiples, margin of safety) | ✅ | Partial |

Each engine outputs a score (-1 to +1), confidence (0 to 1), and reasoning text.
The valuation engine additionally outputs: fair value estimate, margin of safety %, and valuation verdict.

### F3 — LLM Final Decision Maker
- OpenAI GPT reads all 15 engine scores + valuation data + context
- Weighs signal timing (technicals) against valuation (is the price right?)
- Detects contradictions between signals (e.g., bullish technicals but overvalued)
- Considers upcoming events that could invalidate signals
- Applies lessons learned from past mistakes
- Considers due diligence flags (insider selling, management changes, earnings quality)
- Outputs: STRONG BUY / BUY / HOLD / SELL / STRONG SELL + reasoning + fair value context

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
- Today's signal for each watchlist asset (all 15 categories + LLM verdict)
- Valuation summary: fair value vs market price, margin of safety
- LLM reasoning for each decision
- Lessons applied today
- Portfolio risk snapshot (concentration, correlation alerts)
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
| `/valuation BBCA` | Show DCF, peer comparison, fair value estimate |
| `/compare BBCA BBRI BMRI` | Side-by-side sector peer comparison |
| `/duediligence BBCA` | Full DD report (ownership, management, moat) |
| `/portfolio` | Portfolio risk overview (correlation, concentration, VaR) |
| `/fundamentals BBCA` | Deep ratio dashboard with historical trends |

### F10 — Valuation Engine
Core analyst capability — answers "is this asset fairly priced?"
- **DCF Model (IDX stocks):**
  - Project future free cash flows from F5 financial data (revenue growth, margins, capex)
  - Estimate WACC using BI rate, equity risk premium, beta
  - Calculate intrinsic value per share → compare to market price
  - Output: margin of safety % (e.g., "BBCA trades 15% below fair value")
- **Comparable Company Analysis:**
  - Group IDX stocks by sector (banking, telco, consumer, mining)
  - Compare P/E, P/B, EV/EBITDA, ROE, dividend yield across sector peers
  - Flag outliers: "BBRI trades at 8x P/E vs banking sector avg 11x"
- **Crypto Valuation Proxies:**
  - NVT ratio (Network Value to Transactions) — already in on-chain, deepen it
  - Stock-to-flow model for BTC
  - Revenue multiples for DeFi protocols (TVL, fees generated)
- **Scenario Analysis:**
  - Bull / Base / Bear case projections per asset
  - Probability-weighted expected return
  - Sensitivity tables: "if BI rate rises 50bps, fair value drops 12%"
- **Quarter-over-Quarter Tracking:**
  - Track fundamental ratio trends across quarters (improving or deteriorating?)
  - Alert on significant changes: "TLKM debt-to-equity jumped from 0.4 to 0.7"

Each valuation outputs: fair value estimate, margin of safety %, valuation verdict (Undervalued / Fair / Overvalued), and confidence level.

### F11 — Due Diligence Module
Deep research capability for informed investment decisions.
- **Sector Benchmarking:**
  - Maintain sector classifications for all IHSG stocks
  - Compare company metrics against sector median and top quartile
  - Sector rotation signals: "banking sector P/E compressing while earnings grow"
- **Ownership & Insider Analysis (IDX):**
  - Parse IDX ownership structure filings (institutional, retail, insider %)
  - Track insider buying/selling patterns from IDX disclosures
  - Flag significant ownership changes: "foreign institutional ownership in BBCA dropped 5% this month"
- **Management Quality Scoring:**
  - Track CEO/CFO tenure and changes
  - Revenue and profit CAGR during current management period
  - Capital allocation quality: ROE vs cost of equity, dividend policy consistency
  - Corporate action history (rights issues, stock splits, buybacks)
- **Competitive Positioning:**
  - Market share data where available (e.g., banking assets, telco subscribers)
  - Moat indicators: sustained high ROE (>15%), stable margins, pricing power
  - Peer revenue growth comparison

### F12 — Portfolio Risk Monitor
Portfolio-level analysis — not just individual assets, but the whole picture.
- **Correlation Matrix:**
  - Daily correlation between all watchlist assets
  - Alert when correlations spike (diversification breakdown in stress)
  - Cross-market correlation: IDX stocks vs crypto holdings
- **Concentration Risk:**
  - Sector exposure breakdown (% in banking, tech, mining, crypto)
  - Single-asset concentration warnings
  - Geographic/currency exposure (IDR vs USD-denominated assets)
- **Risk Metrics:**
  - Portfolio VaR (Value at Risk) — daily and weekly
  - Maximum drawdown tracking
  - Sharpe ratio, Sortino ratio (risk-adjusted returns)
  - Beta vs IHSG for stock portion, vs BTC for crypto portion
- **Stress Testing:**
  - Historical scenarios: "how would this portfolio perform in March 2020 crash?"
  - Factor shocks: "what if rupiah depreciates 10%?"
  - Report worst-case drawdown estimates

### F13 — Enhanced Fundamental Deep Dive (IDX)
Upgrade F2 Category #1 from simple scores to full analyst-grade output.
- **Ratio Dashboard per Stock:**
  - Profitability: ROE, ROA, net margin, operating margin (5-year trend)
  - Leverage: debt-to-equity, interest coverage, current ratio, quick ratio
  - Efficiency: asset turnover, inventory turnover, receivable days
  - Growth: revenue CAGR (3yr/5yr), EPS growth, book value growth
- **Earnings Quality Analysis:**
  - Cash flow vs reported earnings divergence (accrual red flags)
  - Revenue recognition patterns
  - One-off items and adjusted earnings
- **Dividend Analysis:**
  - Payout ratio, dividend yield, dividend growth rate
  - Sustainability: FCF coverage of dividends
  - Dividend history and consistency

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

### Phase 10 — Valuation Engine (Week 10-11)
DCF model for IDX stocks using F5 financial data, comparable company analysis with sector peer grouping, crypto valuation proxies (NVT, S2F), scenario analysis (bull/base/bear), quarter-over-quarter ratio tracking with change alerts.

### Phase 11 — Enhanced Fundamentals + Due Diligence (Week 12)
Deep ratio dashboard (profitability, leverage, efficiency, growth trends), earnings quality analysis, dividend sustainability scoring, sector benchmarking framework, ownership/insider tracking from IDX filings, management quality scoring.

### Phase 12 — Portfolio Risk Monitor (Week 13)
Correlation matrix across all watchlist assets, concentration risk analysis, portfolio VaR and drawdown tracking, risk-adjusted return metrics (Sharpe, Sortino), stress testing with historical scenarios and factor shocks.

### Phase 13 — Asset Discovery (Week 14)
IDX screener, crypto screener, anomaly detection, opportunity recommendations.

### Phase 14 — Production Hardening (Week 15)
Error handling, rate limits, logging, VPS deployment, real-time alerts.
