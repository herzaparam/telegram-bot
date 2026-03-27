# Phase 12: Portfolio Risk + Advanced Commands - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Portfolio-level risk monitoring with correlation matrix, concentration analysis, VaR, and stress testing. Historical backtesting replaying full pipeline signals. Enhanced /fundamentals with 5-year trends, earnings quality, and dividend analysis. New Telegram commands: `/portfolio`, `/backtest`. New daily report section: portfolio risk snapshot. Does NOT include: real-time alerts (v2), web dashboard (v2), automated trade execution (out of scope).

</domain>

<decisions>
## Implementation Decisions

### Portfolio Risk Display (/portfolio command)
- **D-01:** Correlation matrix displayed as compact ASCII/emoji heatmap grid showing high/medium/low correlation between each asset pair. Fits ~8-10 assets within Telegram message limits
- **D-02:** VaR computed using historical simulation method — use actual past returns from price_history to estimate worst-case loss at 95% and 99% confidence. No distribution assumptions, works well with crypto fat tails
- **D-03:** Concentration risk shows all three dimensions: sector percentage (e.g., "Banking 60%"), largest single-asset position %, and IDR vs USD currency exposure breakdown
- **D-04:** Daily and weekly VaR numbers plus maximum drawdown tracking included in output
- **D-05:** Risk-adjusted return metrics: Sharpe ratio and Sortino ratio computed from historical returns

### Daily Report Portfolio Risk Snapshot (REPT-06)
- **D-06:** Portfolio risk snapshot section in daily report shows concentration %, correlation alerts (pairs >0.8), and VaR summary. Compact format matching existing report card style
- **D-07:** Stress test results are NOT included in daily report — on-demand only via command

### Backtest Behavior (/backtest command)
- **D-08:** Full pipeline replay — re-run all 15 engines + LLM verdict on historical data for each day in the backtest period. Most accurate representation of actual signal quality
- **D-09:** Fixed time period options: 7d, 30d, 90d. User invokes as `/backtest BTC 30d`. Simple preset periods, no custom date ranges
- **D-10:** Output as summary stats only: win rate, total return, buy-and-hold comparison return, max drawdown, Sharpe ratio. Compact, fits one Telegram message

### Stress Testing
- **D-11:** Preset historical scenarios only — hardcoded set: 2020 COVID crash, 2022 crypto winter, 2013 taper tantrum, 2008 GFC. Apply actual historical drawdowns to current portfolio positions
- **D-12:** On-demand delivery only — user runs a command (part of `/portfolio` or separate sub-command) to see stress test projected drawdowns. Not in daily report
- **D-13:** No custom factor shocks — preset scenarios are sufficient for the daily-cadence use case

### Enhanced Fundamentals Dashboard (/fundamentals upgrade)
- **D-14:** Add 5-year ratio trend history with text sparklines or trend arrows per year for profitability, leverage, efficiency, and growth ratios
- **D-15:** Add earnings quality analysis section: cash flow vs earnings divergence detection, one-off/extraordinary item identification
- **D-16:** Add dividend analysis section within /fundamentals: payout ratio, dividend yield, growth rate, FCF coverage. No separate /dividends command
- **D-17:** IDX stocks only for enhanced fundamentals (consistent with Phase 9 D-18, Phase 11 D-11). Crypto assets get existing signal analysis

### Claude's Discretion
- Correlation heatmap emoji/symbol choices and formatting within Telegram limits
- Historical simulation VaR lookback window (e.g., 252 trading days)
- VaR confidence level presentation (95% vs 99% or both)
- Sector classification mapping for concentration analysis
- Currency exposure calculation method (IDR assets vs USD-denominated crypto)
- Backtest full pipeline replay implementation (batch processing, LLM cost management, caching strategy)
- Backtest progress feedback mechanism (long-running operation)
- Stress test scenario data (exact drawdown percentages per scenario per asset type)
- How stress test applies IDX-specific vs crypto-specific shocks
- 5-year trend data source (parsed financials from Phase 9 vs yfinance historical)
- Earnings quality detection algorithm specifics
- Sparkline/trend arrow rendering for 5-year history
- New DB tables schema (portfolio_snapshots, backtest_results, stress_scenarios, etc.)
- Alembic migration details
- Error handling and graceful degradation
- Telegram message formatting and splitting for large outputs
- How /portfolio sub-sections are organized (single message vs multiple)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Portfolio Risk Requirements
- `.planning/REQUIREMENTS.md` — RISK-01 through RISK-05 (correlation, concentration, VaR, risk-adjusted returns, stress testing), REPT-06 (daily report risk snapshot)

