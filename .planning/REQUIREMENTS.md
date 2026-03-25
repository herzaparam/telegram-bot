# Requirements: Trade Signal Agent

**Defined:** 2026-03-23
**Core Value:** The daily signal loop must work reliably: fetch data, run engines, produce LLM verdicts, and deliver a Telegram report every morning

## v1 Requirements

### Data Infrastructure

- [x] **DATA-01**: System stores daily OHLCV price history in TimescaleDB hypertables with auto-compression after 30 days
- [x] **DATA-02**: System fetches IDX stock prices via yfinance (.JK suffix) with aggressive caching
- [x] **DATA-03**: System fetches crypto OHLCV via ccxt (Binance) with CoinGecko metadata backup
- [x] **DATA-04**: Pipeline stages are idempotent and restartable from point of failure
- [x] **DATA-05**: Pipeline tracks execution state in pipeline_runs table
- [x] **DATA-06**: System classifies data sources by tier (critical/important/supplementary) and degrades gracefully on failure

### Watchlist

- [x] **WTCH-01**: User can add IDX stocks and crypto assets to personal watchlist via Telegram
- [x] **WTCH-02**: User can remove assets from watchlist via Telegram
- [x] **WTCH-03**: User can view current watchlist via `/watchlist` command

### Signal Engines

- [x] **ENGN-01**: Technical analysis engine (RSI, MACD, Bollinger, MA, volume) outputs score/confidence/reasoning
- [x] **ENGN-02**: Fundamental analysis engine (P/E, P/B, revenue growth, ROE) for IDX stocks
- [x] **ENGN-03**: Quantitative/statistical engine (momentum, mean reversion, ARIMA)
- [ ] **ENGN-04**: ML/AI engine (XGBoost, LSTM via ONNX, ensemble)
- [x] **ENGN-05**: Sentiment engine (Reddit, Stockbit, Fear & Greed)
- [ ] **ENGN-06**: On-chain engine for crypto (TVL, whale tracking, exchange flows, NVT)
- [ ] **ENGN-07**: Options engine (put/call ratio, max pain) — limited scope
- [ ] **ENGN-08**: Behavioral engine (volume anomaly, herding detection)
- [x] **ENGN-09**: Event-driven engine (earnings calendar, BI meetings, halving)
- [ ] **ENGN-10**: Alternative data engine (GitHub activity) for crypto
- [ ] **ENGN-11**: Network/graph engine (correlation analysis between assets)
- [x] **ENGN-12**: Macro/economic engine (BI rate, Fed rate, CPI, DXY, rupiah)
- [ ] **ENGN-13**: Game theory engine (order book imbalance, whale patterns)
- [ ] **ENGN-14**: Emerging methods engine (fractal dimension, wavelet analysis)
- [x] **ENGN-15**: Valuation engine (DCF, peer multiples, margin of safety) with fair value estimates

### LLM Decision Maker

- [x] **LLM-01**: LLM reads all 15 engine scores + valuation data + context to produce final verdict
- [x] **LLM-02**: LLM detects contradictions between signals (e.g., bullish technicals but overvalued)
- [x] **LLM-03**: LLM considers upcoming events that could invalidate signals
- [x] **LLM-04**: LLM applies lessons learned from past mistakes
- [x] **LLM-05**: LLM outputs STRONG BUY / BUY / HOLD / SELL / STRONG SELL + reasoning + fair value context
- [ ] **LLM-06**: LLM considers due diligence flags (insider selling, management changes, earnings quality)

### Self-Evaluation

- [x] **EVAL-01**: System reviews yesterday's decisions against actual prices every morning
- [x] **EVAL-02**: LLM analyzes what went right/wrong and why
- [x] **EVAL-03**: System extracts concrete lessons and stores in database
- [x] **EVAL-04**: Lessons feed into future LLM decisions automatically
- [x] **EVAL-05**: System tracks accuracy stats over time (win rate, best/worst engine)

### IDX Documents

- [x] **IDXD-01**: System downloads laporan keuangan (quarterly/annual) from idx.co.id
- [x] **IDXD-02**: GPT parses PDF reports in Bahasa Indonesia
- [x] **IDXD-03**: System extracts revenue, net profit, debt, cash flow, management outlook

### News

- [x] **NEWS-01**: System ingests Indonesian financial news (Kontan, CNBC Indonesia, Bisnis) via RSS
- [x] **NEWS-02**: System ingests global crypto/financial news (Finnhub)
- [x] **NEWS-03**: LLM scores news impact per asset
- [x] **NEWS-04**: Daily digest of relevant news included in report

### Telegram Bot

