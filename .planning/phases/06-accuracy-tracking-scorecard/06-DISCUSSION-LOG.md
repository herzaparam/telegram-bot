# Phase 6: Accuracy Tracking + Scorecard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 06-accuracy-tracking-scorecard
**Areas discussed:** Correctness criteria, Evaluation windows, Scorecard content, Report scorecard

---

## Correctness Criteria

### Classification method
| Option | Description | Selected |
|--------|-------------|----------|
| Direction-based | BUY correct if up, SELL correct if down. HOLD correct if <2% | ✓ |
| Threshold-based | BUY correct only if >1% up. ±1% neutral zone | |
| Magnitude-weighted | Sliding scale 0-1 based on move size | |

**User's choice:** Direction-based
**Notes:** Simple, honest, easy to explain

### HOLD threshold
| Option | Description | Selected |
|--------|-------------|----------|
| ±2% band | Same for all assets | |
| ±3% band | More forgiving | |
| Asset-specific bands | Stocks: ±2%, Crypto: ±5% | ✓ |

**User's choice:** Asset-specific bands
**Notes:** Accounts for crypto's higher natural volatility

### Per-engine tracking
| Option | Description | Selected |
|--------|-------------|----------|
| Yes, per-engine tracking | Track each engine's directional accuracy separately | ✓ |
| Verdict-level only | Only track final LLM verdict accuracy | |

**User's choice:** Yes, per-engine tracking

### Evaluation timing
| Option | Description | Selected |
|--------|-------------|----------|
| Next day only | One evaluation per decision | |
| Multi-window | 24h, 3d, 7d, 30d intervals | ✓ |
| Configurable window | Default 24h, configurable via /settings | |

**User's choice:** Multi-window

### Evaluation windows selected
| Option | Description | Selected |
|--------|-------------|----------|
| 24h / next trading day | Short-term signal accuracy | ✓ |
| 3-day | Short-swing accuracy | ✓ |
| 7-day | Weekly outlook accuracy | ✓ |
| 30-day | Monthly accuracy | ✓ |

**User's choice:** All four windows

### Window threshold scaling
| Option | Description | Selected |
|--------|-------------|----------|
| Scale with window | Longer windows get wider HOLD bands | ✓ |
| Same threshold all windows | Keep ±2%/±5% regardless | |
| You decide | Claude picks scaling factors | |

**User's choice:** Scale with window

### Price capture timing
| Option | Description | Selected |
|--------|-------------|----------|
| Capture at decision time | Decide stage records decision_price | ✓ |
| Capture both at evaluation | Record both during evaluate stage | |

**User's choice:** Capture at decision time

---

## Evaluation Windows

### IDX trading calendar
| Option | Description | Selected |
|--------|-------------|----------|
| Static calendar in DB | Pre-populate holidays, manually update yearly | ✓ |
| Infer from price data | Assume non-trading if no price row exists | |
| Skip to next available price | Calendar-agnostic, find next close price | |

**User's choice:** Static calendar in DB

### Crypto evaluation price
| Option | Description | Selected |
|--------|-------------|----------|
| Close of next daily candle | Daily close from price_history | |
| Exact 24h snapshot | Price from hourly candles 24h after decision | ✓ |
| You decide | Claude picks best approach | |

**User's choice:** Exact 24h snapshot
**Notes:** Hourly candle data already available in price_history_hourly

### Pending evaluations
| Option | Description | Selected |
|--------|-------------|----------|
| Evaluate what's ready, skip the rest | Process matured windows only | ✓ |
| Backfill evaluations | Also re-check older skipped decisions | |

**User's choice:** Evaluate what's ready, skip the rest

---

## Scorecard Content

### Default /scorecard display
| Option | Description | Selected |
|--------|-------------|----------|
| Multi-window summary | Win rate per window, best/worst engine, buy-and-hold | ✓ |
| Simple summary | Just overall win rate and engine stats | |
| Per-asset breakdown | Full breakdown by asset and window | |

**User's choice:** Multi-window summary

### Command arguments
| Option | Description | Selected |
|--------|-------------|----------|
| /scorecard [period] | Optional period, default 30d | |
| /scorecard [period] [asset] | Both period and asset filters | ✓ |
| No arguments | Always shows 30-day summary | |

**User's choice:** /scorecard [period] [asset]

### Buy-and-hold baseline
| Option | Description | Selected |
|--------|-------------|----------|
| Per-asset over period | Calculate per watchlist asset over scorecard period | ✓ |
| Portfolio aggregate | Equal-weight portfolio aggregate | |
| You decide | Claude picks approach | |

**User's choice:** Per-asset over period

---

## Report Scorecard

### Detail level
| Option | Description | Selected |
|--------|-------------|----------|
| Per-asset results | Each asset with verdict, change %, correct/wrong emoji | ✓ |
| Summary only | Just "4/6 correct (67%)" | |
| Summary + worst miss | Summary plus biggest miss callout | |

**User's choice:** Per-asset results

### Evaluation window in report
| Option | Description | Selected |
|--------|-------------|----------|
| 24h / next trading day | Only shortest window | |
| Show all available windows | All matured windows with separate sections | ✓ |
| Configurable via /settings | User picks window for report | |

**User's choice:** Show all available windows

### Multi-window format
| Option | Description | Selected |
|--------|-------------|----------|
| Separate section per window | Yesterday's 24h first, then 7-day results, etc. | ✓ |
| Inline badge per result | All in one list with window badge | |
| 24h primary, others as summary | Full for 24h, summary stats for longer | |

**User's choice:** Separate section per window

### Trend indicator
| Option | Description | Selected |
|--------|-------------|----------|
| No trend indicator | Keep it clean | |
| Brief trend line | One line showing weekly win rate trend | ✓ |

**User's choice:** Brief trend line

### Empty state
| Option | Description | Selected |
|--------|-------------|----------|
| Skip section entirely | Omit when no evaluatable decisions | ✓ |
| Placeholder message | "No prior decisions to evaluate yet" | |

**User's choice:** Skip section entirely

---

## Claude's Discretion

- Exact HOLD threshold scaling values per window per asset type
- evaluations table schema details
- accuracy_stats table computation logic
- IDX holiday data source and initial population
- Evaluate stage implementation details
- Hourly candle query strategy for exact 24h snapshots
- Error handling for missing evaluation prices
- /scorecard message formatting
- Buy-and-hold return calculation method

## Deferred Ideas

None — discussion stayed within phase scope
