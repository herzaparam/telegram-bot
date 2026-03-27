# Phase 12: Portfolio Risk + Advanced Commands - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 12-portfolio-risk-advanced-commands
**Areas discussed:** Portfolio risk display, Backtest behavior, Stress testing design, Fundamentals dashboard

---

## Portfolio Risk Display

### Correlation Matrix Format

| Option | Description | Selected |
|--------|-------------|----------|
| Compact heatmap text | ASCII/emoji heatmap grid showing high/medium/low correlation between each pair | ✓ |
| Top alerts only | Skip full matrix — just show pairs with correlation >0.8 as warnings | |
| You decide | Claude picks the best format based on watchlist size | |

**User's choice:** Compact heatmap text
**Notes:** Fits ~8-10 assets before hitting Telegram message limits.

### VaR Method

| Option | Description | Selected |
|--------|-------------|----------|
| Historical simulation | Use actual past returns to estimate worst-case loss. No distribution assumptions | ✓ |
| Parametric (variance-covariance) | Assumes normal returns, faster to compute. Less accurate for crypto fat tails | |
| You decide | Claude picks based on data availability and VPS constraints | |

**User's choice:** Historical simulation
**Notes:** Works well with existing price_history data and handles crypto fat tails.

### Concentration Risk Breakdown

| Option | Description | Selected |
|--------|-------------|----------|
| Sector + single-asset + currency | All three: sector %, largest position %, IDR vs USD exposure | ✓ |
| Sector + single-asset only | Skip currency — split is obvious from asset types | |
| You decide | Claude determines what's most useful | |

**User's choice:** Sector + single-asset + currency (full picture)

---

## Backtest Behavior

### Signal Replay Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Full pipeline replay | Re-run all 15 engines + LLM verdict on historical data. Most accurate but slow/costly | ✓ |
| Engine scores only | Replay 15 engines but skip LLM. Weighted average as verdict. Fast, no API cost | |
| Use stored decisions | Only backtest dates with existing DailyDecision records. Instant but limited | |

**User's choice:** Full pipeline replay
**Notes:** Most accurate representation of actual signal quality. LLM cost per backtest accepted.

### Time Period Options

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed options (7d/30d/90d) | Simple preset periods. /backtest BTC 30d | ✓ |
| Flexible duration | Days, months, year shortcuts (/backtest BTC 6m, /backtest BTC 2024) | |
| You decide | Claude picks reasonable set | |

**User's choice:** Fixed options (7d/30d/90d)

### Results Presentation

| Option | Description | Selected |
|--------|-------------|----------|
| Summary stats only | Win rate, total return, buy-and-hold return, max drawdown, Sharpe ratio. One message | ✓ |
| Stats + trade log | Summary plus table of each signal with date/verdict/outcome. May need splitting | |
| You decide | Claude picks based on constraints | |

**User's choice:** Summary stats only

---

## Stress Testing Design

### Scenario Set

| Option | Description | Selected |
|--------|-------------|----------|
| Preset scenarios only | Hardcoded: 2020 COVID, 2022 crypto winter, 2013 taper tantrum, 2008 GFC | ✓ |
| Preset + custom shocks | Presets plus user-defined factor shocks (e.g., "IDX -20%, BTC -40%") | |
| You decide | Claude picks based on portfolio mix | |

**User's choice:** Preset scenarios only

### Delivery Method

| Option | Description | Selected |
|--------|-------------|----------|
| On-demand only | User runs command to see stress results. Not in daily report | ✓ |
| Daily report section | Mini stress test in daily report + on-demand command for full detail | |
| You decide | Claude picks based on report length | |

**User's choice:** On-demand only

---

## Fundamentals Dashboard

### Enhancement Depth

| Option | Description | Selected |
|--------|-------------|----------|
| 5-year trends + earnings quality | Full upgrade: 5-year ratio history, earnings quality, dividend analysis | ✓ |
| Earnings quality + dividends only | Keep current display, add earnings quality and dividend sections | |
| You decide | Claude determines right depth | |

**User's choice:** 5-year trend charts + earnings quality (major upgrade)

### Dividend Analysis Location

| Option | Description | Selected |
|--------|-------------|----------|
| Part of /fundamentals | Add dividend section within existing /fundamentals command output | ✓ |
| Separate /dividends command | New dedicated command for dividend-specific analysis | |
| You decide | Claude picks based on ergonomics | |

**User's choice:** Part of /fundamentals

---

## Claude's Discretion

- Correlation heatmap emoji/symbol choices
- VaR lookback window and confidence levels
- Sector classification mapping for concentration
- Backtest LLM cost management and caching
- Stress test scenario data (exact drawdown percentages)
- 5-year trend data source selection
- Earnings quality detection algorithm
- DB schema design for new tables
- Message formatting and splitting

## Deferred Ideas

None — discussion stayed within phase scope.