- [x] **TBOT-01**: `/start` welcome + setup
- [x] **TBOT-02**: `/report` gets today's full report on demand
- [x] **TBOT-03**: `/report BTC` gets detailed single-asset report
- [x] **TBOT-04**: `/scorecard` shows accuracy stats + recent results
- [x] **TBOT-05**: `/lessons` shows learned lessons
- [ ] **TBOT-06**: `/discover` shows today's opportunities
- [x] **TBOT-07**: `/settings` configures notification time, categories
- [ ] **TBOT-08**: `/backtest BTC 30d` runs historical signal replay
- [ ] **TBOT-09**: `/valuation BBCA` shows DCF, peer comparison, fair value
- [ ] **TBOT-10**: `/compare BBCA BBRI BMRI` side-by-side sector comparison
- [ ] **TBOT-11**: `/duediligence BBCA` full DD report
- [ ] **TBOT-12**: `/portfolio` portfolio risk overview
- [ ] **TBOT-13**: `/fundamentals BBCA` deep ratio dashboard

### Daily Report

- [x] **REPT-01**: Yesterday's scorecard (was I right/wrong, accuracy stats)
- [x] **REPT-02**: Today's signal for each watchlist asset (all 15 categories + LLM verdict)
- [ ] **REPT-03**: Valuation summary (fair value vs market price, margin of safety)
- [x] **REPT-04**: LLM reasoning for each decision
- [x] **REPT-05**: Lessons applied today
- [ ] **REPT-06**: Portfolio risk snapshot (concentration, correlation alerts)
- [ ] **REPT-07**: New opportunities discovered

### Valuation Engine

- [x] **VALN-01**: DCF model for IDX stocks using parsed financial data
- [x] **VALN-02**: Comparable company analysis with sector peer grouping
- [x] **VALN-03**: Crypto valuation proxies (NVT ratio, stock-to-flow for BTC, revenue multiples for DeFi)
- [x] **VALN-04**: Scenario analysis (bull/base/bear) with probability-weighted returns
- [x] **VALN-05**: Quarter-over-quarter ratio tracking with change alerts

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
| DATA-01 | Phase 2 | Complete |
| DATA-02 | Phase 2 | Complete |
| DATA-03 | Phase 2 | Complete |
| DATA-04 | Phase 1 | Complete |
| DATA-05 | Phase 1 | Complete |
| DATA-06 | Phase 1 | Complete |
| WTCH-01 | Phase 5 | Complete |
| WTCH-02 | Phase 5 | Complete |
| WTCH-03 | Phase 5 | Complete |
| ENGN-01 | Phase 3 | Complete |
| ENGN-02 | Phase 8 | Complete |
| ENGN-03 | Phase 3 | Complete |
| ENGN-04 | Phase 10 | Pending |
| ENGN-05 | Phase 8 | Complete |
| ENGN-06 | Phase 10 | Pending |
| ENGN-07 | Phase 10 | Pending |
| ENGN-08 | Phase 10 | Pending |
| ENGN-09 | Phase 8 | Complete |
| ENGN-10 | Phase 10 | Pending |
| ENGN-11 | Phase 10 | Pending |
| ENGN-12 | Phase 8 | Complete |
| ENGN-13 | Phase 10 | Pending |
| ENGN-14 | Phase 10 | Pending |
| ENGN-15 | Phase 9 | Complete |
| LLM-01 | Phase 4 | Complete |
| LLM-02 | Phase 4 | Complete |
| LLM-03 | Phase 4 | Complete |
| LLM-04 | Phase 7 | Complete |
| LLM-05 | Phase 4 | Complete |
| LLM-06 | Phase 11 | Pending |
| EVAL-01 | Phase 6 | Complete |
| EVAL-02 | Phase 7 | Complete |
| EVAL-03 | Phase 7 | Complete |
| EVAL-04 | Phase 7 | Complete |
| EVAL-05 | Phase 6 | Complete |
| IDXD-01 | Phase 9 | Complete |
| IDXD-02 | Phase 9 | Complete |
| IDXD-03 | Phase 9 | Complete |
| NEWS-01 | Phase 8 | Complete |
| NEWS-02 | Phase 8 | Complete |
| NEWS-03 | Phase 8 | Complete |
| NEWS-04 | Phase 8 | Complete |
| TBOT-01 | Phase 5 | Complete |
| TBOT-02 | Phase 5 | Complete |
| TBOT-03 | Phase 5 | Complete |
| TBOT-04 | Phase 6 | Complete |
| TBOT-05 | Phase 7 | Complete |
| TBOT-06 | Phase 11 | Pending |
| TBOT-07 | Phase 5 | Complete |
| TBOT-08 | Phase 12 | Pending |
| TBOT-09 | Phase 9 | Pending |
| TBOT-10 | Phase 11 | Pending |
| TBOT-11 | Phase 11 | Pending |
| TBOT-12 | Phase 12 | Pending |
| TBOT-13 | Phase 9 | Pending |
| REPT-01 | Phase 6 | Complete |
| REPT-02 | Phase 5 | Complete |
| REPT-03 | Phase 9 | Pending |
| REPT-04 | Phase 5 | Complete |
| REPT-05 | Phase 7 | Complete |
| REPT-06 | Phase 12 | Pending |
| REPT-07 | Phase 11 | Pending |
| VALN-01 | Phase 9 | Complete |
| VALN-02 | Phase 9 | Complete |
| VALN-03 | Phase 9 | Complete |
| VALN-04 | Phase 9 | Complete |
| VALN-05 | Phase 9 | Complete |
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