### Backtest & Fundamentals Requirements
- `.planning/REQUIREMENTS.md` — TBOT-08 (/backtest command), TBOT-12 (/portfolio command), FUND-01 (ratio dashboard), FUND-02 (earnings quality), FUND-03 (dividend analysis)

### Existing Correlation Infrastructure
- `src/engines/network.py` — NetworkEngine with pre-computed pairwise correlation analysis (reusable for portfolio-wide matrix)
- `src/data/analyze.py` — `_compute_correlation_data()` function computing 30-day rolling correlations between assets

### Engine & Signal Contract
- `src/engines/base.py` — BaseEngine ABC and Signal dataclass (contract for all engines)
- `src/data/analyze.py` — `_get_engines_for_asset()` and `analyze_stage()` (pipeline replay entry point for backtest)

### Telegram Bot Patterns
- `src/bot/handlers/` — Existing handler patterns (valuation.py, fundamentals.py, discover.py) for new /portfolio and /backtest handlers
- `src/report/formatter.py` — HTML formatting utilities, emoji maps, message splitting for Telegram

### Prior Phase Context
- `.planning/phases/09-idx-documents-valuation-engine/09-CONTEXT.md` — Valuation engine decisions, financial data extraction (Phase 9 fundamentals feed into enhanced dashboard)
- `.planning/phases/11-asset-discovery-due-diligence/11-CONTEXT.md` — Due diligence patterns, sector benchmarking (reusable for concentration analysis)

### Database & Price Data
- `src/db/price_repo.py` — Raw asyncpg OHLCV repository (historical price data for VaR and backtest)
- `src/db/models.py` — Existing ORM models including PriceHistory, DailyDecision, Asset

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `NetworkEngine` + `_compute_correlation_data()`: Already computes 30-day rolling pairwise correlations. Can be extended to build full NxN correlation matrix for portfolio view
- `src/report/formatter.py`: HTML formatting, emoji maps (VERDICT_EMOJI, VALUATION_EMOJI, TREND_EMOJI), message splitting — reuse for /portfolio and /backtest output
- `src/bot/handlers/*.py`: Established pattern for Telegram command handlers with auth checks, HTML formatting, async DB queries
- `src/engines/valuation.py`: ValuationEngine with DCF, peer comparison — financial data access patterns reusable for enhanced fundamentals
- `src/engines/fundamental.py`: FundamentalEngine with yfinance-based ratios — existing ratio computation to extend with 5-year trends
- `src/db/price_repo.py`: Raw asyncpg queries for bulk price data — efficient historical data access for VaR and backtest

### Established Patterns
- Two-process model: bot (always-on) vs pipeline (daily). Portfolio risk computation happens in pipeline, results served by bot
- Sequential engine execution per asset with memory release — backtest must follow same pattern to stay within 1GB RAM
- HTML parse_mode for all Telegram messages (Phase 5 decision)
- IDX-only for fundamental analysis commands, crypto gets "not applicable" (Phase 9, 11 precedent)
- Async pipeline stages with `StageFunc` signature
- Existing `DailyDecision` model stores pipeline verdicts — backtest generates similar records

### Integration Points
- New `/portfolio` and `/backtest` handlers in `src/bot/handlers/`
- Portfolio risk snapshot section added to daily report via `src/report/formatter.py`
- Backtest needs to invoke `analyze_stage()` or equivalent for each historical day
- VaR/stress test computations may need a new module (e.g., `src/risk/`) or extend `src/data/`
- Enhanced /fundamentals extends existing `src/bot/handlers/fundamentals.py`
- New DB tables for portfolio snapshots, backtest results via Alembic migration

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-portfolio-risk-advanced-commands*
*Context gathered: 2026-03-27*
