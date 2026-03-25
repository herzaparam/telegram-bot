# Phase 9: IDX Documents + Valuation Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-25
**Phase:** 09-IDX Documents + Valuation Engine
**Areas discussed:** PDF sourcing strategy, Financial data extraction, Valuation methodology, Telegram commands UX

---

## PDF Sourcing Strategy

### PDF Acquisition Method
| Option | Description | Selected |
|--------|-------------|----------|
| Auto-scrape idx.co.id | Scrape IDX website for latest quarterly/annual reports per watchlist stock. Runs during fetch stage. | ✓ |
| Semi-manual with cache | User uploads PDFs via Telegram or drops in a folder. | |
| You decide | Claude picks based on feasibility. | |

**User's choice:** Auto-scrape idx.co.id
**Notes:** None

### Report Types
| Option | Description | Selected |
|--------|-------------|----------|
| Quarterly + Annual | Fetch Q1, Q2, Q3 interim reports AND annual report. QoQ tracking. | ✓ |
| Annual only | Just the annual laporan tahunan. | |
| Latest available only | Most recent report, quarterly or annual. | |

**User's choice:** Quarterly + Annual
**Notes:** None

### Fetch Frequency
| Option | Description | Selected |
|--------|-------------|----------|
| Weekly check | Check idx.co.id once a week. Reports only update quarterly. | ✓ |
| On-demand only | Only fetch when user runs /valuation or /fundamentals. | |
| Daily with smart skip | Run daily but skip if latest already cached. | |

**User's choice:** Weekly check
**Notes:** None

### PDF Storage
| Option | Description | Selected |
|--------|-------------|----------|
| Store both | Save PDF locally AND extracted data to DB. Allows re-parsing. | ✓ |
| Extracted data only | Parse PDF, store structured data, discard PDF. | |
| You decide | Claude picks. | |

**User's choice:** Store both
**Notes:** None

### Parse Error Handling
| Option | Description | Selected |
|--------|-------------|----------|
| Retry with Vision LLM fallback | pymupdf4llm first, Vision LLM for mangled tables. Log partial results. | ✓ |
| Skip and alert | Skip stock's valuation with warning. No Vision LLM cost. | |
| You decide | Claude picks. | |

**User's choice:** Retry with Vision LLM fallback
**Notes:** Per architecture doc specification

### History Depth
| Option | Description | Selected |
|--------|-------------|----------|
| Last 4 quarters + 2 annual | Enables QoQ and YoY ratio tracking (VALN-05). | ✓ |
| Only latest | Overwrite with most recent. No trend analysis. | |
| Everything available | All historical reports. Maximum data. | |

**User's choice:** Last 4 quarters + 2 annual
**Notes:** None

### Scraper Resilience
| Option | Description | Selected |
|--------|-------------|----------|
| Graceful degradation + alert | Fall back to yfinance, log error, Telegram alert. | ✓ |
| Hard fail with manual override | Stop valuation, user uploads PDFs manually. | |
| You decide | Claude picks. | |

**User's choice:** Graceful degradation + alert
**Notes:** None

### Scraping Method
| Option | Description | Selected |
|--------|-------------|----------|
| Direct HTTP with httpx | Simpler, faster, lower resources. Falls back to yfinance if blocked. | ✓ |
| Headless browser (Playwright) | More robust against JS pages. Heavier dependency. | |
| You decide | Claude investigates and picks. | |

**User's choice:** Direct HTTP with httpx
**Notes:** None

---

## Financial Data Extraction

### Additional Fields
| Option | Description | Selected |
|--------|-------------|----------|
| Add management outlook + margins | Gross/operating/net margin, management guidance, capex. | ✓ |
| Stick to architecture basics | Just 5 fields: revenue, net profit, debt, operating CF, equity. | |
| Full income statement + balance sheet | Complete financials extraction. | |

**User's choice:** Add management outlook + margins
**Notes:** None

### Integration with FundamentalEngine
| Option | Description | Selected |
|--------|-------------|----------|
| PDF data enhances FundamentalEngine | PDF → ValuationEngine for DCF/peer. FundamentalEngine keeps yfinance. Complementary. | ✓ |
| PDF replaces yfinance | FundamentalEngine switches to PDF data. More accurate, slower refresh. | |
| You decide | Claude determines. | |

**User's choice:** PDF data enhances FundamentalEngine
**Notes:** None

### Bilingual Handling
| Option | Description | Selected |
|--------|-------------|----------|
| LLM handles translation in-prompt | Send Indonesian text to GPT-4o-mini with Indonesian field names. Returns structured output. | ✓ |
| Pre-translate then extract | Translate first, then extract. Two LLM calls, 2x cost. | |
| You decide | Claude picks. | |

**User's choice:** LLM handles translation in-prompt
**Notes:** Per architecture doc specification

### Cross-Validation
| Option | Description | Selected |
|--------|-------------|----------|
| Cross-validate key metrics | Compare PDF revenue/profit with yfinance. Flag >10% discrepancies. | ✓ |
| No cross-validation | Trust LLM extraction. Simpler. | |
| You decide | Claude determines. | |

