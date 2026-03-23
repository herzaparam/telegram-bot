# Feature Research

**Domain:** Daily trading signal agent (IDX stocks + global crypto)
**Researched:** 2026-03-23
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Daily signal delivery via Telegram | Core value prop. Every signal bot delivers via messaging. Without reliable daily delivery, the product does not exist. | MEDIUM | Scheduled send + on-demand `/report`. Must handle Telegram rate limits and message length (4096 char cap). Split into multiple messages or use inline formatting. |
| Watchlist management | Users need to choose what assets they track. Every signal service has this. | LOW | `/add`, `/remove`, `/watchlist` commands. Store per-user in PostgreSQL. Support both IDX tickers (BBCA) and crypto pairs (BTC). |
| Technical analysis signals | Most basic analysis type. Stockbot, TradingView, every screener does RSI/MACD/MA. Users expect at least this. | MEDIUM | pandas-ta covers 130+ indicators. Focus on the 10-15 most actionable: RSI, MACD, Bollinger, EMA crossovers, volume breakout. Output score + confidence + reasoning. |
| Clear buy/sell/hold verdict | Users want a decision, not raw data. Signal bots that just dump indicators get abandoned. | MEDIUM | LLM synthesizes engine scores into STRONG BUY / BUY / HOLD / SELL / STRONG SELL. Must include reasoning -- "why" matters as much as "what." |
| Entry/exit context | Every serious signal includes where to enter and what to watch. Without this, signals are useless noise. | MEDIUM | Support/resistance levels, suggested stop-loss zones, take-profit targets. Can be LLM-generated from technical levels. |
| Historical price data storage | Cannot analyze without data. Every system stores OHLCV. | MEDIUM | TimescaleDB hypertables with compression. Need 1-2 years of daily data per asset for meaningful analysis. yfinance for IDX, ccxt for crypto. |
| Signal reasoning/explanation | Traders do not follow black-box signals. They need to understand the "why" to trust the system. | LOW | Each engine outputs reasoning text. LLM final verdict includes synthesis of key factors. Critical for user trust and learning. |
| Error recovery and reliability | Daily signal must arrive. If it fails silently, users lose trust immediately. | MEDIUM | Pipeline stage restartability, failure notifications, retry logic. Track pipeline runs in DB. Alert user if daily report fails. |
| Accuracy tracking / scorecard | Users need to know if the system actually works. Win rate, hit rate over time. | MEDIUM | Compare yesterday's signals vs actual price movement. Track cumulative accuracy per engine and overall. `/scorecard` command. |

### Differentiators (Competitive Advantage)

