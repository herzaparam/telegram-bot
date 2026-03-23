# Requirements: Trade Signal Agent

**Defined:** 2026-03-23
**Core Value:** The daily signal loop must work reliably: fetch data, run engines, produce LLM verdicts, and deliver a Telegram report every morning

## v1 Requirements

### Data Infrastructure

- [ ] **DATA-01**: System stores daily OHLCV price history in TimescaleDB hypertables with auto-compression after 30 days
- [ ] **DATA-02**: System fetches IDX stock prices via yfinance (.JK suffix) with aggressive caching
- [ ] **DATA-03**: System fetches crypto OHLCV via ccxt (Binance) with CoinGecko metadata backup
- [ ] **DATA-04**: Pipeline stages are idempotent and restartable from point of failure
- [x] **DATA-05**: Pipeline tracks execution state in pipeline_runs table
- [ ] **DATA-06**: System classifies data sources by tier (critical/important/supplementary) and degrades gracefully on failure

### Watchlist

- [ ] **WTCH-01**: User can add IDX stocks and crypto assets to personal watchlist via Telegram
- [ ] **WTCH-02**: User can remove assets from watchlist via Telegram
- [ ] **WTCH-03**: User can view current watchlist via `/watchlist` command

### Signal Engines

- [ ] **ENGN-01**: Technical analysis engine (RSI, MACD, Bollinger, MA, volume) outputs score/confidence/reasoning
- [ ] **ENGN-02**: Fundamental analysis engine (P/E, P/B, revenue growth, ROE) for IDX stocks
- [ ] **ENGN-03**: Quantitative/statistical engine (momentum, mean reversion, ARIMA)
- [ ] **ENGN-04**: ML/AI engine (XGBoost, LSTM via ONNX, ensemble)
- [ ] **ENGN-05**: Sentiment engine (Reddit, Stockbit, Fear & Greed)
- [ ] **ENGN-06**: On-chain engine for crypto (TVL, whale tracking, exchange flows, NVT)
- [ ] **ENGN-07**: Options engine (put/call ratio, max pain) — limited scope
- [ ] **ENGN-08**: Behavioral engine (volume anomaly, herding detection)
- [ ] **ENGN-09**: Event-driven engine (earnings calendar, BI meetings, halving)
- [ ] **ENGN-10**: Alternative data engine (GitHub activity) for crypto
- [ ] **ENGN-11**: Network/graph engine (correlation analysis between assets)
- [ ] **ENGN-12**: Macro/economic engine (BI rate, Fed rate, CPI, DXY, rupiah)
- [ ] **ENGN-13**: Game theory engine (order book imbalance, whale patterns)
- [ ] **ENGN-14**: Emerging methods engine (fractal dimension, wavelet analysis)
- [ ] **ENGN-15**: Valuation engine (DCF, peer multiples, margin of safety) with fair value estimates

### LLM Decision Maker

- [ ] **LLM-01**: LLM reads all 15 engine scores + valuation data + context to produce final verdict
- [ ] **LLM-02**: LLM detects contradictions between signals (e.g., bullish technicals but overvalued)
- [ ] **LLM-03**: LLM considers upcoming events that could invalidate signals
- [ ] **LLM-04**: LLM applies lessons learned from past mistakes
- [ ] **LLM-05**: LLM outputs STRONG BUY / BUY / HOLD / SELL / STRONG SELL + reasoning + fair value context
- [ ] **LLM-06**: LLM considers due diligence flags (insider selling, management changes, earnings quality)

### Self-Evaluation

- [ ] **EVAL-01**: System reviews yesterday's decisions against actual prices every morning
- [ ] **EVAL-02**: LLM analyzes what went right/wrong and why
- [ ] **EVAL-03**: System extracts concrete lessons and stores in database
- [ ] **EVAL-04**: Lessons feed into future LLM decisions automatically
- [ ] **EVAL-05**: System tracks accuracy stats over time (win rate, best/worst engine)

### IDX Documents

- [ ] **IDXD-01**: System downloads laporan keuangan (quarterly/annual) from idx.co.id
- [ ] **IDXD-02**: GPT parses PDF reports in Bahasa Indonesia
- [ ] **IDXD-03**: System extracts revenue, net profit, debt, cash flow, management outlook

### News

- [ ] **NEWS-01**: System ingests Indonesian financial news (Kontan, CNBC Indonesia, Bisnis) via RSS
- [ ] **NEWS-02**: System ingests global crypto/financial news (Finnhub)
- [ ] **NEWS-03**: LLM scores news impact per asset
- [ ] **NEWS-04**: Daily digest of relevant news included in report

