# Phase 8: Fundamental, Macro, Sentiment, and News Engines - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 08-fundamental-macro-sentiment-and-news-engines
**Areas discussed:** Fundamental data sources, Macro engine architecture, Sentiment sources & access, News ingestion & LLM scoring

---

## Fundamental Data Sources

| Option | Description | Selected |
|--------|-------------|----------|
| yfinance .info only | Use yfinance's .info dict for IDX tickers — trailingPE, priceToBook, returnOnEquity, revenueGrowth. Cache in DB, refresh weekly. | ✓ |
| yfinance + manual IDX scrape | Primary yfinance, fallback scrape idx.co.id summary pages. More complete but fragile. | |
| yfinance + Stockbit scrape | Primary yfinance, supplement with Stockbit fundamental data. Richer but unreliable. | |

**User's choice:** yfinance .info only
**Notes:** Simplest to implement, no new API keys needed.

### Crypto Fundamental Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Score=0, confidence=0 | Return zero score with reasoning "not applicable". Matches roadmap success criteria. | ✓ |
| Skip engine entirely for crypto | Set supports_crypto=False. Cleaner but LLM won't see engine in crypto signal sets. | |

**User's choice:** Score=0, confidence=0

### Refresh Frequency

| Option | Description | Selected |
|--------|-------------|----------|
| Weekly refresh | Cache in fundamentals table, skip if <7 days old. Fundamentals change quarterly at most. | ✓ |
| Daily refresh | Fetch every pipeline run. Simpler but wastes API calls. | |

**User's choice:** Weekly refresh

### Ratio Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Core 4 from requirements | P/E, P/B, revenue growth, ROE — exactly ENGN-02 | |
| Core 4 + dividend yield + debt/equity | Add dividend yield and D/E for richer picture | ✓ |
| You decide | Claude picks based on yfinance .info availability | |

**User's choice:** Core 4 + dividend yield + debt/equity

---

## Macro Engine Architecture

### Data Integration Pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Fetch-then-cache pattern | Macro fetcher stores in macro_data table. MacroEngine reads from DB during analyze. | ✓ |
| Pre-load macro context into engine | Macro data passed to engine constructor. Breaks stateless pattern. | |
| Separate macro stage | New pipeline stage between fetch and analyze. | |

**User's choice:** Fetch-then-cache pattern

### Macro Data Sources

| Option | Description | Selected |
|--------|-------------|----------|
| FRED only | Covers Fed rate, CPI, DXY, USD/IDR. Single API, free, fredapi library. | ✓ |
| FRED + Bank Indonesia API | More accurate IDR data but BI's API is unreliable. | |
| FRED + World Bank API | World Bank updates slowly but is reliable. | |

**User's choice:** FRED only

### Stock vs Crypto Differentiation

| Option | Description | Selected |
|--------|-------------|----------|
| Same score, different reasoning | One global score, reasoning highlights relevant factors per asset type. LLM interprets. | ✓ |
| Asset-type-specific scoring | Separate sub-scores per asset type. More nuanced but complex. | |
| You decide | | |

**User's choice:** Same score, different weighting in reasoning

---

## Sentiment Sources & Access

### Source Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Fear & Greed + Reddit only | alternative.me (free, no auth) + Reddit PRAW (r/cryptocurrency, r/finansial). Skip Stockbit. | ✓ |
| Fear & Greed + Reddit + Stockbit | All three from ARCHITECTURE.md. Stockbit adds IDX sentiment but scraping is fragile. | |
| Fear & Greed only | Just crypto Fear & Greed. Simple but limited — no IDX sentiment. | |

**User's choice:** Fear & Greed + Reddit only

### Reddit Analysis Method

| Option | Description | Selected |
|--------|-------------|----------|
| LLM batch analysis | Fetch ~20 posts/subreddit, one LLM call per subreddit. ~$0.02/day. | ✓ |
| Keyword + VADER scoring | NLP-based, no LLM cost. Less accurate for financial context. | |
| You decide | | |

**User's choice:** LLM batch analysis

### Reddit API Access

| Option | Description | Selected |
|--------|-------------|----------|
| No, will register | Create Reddit app at reddit.com/prefs/apps. Add credentials to .env. | ✓ |
| Yes, already have one | | |
| Skip Reddit for now | Start with Fear & Greed only. | |

**User's choice:** No, will register

---

## News Ingestion & LLM Scoring

### News Pipeline Design

| Option | Description | Selected |
|--------|-------------|----------|
| Part of fetch stage | News fetchers run alongside price fetchers. Cached in news_events table. | ✓ |
| Separate news stage | New 'fetch_news' stage. Explicit separation but adds complexity. | |
| Standalone news pipeline | Own scheduled job. Most decoupled but operationally complex. | |

**User's choice:** Part of fetch stage

### LLM Scoring Method

| Option | Description | Selected |
|--------|-------------|----------|
| Batch LLM call | All headlines in one call with watchlist. ~$0.03/day. | ✓ |
| Per-headline LLM calls | One call per headline. Higher cost and latency. | |
| Keyword-first, LLM for ambiguous | Keyword matching + LLM fallback. Harder to implement well. | |

**User's choice:** Batch LLM call

### Finnhub API Access

| Option | Description | Selected |
|--------|-------------|----------|
| No, will register | Sign up at finnhub.io for free API key. | ✓ |
| Yes, already have one | | |
| Skip Finnhub for now | RSS feeds only. Crypto news will have gaps. | |

**User's choice:** No, will register

### Daily Report News Format

| Option | Description | Selected |
|--------|-------------|----------|
| Separate news section | "News & Events" section at bottom. Top 5-10 headlines grouped by category. | ✓ |
| Inline per asset | News under each asset's signal card. More contextual but longer. | |
| Both | Separate section + inline mentions. Most complete but longest. | |

**User's choice:** Separate news section

---

## Claude's Discretion

- Zone thresholds for fundamental ratio scoring
- FRED series IDs, macro score computation, refresh frequency
- Reddit post selection, LLM prompt design for sentiment and news
- Event engine scoring logic, RSS deduplication, Finnhub endpoint selection
- Table schemas, migration details, error handling per data source

## Deferred Ideas

None — discussion stayed within phase scope