**User's choice:** Cross-validate key metrics
**Notes:** None

### Database Schema
| Option | Description | Selected |
|--------|-------------|----------|
| financial_docs + financial_data tables | Normalized, queryable. financial_docs for metadata, financial_data for extracted fields. | ✓ |
| Single JSONB column | All fields as JSONB blob. Simpler schema, harder queries. | |
| You decide | Claude designs. | |

**User's choice:** financial_docs + financial_data tables
**Notes:** None

---

## Valuation Methodology

### DCF Parameters
| Option | Description | Selected |
|--------|-------------|----------|
| Formula-based with market inputs | WACC from risk-free rate + ERP + beta. Growth from historical CAGR capped at GDP growth. | ✓ |
| LLM-estimated | LLM proposes rates with reasoning. Less reproducible. | |
| Fixed conservative defaults | Standard 10% discount, sector-average growth. | |
| You decide | Claude picks. | |

**User's choice:** Formula-based with market inputs
**Notes:** None

### Peer Groups
| Option | Description | Selected |
|--------|-------------|----------|
| Sector-based from IDX classification | Group by IDX sector (Banking, Telco, etc.). Compare multiples within sector. | ✓ |
| Manual peer mapping | Pre-define peer groups in config. More accurate, manual maintenance. | |
| You decide | Claude determines. | |

**User's choice:** Sector-based from IDX classification
**Notes:** None

### Crypto Valuation
| Option | Description | Selected |
|--------|-------------|----------|
| NVT + simple metrics only | NVT for BTC/ETH, mcap/TVL for DeFi. Lightweight. Phase 10 adds more. | ✓ |
| Skip crypto valuation entirely | IDX stocks only. score=0/confidence=0 for crypto. | |
| Full crypto valuation suite | Stock-to-flow, revenue multiples, token economics. | |

**User's choice:** NVT + simple metrics only
**Notes:** None

### Scenario Analysis
| Option | Description | Selected |
|--------|-------------|----------|
| Revenue growth ± standard deviation | Base = CAGR, Bull = +1 SD, Bear = -1 SD. Weights: 25/50/25. | ✓ |
| LLM-generated scenarios | LLM writes narratives with custom assumptions. | |
| You decide | Claude picks. | |

**User's choice:** Revenue growth ± standard deviation
**Notes:** None

---

## Telegram Commands UX

### /valuation Output Detail
| Option | Description | Selected |
|--------|-------------|----------|
| Summary + key numbers | Fair value, current price, MoS %, DCF range, peer rank. One message. | ✓ |
| Full analysis report | Detailed DCF table, all multiples, scenario breakdown. Multi-message. | |
| You decide | Claude designs. | |

**User's choice:** Summary + key numbers
**Notes:** None

### /fundamentals vs /valuation Split
| Option | Description | Selected |
|--------|-------------|----------|
| /fundamentals = ratios, /valuation = fair value | Complementary views. Ratios vs fair value estimate. | ✓ |
| Merge into one command | Single /analysis command with both. | |
| You decide | Claude determines. | |

**User's choice:** /fundamentals = ratios, /valuation = fair value
**Notes:** None

### Daily Report Valuation Summary
| Option | Description | Selected |
|--------|-------------|----------|
| Compact table per IDX stock | One line per stock: ticker, price, fair value, MoS %, arrow. | ✓ |
| Detailed paragraph per stock | 2-3 sentences per stock explaining context. | |
| You decide | Claude designs. | |

**User's choice:** Compact table per IDX stock
**Notes:** None

### No Financial Docs Available
| Option | Description | Selected |
|--------|-------------|----------|
| Show yfinance-based estimate with disclaimer | Rough valuation from market data, clearly marked as estimate. | ✓ |
| Show 'Unavailable' | Clear message that reports are needed. No estimate. | |
| You decide | Claude picks. | |

**User's choice:** Show yfinance-based estimate with disclaimer
**Notes:** None

### Crypto Command Behavior
| Option | Description | Selected |
|--------|-------------|----------|
| IDX stocks only, crypto shows message | "Valuation not available for crypto — use /report BTC" | ✓ |
| Show crypto proxies for /valuation | NVT and basic metrics for /valuation BTC. | |
| You decide | Claude determines. | |

**User's choice:** IDX stocks only, crypto shows message
**Notes:** None

### QoQ Alert Delivery
| Option | Description | Selected |
|--------|-------------|----------|
| Include in daily report only | Highlight significant ratio changes in next daily report. No push. | ✓ |
| Push alert immediately | Separate Telegram message on detection. | |
| You decide | Claude picks. | |

**User's choice:** Include in daily report only
**Notes:** None

---

## Claude's Discretion

- idx.co.id URL structure and scraping implementation
- pymupdf4llm extraction parameters and Vision LLM trigger conditions
- LLM prompt design for extraction
- Database table schemas and indexes
- WACC calculation specifics
- Peer comparison weights and ranking
- Crypto proxy data sources
- Scenario terminal value methodology
- Telegram message formatting
- QoQ change thresholds
- Error handling and retry logic
- Alembic migration details

## Deferred Ideas

None — discussion stayed within phase scope