### Telegram Bot

- [ ] **TBOT-01**: `/start` welcome + setup
- [ ] **TBOT-02**: `/report` gets today's full report on demand
- [ ] **TBOT-03**: `/report BTC` gets detailed single-asset report
- [ ] **TBOT-04**: `/scorecard` shows accuracy stats + recent results
- [ ] **TBOT-05**: `/lessons` shows learned lessons
- [ ] **TBOT-06**: `/discover` shows today's opportunities
- [ ] **TBOT-07**: `/settings` configures notification time, categories
- [ ] **TBOT-08**: `/backtest BTC 30d` runs historical signal replay
- [ ] **TBOT-09**: `/valuation BBCA` shows DCF, peer comparison, fair value
- [ ] **TBOT-10**: `/compare BBCA BBRI BMRI` side-by-side sector comparison
- [ ] **TBOT-11**: `/duediligence BBCA` full DD report
- [ ] **TBOT-12**: `/portfolio` portfolio risk overview
- [ ] **TBOT-13**: `/fundamentals BBCA` deep ratio dashboard

### Daily Report

- [ ] **REPT-01**: Yesterday's scorecard (was I right/wrong, accuracy stats)
- [ ] **REPT-02**: Today's signal for each watchlist asset (all 15 categories + LLM verdict)
- [ ] **REPT-03**: Valuation summary (fair value vs market price, margin of safety)
- [ ] **REPT-04**: LLM reasoning for each decision
- [ ] **REPT-05**: Lessons applied today
- [ ] **REPT-06**: Portfolio risk snapshot (concentration, correlation alerts)
- [ ] **REPT-07**: New opportunities discovered

### Valuation Engine

- [ ] **VALN-01**: DCF model for IDX stocks using parsed financial data
- [ ] **VALN-02**: Comparable company analysis with sector peer grouping
- [ ] **VALN-03**: Crypto valuation proxies (NVT ratio, stock-to-flow for BTC, revenue multiples for DeFi)
- [ ] **VALN-04**: Scenario analysis (bull/base/bear) with probability-weighted returns
- [ ] **VALN-05**: Quarter-over-quarter ratio tracking with change alerts

### Due Diligence

- [ ] **DUED-01**: Sector benchmarking — compare company metrics against sector median
- [ ] **DUED-02**: Ownership & insider analysis from IDX disclosure filings
- [ ] **DUED-03**: Management quality scoring (tenure, CAGR, capital allocation)
- [ ] **DUED-04**: Competitive positioning (market share, moat indicators)

### Portfolio Risk

- [ ] **RISK-01**: Correlation matrix across all watchlist assets with spike alerts
- [ ] **RISK-02**: Concentration risk analysis (sector, single-asset, currency exposure)
- [ ] **RISK-03**: Portfolio VaR (daily and weekly), maximum drawdown tracking
- [ ] **RISK-04**: Risk-adjusted return metrics (Sharpe ratio, Sortino ratio)
- [ ] **RISK-05**: Stress testing with historical scenarios and factor shocks

### Asset Discovery

- [ ] **DISC-01**: Scan all IHSG stocks for unusual volume, breakouts
- [ ] **DISC-02**: Scan crypto market for top movers, anomalies
- [ ] **DISC-03**: Recommend new assets based on signal strength
- [ ] **DISC-04**: "New Opportunities" section in daily report

### Enhanced Fundamentals

- [ ] **FUND-01**: Ratio dashboard per stock (profitability, leverage, efficiency, growth — 5-year trends)
- [ ] **FUND-02**: Earnings quality analysis (cash flow vs earnings divergence, one-off items)
- [ ] **FUND-03**: Dividend analysis (payout ratio, yield, growth rate, FCF coverage)

## v2 Requirements

### Real-time Alerts
- **RTAM-01**: Event-driven alerts for extreme price moves (not full analysis)
- **RTAM-02**: High-impact news push notifications