Features that set this product apart from typical signal bots. Not required, but these are where value is created.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| 15-engine multi-dimensional analysis | Most bots use 1-3 signal types (usually just technicals). Running 15 categories (technical, fundamental, sentiment, on-chain, macro, behavioral, etc.) provides a panoramic view no single-method bot can match. | HIGH | Build incrementally: start with 3-4 engines, add over time. Each engine is independent (score + confidence + reasoning interface). Sequential execution keeps RAM manageable. |
| LLM-powered decision synthesis | Most bots use rule-based scoring. Using an LLM to weigh contradictions, consider context, and produce nuanced reasoning is genuinely different. "Bullish technicals but overvalued" type analysis is hard to get from rules. | MEDIUM | GPT-4o-mini via LiteLLM. Structured output via Pydantic. Prompt engineering is the main effort. Cost target: ~$0.50-1.00/month at daily cadence. |
| Self-evaluation feedback loop | Almost no signal bot reviews its own past decisions and learns from mistakes. This is the strongest differentiator. System that gets smarter over time builds compounding trust. | HIGH | Morning self-review: fetch actual prices, compare to yesterday's verdict, LLM extracts lessons, lessons feed into future decisions. Requires decision tracking table, lesson storage, accuracy stats. |
| Indonesian financial document (laporan keuangan) parsing | IDX-specific edge. Most global tools cannot parse Bahasa Indonesia PDF financial reports. This unlocks fundamental analysis that competitors cannot offer for IDX stocks. | HIGH | PyMuPDF for PDF extraction, GPT for parsing Bahasa Indonesia. Extract revenue, net profit, debt, cash flow. Feed into fundamental engine. Quality depends on PDF structure consistency. |
| Valuation engine with DCF + peer comparison | Moves beyond "is the trend up?" to "is the price right?" Most signal bots never answer valuation questions. Fair value estimates + margin of safety give investment-grade insight. | HIGH | DCF requires projected cash flows (from parsed financials), WACC estimation (BI rate, beta). Peer comparison needs sector classification. Crypto proxies: NVT, stock-to-flow. |
| Multi-market coverage (IDX + crypto) | Most bots focus on one market. Covering both IDX and crypto in one system serves traders who diversify across asset classes. Cross-market correlation insights are a bonus. | MEDIUM | Different data sources (yfinance vs ccxt), different applicable engines (fundamentals for stocks, on-chain for crypto). Engine applicability matrix already defined in PROJECT-PLAN.md. |
| Due diligence module (ownership, insider tracking) | Goes beyond numbers into qualitative research. Insider selling patterns, management quality scoring, competitive positioning -- this is analyst-grade work automated. | HIGH | IDX-specific data scraping from idx.co.id filings. Management tracking requires manual data initially. Sector benchmarking needs maintained classification. |
| Portfolio risk monitor | Individual asset signals are common. Portfolio-level risk view (correlation matrix, VaR, concentration risk, stress testing) is institutional-grade and rare in retail signal bots. | HIGH | Requires position data from user (or watchlist as proxy). Correlation matrix, VaR calculation, historical stress scenarios. pandas/numpy-heavy computation. |
| Asset discovery / screening | Proactive opportunity finding vs reactive watchlist analysis. Scanning full IHSG and crypto for anomalies, breakouts, unusual volume surfaces opportunities users would miss. | MEDIUM | Daily screener across all IHSG stocks and top crypto. Volume anomaly detection, breakout detection, momentum screening. Adds "New Opportunities" section to daily report. |
| Scenario analysis (bull/base/bear) | Probability-weighted expected returns give users a framework for position sizing. Most bots give a single verdict with no uncertainty range. | MEDIUM | Three scenarios with probability weights. Sensitivity tables: "if BI rate rises 50bps, fair value drops 12%." Builds on valuation engine outputs. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems. Deliberately excluded.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Automated trade execution | "Just execute the signals for me" -- convenience appeal | Liability nightmare. Signal errors become real losses. Users lose agency and blame the system. Regulatory gray area in Indonesia (OJK). Requires exchange API keys with withdrawal permissions -- security risk. | Signals-only approach. Users decide and execute. Clear disclaimer that signals are not financial advice. |
| Real-time / intraday signals | "I want signals during market hours" -- day trader appeal | Dramatically increases infrastructure cost (always-on analysis), LLM API costs (100x more calls), data costs, and complexity. Daily cadence matches the analysis depth (15 engines need time). Real-time signals from 15 engines would be shallow. | Daily cadence with depth. If a major event happens, the next morning report covers it. Potential future: event-driven alerts for extreme moves only (not full analysis). |
| Mobile app | "I want an app" -- familiarity | Telegram IS the app. Building a native app adds months of development, app store approval, maintenance burden. Telegram has push notifications, inline keyboards, rich formatting. Zero distribution friction. | Telegram bot with rich formatting, inline keyboards, and callback queries. Progressive enhancement: web dashboard later if needed. |
| Multi-tenant SaaS with billing | "Sell this to others" -- monetization appeal | Premature optimization. Small group of active traders is the target. Adding auth, billing, tenant isolation, pricing tiers before validating the core signal quality is classic over-engineering. | Shared instance for the small group. If signal quality proves out, consider SaaS later as a separate project. |
| Backtesting UI | "Let me backtest any strategy" -- power user appeal | Full backtesting is a product unto itself (QuantConnect, Backtrader). Building a good backtesting framework is months of work. Bad backtesting gives false confidence (overfitting, survivorship bias). | Limited `/backtest BTC 30d` command that replays historical signals. Not a strategy builder -- just "how would my current engines have performed?" |
| Real-time price alerts | "Alert me when BTC hits $X" -- common request | Requires always-on price monitoring, WebSocket connections, alert management. Separate concern from daily analysis. Many free tools already do this (Binance app, CoinGecko). | Point users to existing free tools for price alerts. Focus system on analysis depth, not price monitoring. |
| Social/community features | "Let users share signals, discuss trades" -- engagement appeal | Community moderation, content liability, spam management. Completely different product category. Distracts from core analytical value. | The small trader group already has their own Telegram group for discussion. Keep the bot focused on analysis. |
| Granular per-engine configuration | "Let me tune each engine's weight" -- control appeal | 15 engines with configurable weights creates a combinatorial explosion of settings. Users will over-optimize to recent data. The LLM decision maker is the "weighting" mechanism and adapts via feedback loop. | LLM handles weighting implicitly. Expose only high-level settings: notification time, which asset types to include, report verbosity level. |

