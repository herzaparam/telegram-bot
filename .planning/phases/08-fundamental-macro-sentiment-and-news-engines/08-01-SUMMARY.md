---
phase: 08-fundamental-macro-sentiment-and-news-engines
plan: 01
subsystem: database
tags: [feedparser, fredapi, asyncpraw, finnhub-python, sqlalchemy, alembic, pydantic-settings]

requires:
  - phase: 07-self-evaluation-feedback-loop
    provides: Lesson ORM model and migration 006 (down_revision for 007)

provides:
  - NewsEvent ORM model with url-unique constraint and LLM-scored impact fields
  - MacroData ORM model caching FRED series values by date
  - StockFundamental ORM model caching yfinance .info fundamentals per asset
  - Alembic migration 007 creating all three tables with indexes
  - Settings fields for FRED, Finnhub, Reddit API keys
  - Settings weight fields for fundamental (6), macro (4), and sentiment (2) engines

affects:
  - 08-02 (news fetcher uses NewsEvent model and finnhub_api_key)
  - 08-03 (macro fetcher uses MacroData model and fred_api_key)
  - 08-04 (fundamental engine uses StockFundamental model)

tech-stack:
  added: [feedparser==6.0.12, fredapi==0.5.2, asyncpraw==7.2.0, finnhub-python==2.4.27]
  patterns:
    - "External API keys default empty string -- engines degrade gracefully when missing"
    - "Engine weight groups named by domain prefix (weight_fundamental_*, weight_macro_*, weight_sentiment_*)"
    - "Migration 007 uses op.create_table() with named PK/UQ constraints following 006 pattern"

key-files:
  created:
    - src/db/migrations/versions/007_news_macro_fundamentals.py
    - .env.example
  modified:
    - pyproject.toml
    - src/config.py
    - src/db/models.py

key-decisions:
  - "API keys default to empty string so Settings() always instantiates; engines check and skip gracefully"
  - "StockFundamental uses UniqueConstraint on asset_id (one record per asset, upserted on weekly refresh)"
  - "MacroData unique on (series_id, observation_date) to allow historical backfill without duplicates"
  - "news_events.fetched_at indexed for date-range queries; macro_data.series_id indexed for series lookup"

patterns-established:
  - "migration 007 down_revision=006, follows same create_table/PrimaryKeyConstraint/UniqueConstraint naming pattern"

requirements-completed: [ENGN-02, ENGN-12, ENGN-05, ENGN-09, NEWS-01, NEWS-02]

duration: 2min
completed: 2026-03-25
---

# Phase 08 Plan 01: Deps, Config, ORM Models, and Migration 007 Summary

**Three new DB tables (news_events, macro_data, stock_fundamentals) with ORM models and Alembic migration 007, plus feedparser/fredapi/asyncpraw/finnhub-python dependencies and 16 new Settings fields.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-25T09:35:38Z
- **Completed:** 2026-03-25T09:37:45Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Installed four new libraries (feedparser, fredapi, asyncpraw, finnhub-python) into pyproject.toml
- Extended Settings class with 4 API key fields and 12 engine weight fields across 3 domains
- Added NewsEvent, MacroData, and StockFundamental ORM models with correct schemas and constraints
- Created Alembic migration 007 that creates all 3 tables with unique constraints and indexes

## Task Commits

Each task was committed atomically:

1. **Task 1: Install deps and extend Settings** - `775a660` (feat)
2. **Task 2: ORM models and migration 007** - `2301688` (feat)

## Files Created/Modified

- `pyproject.toml` - Added feedparser, fredapi, asyncpraw, finnhub-python to dependencies
- `src/config.py` - Added fred_api_key, finnhub_api_key, reddit_client_id, reddit_client_secret and 12 weight fields
- `src/db/models.py` - Added NewsEvent, MacroData, StockFundamental ORM classes
- `src/db/migrations/versions/007_news_macro_fundamentals.py` - Alembic migration creating 3 tables
- `.env.example` - Created with Phase 8 API key stubs

## Decisions Made

- API keys default to empty string (not None/Optional) so Settings always instantiates; fetcher engines will check and skip gracefully when missing
- StockFundamental unique on asset_id (one cached record per asset, weekly upsert)
- MacroData unique on (series_id, observation_date) to allow backfill without duplicates
- Indexes on news_events.fetched_at and macro_data.series_id per plan spec for efficient date-range and series queries

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**External services require manual configuration before Phase 8 engines can fetch live data:**

| Service | Env Var | Source |
|---------|---------|--------|
| FRED | `FRED_API_KEY` | https://fred.stlouisfed.org/docs/api/api_key.html |
| Finnhub | `FINNHUB_API_KEY` | https://finnhub.io/register |
| Reddit | `REDDIT_CLIENT_ID` | https://www.reddit.com/prefs/apps |
| Reddit | `REDDIT_CLIENT_SECRET` | Same Reddit app page |

Engines degrade gracefully when keys are missing (return neutral signals), so the pipeline remains functional without them.

## Next Phase Readiness

- Foundation complete; 08-02 (news fetcher), 08-03 (macro fetcher), and 08-04 (fundamental engine) can all start
- Migration 007 must be run against the live DB before Phase 8 engines are activated
- uv.lock updated; run `uv sync` on the VPS to install new packages

---
*Phase: 08-fundamental-macro-sentiment-and-news-engines*
*Completed: 2026-03-25*