### Web Dashboard
- **DASH-01**: Browser-based dashboard for historical signal visualization
- **DASH-02**: Interactive charts with engine overlays

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automated trade execution | Liability risk, regulatory gray area (OJK), security risk with exchange API keys |
| Real-time / intraday signals | 100x infrastructure cost, shallow analysis at speed, daily cadence matches depth |
| Mobile app | Telegram IS the app — push notifications, rich formatting, zero distribution friction |
| Multi-tenant SaaS with billing | Premature — validate signal quality first, shared instance for small group |
| Social/community features | Different product category, moderation burden, group already has Telegram chat |
| Granular per-engine weight configuration | LLM handles weighting implicitly via feedback loop, avoids user overfitting |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 2 | Pending |
| DATA-02 | Phase 2 | Pending |
| DATA-03 | Phase 2 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Complete |
| DATA-06 | Phase 1 | Pending |
| WTCH-01 | Phase 5 | Pending |
| WTCH-02 | Phase 5 | Pending |
| WTCH-03 | Phase 5 | Pending |
| ENGN-01 | Phase 3 | Pending |
| ENGN-02 | Phase 8 | Pending |
| ENGN-03 | Phase 3 | Pending |
| ENGN-04 | Phase 10 | Pending |
| ENGN-05 | Phase 8 | Pending |
| ENGN-06 | Phase 10 | Pending |
| ENGN-07 | Phase 10 | Pending |
| ENGN-08 | Phase 10 | Pending |
| ENGN-09 | Phase 8 | Pending |
| ENGN-10 | Phase 10 | Pending |
| ENGN-11 | Phase 10 | Pending |
| ENGN-12 | Phase 8 | Pending |
| ENGN-13 | Phase 10 | Pending |
| ENGN-14 | Phase 10 | Pending |
| ENGN-15 | Phase 9 | Pending |
| LLM-01 | Phase 4 | Pending |
| LLM-02 | Phase 4 | Pending |
| LLM-03 | Phase 4 | Pending |
| LLM-04 | Phase 7 | Pending |
| LLM-05 | Phase 4 | Pending |
| LLM-06 | Phase 11 | Pending |
| EVAL-01 | Phase 6 | Pending |
| EVAL-02 | Phase 7 | Pending |
| EVAL-03 | Phase 7 | Pending |
| EVAL-04 | Phase 7 | Pending |
| EVAL-05 | Phase 6 | Pending |
| IDXD-01 | Phase 9 | Pending |
| IDXD-02 | Phase 9 | Pending |
| IDXD-03 | Phase 9 | Pending |
| NEWS-01 | Phase 8 | Pending |
| NEWS-02 | Phase 8 | Pending |
| NEWS-03 | Phase 8 | Pending |
| NEWS-04 | Phase 8 | Pending |
| TBOT-01 | Phase 5 | Pending |
| TBOT-02 | Phase 5 | Pending |
| TBOT-03 | Phase 5 | Pending |
| TBOT-04 | Phase 6 | Pending |
| TBOT-05 | Phase 7 | Pending |
| TBOT-06 | Phase 11 | Pending |
| TBOT-07 | Phase 5 | Pending |
| TBOT-08 | Phase 12 | Pending |
| TBOT-09 | Phase 9 | Pending |
| TBOT-10 | Phase 11 | Pending |
| TBOT-11 | Phase 11 | Pending |
| TBOT-12 | Phase 12 | Pending |
| TBOT-13 | Phase 9 | Pending |
| REPT-01 | Phase 6 | Pending |
| REPT-02 | Phase 5 | Pending |
| REPT-03 | Phase 9 | Pending |
| REPT-04 | Phase 5 | Pending |
| REPT-05 | Phase 7 | Pending |
| REPT-06 | Phase 12 | Pending |
| REPT-07 | Phase 11 | Pending |
| VALN-01 | Phase 9 | Pending |
| VALN-02 | Phase 9 | Pending |
| VALN-03 | Phase 9 | Pending |
| VALN-04 | Phase 9 | Pending |
| VALN-05 | Phase 9 | Pending |
| DUED-01 | Phase 11 | Pending |
| DUED-02 | Phase 11 | Pending |
| DUED-03 | Phase 11 | Pending |
| DUED-04 | Phase 11 | Pending |
| RISK-01 | Phase 12 | Pending |
| RISK-02 | Phase 12 | Pending |
| RISK-03 | Phase 12 | Pending |
| RISK-04 | Phase 12 | Pending |
| RISK-05 | Phase 12 | Pending |
| DISC-01 | Phase 11 | Pending |
| DISC-02 | Phase 11 | Pending |
| DISC-03 | Phase 11 | Pending |
| DISC-04 | Phase 11 | Pending |
| FUND-01 | Phase 12 | Pending |
| FUND-02 | Phase 12 | Pending |
| FUND-03 | Phase 12 | Pending |

**Coverage:**
- v1 requirements: 83 total
- Mapped to phases: 83
- Unmapped: 0

---
*Requirements defined: 2026-03-23*
*Last updated: 2026-03-23 after roadmap creation*