## Feature Dependencies

```
[Price Data Fetching & Storage]
    |
    +--requires--> [Technical Analysis Engine]
    |                  |
    |                  +--enhances--> [LLM Final Decision]
    |                                    |
    +--requires--> [Fundamental Engine]  +--requires--> [Daily Telegram Report]
    |                  |                                    |
    |                  +--enhances--> [LLM Final Decision]  +--enhances--> [Accuracy Tracking]
    |                                                                          |
    +--requires--> [Macro Engine]                                              +--requires--> [Self-Evaluation Loop]
    |                  |                                                                          |
    |                  +--enhances--> [LLM Final Decision]                                        +--feeds--> [LLM Final Decision]
    |
    +--requires--> [Watchlist Management]
    |
    +--requires--> [Telegram Bot (always-on)]

[IDX PDF Parsing] --requires--> [Fundamental Engine] --enhances--> [Valuation Engine (DCF)]

[Valuation Engine] --requires--> [Fundamental Engine] + [Macro Engine]

[Due Diligence Module] --requires--> [Fundamental Engine] + [IDX PDF Parsing]

[Portfolio Risk Monitor] --requires--> [Price Data] + [Watchlist Management]

[Asset Discovery] --requires--> [Price Data] + [Technical Analysis Engine]

[Self-Evaluation Loop] --requires--> [Decision Tracking] + [Price Data]

[Sentiment Engine] --conflicts-with--> [launching before Technical Engine is validated]
    (sentiment is noisier; validate simpler engines first)
```

### Dependency Notes

- **LLM Final Decision requires at least 1 engine:** Can launch with just Technical Analysis, then add engines incrementally. LLM prompt adapts to available engines.
- **Self-Evaluation requires Decision Tracking:** Must store decisions before you can evaluate them. Implement decision storage with the first signal delivery, even if evaluation comes later.
- **Valuation Engine requires Fundamental Engine + IDX PDF Parsing:** DCF needs financial data. Cannot build valuation without the data pipeline in place first.
- **Portfolio Risk Monitor requires position/watchlist data:** Works with watchlist as a proxy for portfolio. True portfolio risk needs user-provided position sizes.
- **Asset Discovery requires broad price data:** Need to fetch prices for all IHSG stocks (not just watchlist) to scan for opportunities. Significant data volume increase.
- **Due Diligence requires IDX-specific data sources:** Ownership filings, insider transaction data from idx.co.id. Scraping stability is a risk.

## MVP Definition

### Launch With (v1)

Minimum viable product -- the daily signal loop must work end-to-end for the core value to be validated.

- [ ] **Price data fetching and storage** -- Cannot analyze without data. yfinance for IDX, ccxt for crypto, TimescaleDB storage.
- [ ] **Watchlist management via Telegram** -- Users must choose what to track. `/add`, `/remove`, `/watchlist`.
- [ ] **Technical analysis engine** -- The simplest, most established analysis type. RSI, MACD, Bollinger, EMA, volume. Proves the engine interface works.
- [ ] **LLM final decision maker** -- Even with one engine, the LLM synthesis is the core differentiator. STRONG BUY to STRONG SELL + reasoning.
- [ ] **Daily Telegram report** -- The delivery mechanism. Scheduled morning report with signals, verdicts, and reasoning.
- [ ] **Decision tracking** -- Store every decision for future evaluation. Even if self-evaluation comes later, start collecting data from day one.
- [ ] **Basic accuracy tracking** -- Compare yesterday's signals to actual price movement. `/scorecard` shows win rate. Builds trust early.
- [ ] **Error handling and pipeline reliability** -- Retry logic, failure alerts, stage restartability. Daily signal must arrive.

### Add After Validation (v1.x)

Features to add once the core daily loop is working and producing reasonable signals.

- [ ] **Fundamental analysis engine** -- Add when IDX financial data pipeline is working. Second engine type deepens analysis.
- [ ] **Macro/economic engine** -- BI rate, FRED data, DXY, rupiah. Third engine adds macro context. Low data cost (FRED is free).
- [ ] **Self-evaluation feedback loop** -- Add after 2-4 weeks of decision data exists. This is the compounding advantage -- start it as soon as there is enough history.
- [ ] **Sentiment engine** -- Reddit, Fear & Greed, Google Trends. Fourth engine type. Noisier than technicals, so validate after core is solid.
- [ ] **News-driven signals** -- RSS feeds from Kontan, CNBC Indonesia, Finnhub. LLM scores news impact.
- [ ] **IDX PDF parsing (laporan keuangan)** -- Unlocks deep fundamental analysis for IDX stocks. High value but high complexity.
- [ ] **On-chain analysis engine** -- For crypto assets. TVL, whale tracking, exchange flows. Adds crypto-specific depth.

### Future Consideration (v2+)

Features to defer until signal quality is validated and core loop is mature.

- [ ] **Valuation engine (DCF, peer comparison)** -- Requires solid fundamental data pipeline. High value but depends on multiple prior features.
- [ ] **Due diligence module** -- Ownership tracking, management quality. Analyst-grade work that depends on IDX data scraping reliability.
- [ ] **Portfolio risk monitor** -- Correlation matrix, VaR, stress testing. Institutional-grade feature. Defer until users actually track positions.
- [ ] **Asset discovery / screener** -- Scanning all IHSG requires broad data fetching. Defer until per-asset analysis is solid.
- [ ] **ML/AI engine (XGBoost, LSTM)** -- Requires substantial training data and offline model training. ONNX deployment adds complexity. Defer until simpler engines are validated.
- [ ] **Remaining engines (behavioral, event-driven, game theory, emerging, options, network, alternative data)** -- Build incrementally after core 5-6 engines prove the architecture.
- [ ] **Scenario analysis (bull/base/bear)** -- Depends on valuation engine. Nice-to-have layered on top.
- [ ] **Enhanced fundamental deep dive** -- Ratio dashboards, earnings quality. Refinement of fundamental engine, not a new capability.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Daily Telegram report delivery | HIGH | MEDIUM | P1 |
| Watchlist management | HIGH | LOW | P1 |
| Technical analysis engine | HIGH | MEDIUM | P1 |
| LLM final decision maker | HIGH | MEDIUM | P1 |
| Decision tracking | MEDIUM | LOW | P1 |
| Basic accuracy tracking / scorecard | HIGH | MEDIUM | P1 |
| Pipeline error handling / reliability | HIGH | MEDIUM | P1 |
| Price data fetching & storage | HIGH | MEDIUM | P1 |
| Self-evaluation feedback loop | HIGH | HIGH | P2 |
| Fundamental analysis engine | HIGH | MEDIUM | P2 |
| Macro/economic engine | MEDIUM | LOW | P2 |
| Sentiment engine | MEDIUM | MEDIUM | P2 |
| News-driven signals | MEDIUM | MEDIUM | P2 |
| IDX PDF parsing | HIGH | HIGH | P2 |
| On-chain analysis engine | MEDIUM | MEDIUM | P2 |
| Valuation engine (DCF + peers) | HIGH | HIGH | P3 |
| Due diligence module | MEDIUM | HIGH | P3 |
| Portfolio risk monitor | MEDIUM | HIGH | P3 |
| Asset discovery / screener | MEDIUM | MEDIUM | P3 |
| ML/AI engine (XGBoost/LSTM) | MEDIUM | HIGH | P3 |
| Remaining analysis engines (7 types) | LOW | HIGH | P3 |
| Scenario analysis | LOW | MEDIUM | P3 |
| Enhanced fundamental deep dive | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch -- the daily signal loop
- P2: Should have, add incrementally -- deepens analysis quality
- P3: Nice to have, future consideration -- institutional-grade features

## Competitor Feature Analysis

| Feature | Stockbot (IDX) | Steven Signal | Tickeron | 3Commas | Our Approach |
|---------|---------------|---------------|----------|---------|--------------|
| Technical analysis | Candlestick, MACD, RSI, volume | EMA, SMA, RSI, candlestick patterns | 150+ patterns, AI pattern recognition | Basic indicators | 15 engines including technicals, fundamentals, sentiment, on-chain, macro |
| Signal delivery | Mobile app | Telegram | Web dashboard + alerts | Web + mobile | Telegram-first, daily cadence |
| Verdict clarity | Trading plan with entry/SL/TP | Directional signals (not financial advice) | BUY/SELL with confidence % | Automated execution | STRONG BUY to STRONG SELL with LLM reasoning |
| Self-learning | None | None | AI model updates | None | Daily self-evaluation loop with lesson extraction |
| Fundamental analysis | None (technical only) | None (technical only) | Limited | None | IDX PDF parsing, DCF, peer comparison |
| IDX/Indonesia focus | Native IDX support | No (crypto only) | US-focused | Crypto-focused | Native IDX + crypto, Bahasa Indonesia parsing |
| Risk management | Stop-loss suggestions | None | Portfolio-level controls | Position sizing, drawdown limits | Portfolio correlation, VaR, stress testing |
| Valuation | None | None | None | None | DCF, peer multiples, margin of safety |
| Cost | Freemium app | Paid subscription | $50-200/month | $49-99/month | Self-hosted, LLM API cost only (~$1/month) |

## Sources

- [Stockbot.id - IDX Trading Signal App](https://www.stockbot.id/)
- [Steven Signal - AI Trading Telegram Bot Case Study](https://maddevs.io/case-studies/steven-signal/)
- [Tickeron - AI Trading Signal Agents](https://tickeron.com/trading-investing-101/top-8-ai-trading-signal-agents-on-august-1-2025/)
- [3Commas - AI Trading Bot Risk Management Guide](https://3commas.io/blog/ai-trading-bot-risk-management-guide-2025)
- [CoinGecko - Top Telegram Trading Bots](https://www.coingecko.com/learn/top-telegram-trading-bots)
- [Bitget - Telegram Signal & Trade Copier Guide 2026](https://www.bitget.com/amp/academy/telegram-signal-and-trade-copier-tools-complete-2026-america-automation-guide)
- [Macrosynergy - How to Measure Signal Quality](https://macrosynergy.com/research/how-to-measure-the-quality-of-a-trading-signal/)
- [AI-Signals.com - AI Trading Signals Platform](https://ai-signals.com/)

---
*Feature research for: Daily trading signal agent (IDX stocks + global crypto)*
*Researched: 2026-03-23*
