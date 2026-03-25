---
phase: 08-fundamental-macro-sentiment-and-news-engines
plan: 02
subsystem: data-fetchers
tags: [yfinance, fredapi, feedparser, finnhub, asyncpraw, httpx, sqlalchemy, tdd]

requires:
  - phase: 08-fundamental-macro-sentiment-and-news-engines
    plan: 01
    provides: StockFundamental/MacroData/NewsEvent ORM models, API key Settings fields

provides:
  - fetch_fundamentals() per-stock yfinance .info fetcher with 7-day cache and pg_insert UPSERT
  - fetch_macro_data() FRED 4-series fetcher with empty-key guard and partial success
  - fetch_news() RSS + Finnhub fetcher with URL dedup and empty-key guard
  - fetch_sentiment_data() Fear & Greed + Reddit fetcher returning SentimentSnapshot

affects:
  - 08-03 (engines read data written by these fetchers; SentimentSnapshot passed to SentimentEngine)

tech-stack:
  added: [feedparser>=6.0.12, fredapi>=0.5.2, asyncpraw>=7.2.0, finnhub-python>=2.4.27]
  patterns:
    - "yfinance and fredapi sync calls wrapped in asyncio.get_event_loop().run_in_executor(None, ...)"
    - "pg_insert with on_conflict_do_update for UPSERT on named constraints"
    - "Empty-key string guard pattern: if settings.fred_api_key == '': return"
    - "SentimentSnapshot dataclass returned to caller (not stored in DB)"
    - "asyncio.gather() for concurrent Fear & Greed + Reddit subreddit fetches"

key-files:
  created:
    - src/data/fundamental_fetcher.py
    - src/data/macro_fetcher.py
    - src/data/news_fetcher.py
    - src/data/sentiment_fetcher.py
    - tests/test_data/test_fundamental_fetcher.py
    - tests/test_data/test_macro_fetcher.py
    - tests/test_data/test_news_fetcher.py
    - tests/test_data/test_sentiment_fetcher.py
  modified:
    - pyproject.toml
    - src/config.py
    - src/db/models.py

key-decisions:
  - "SentimentSnapshot is not stored in DB -- passed directly to SentimentEngine as constructor arg; same pattern as macro data passed to MacroEngine"
  - "session.add() used for NewsEvent INSERT (not pg_insert) to allow SQLAlchemy ORM identity map to manage object lifecycle"
  - "Phase 08-01 prerequisites (ORM models, config fields, pyproject deps) were missing from worktree -- added as Rule 3 deviation before fetcher implementation"
  - "_fetch_yfinance_info catches all exceptions internally, returns empty dict; fetch_fundamentals checks empty dict and returns without DB write"
  - "FRED series each wrapped in try/except in executor to allow partial success across 4 series"

metrics:
  duration: 5min
  completed: 2026-03-25
  tasks: 2
  files_created: 8
  files_modified: 3
---

# Phase 08 Plan 02: Data Fetchers Summary

**Four async data fetchers implementing yfinance fundamentals, FRED macro, RSS+Finnhub news, and Fear&Greed+Reddit sentiment with pg_insert UPSERT, 7-day cache, URL dedup, empty-key guards, and full TDD test coverage.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-25T09:40:43Z
- **Completed:** 2026-03-25T09:45:49Z
- **Tasks:** 2
- **Files created:** 8
- **Files modified:** 3

## Accomplishments

- Implemented `fetch_fundamentals()` in `src/data/fundamental_fetcher.py`:
  - Wraps `yfinance.Ticker(symbol).info` in `run_in_executor` for async safety
  - Checks existing `StockFundamental` row freshness (7-day TTL) before fetching
  - Skips crypto assets immediately (`asset.asset_type != "stock"` guard)
  - UPSERT via `pg_insert(...).on_conflict_do_update(constraint="uq_stock_fundamentals_asset", ...)`
  - Returns gracefully when yfinance returns empty dict

- Implemented `fetch_macro_data()` in `src/data/macro_fetcher.py`:
  - Fetches 4 FRED series (DFF, CPIAUCSL, DTWEXBGS, CCUSMA02IDM618N)
  - `if settings.fred_api_key == ""` guard skips entirely when unconfigured
  - Each series independently wrapped in try/except -- partial success allowed
  - UPSERT via `pg_insert(...).on_conflict_do_update(constraint="uq_macro_data_series_date", ...)`

- Implemented `fetch_news()` in `src/data/news_fetcher.py`:
  - `RSS_FEEDS` dict with kontan/cnbc_id/bisnis sources
  - `_parse_rss_feed()` sync function via `run_in_executor`, catches all exceptions
  - URL dedup via `SELECT ... WHERE url = ?` before each INSERT
  - `_fetch_finnhub_news_sync()` capped at 30 headlines, `finnhub_api_key` guard
  - Top-level exception catch (SUPPLEMENTARY tier)

- Implemented `fetch_sentiment_data()` in `src/data/sentiment_fetcher.py`:
  - `SentimentSnapshot` dataclass with `fear_greed_value`, `fear_greed_classification`, `reddit_posts`
  - `_fetch_fear_greed()` via `httpx.AsyncClient` to `api.alternative.me/fng`
  - `_fetch_reddit_posts()` via `asyncpraw.Reddit` with async context manager
  - `asyncio.gather()` for concurrent Fear & Greed + r/cryptocurrency + r/finansial
  - `reddit_client_id == ""` guard skips Reddit, returns Fear & Greed only

## Task Commits

Each task was committed atomically:

1. **Task 1: Fundamental and macro data fetchers with tests** - `feaab21` (feat)
2. **Task 2: News and sentiment data fetchers with tests** - `93c36ee` (feat)

## Files Created

- `src/data/fundamental_fetcher.py` - fetch_fundamentals() with yfinance, 7-day cache, UPSERT
- `src/data/macro_fetcher.py` - fetch_macro_data() with FRED, 4 series, empty-key guard
- `src/data/news_fetcher.py` - fetch_news() with RSS_FEEDS + Finnhub, URL dedup
- `src/data/sentiment_fetcher.py` - fetch_sentiment_data() with SentimentSnapshot, Fear & Greed + Reddit
- `tests/test_data/test_fundamental_fetcher.py` - 5 tests
- `tests/test_data/test_macro_fetcher.py` - 3 tests
- `tests/test_data/test_news_fetcher.py` - 5 tests
- `tests/test_data/test_sentiment_fetcher.py` - 4 tests

## Files Modified

- `pyproject.toml` - Added feedparser, fredapi, asyncpraw, finnhub-python dependencies
- `src/config.py` - Added API key fields + engine weight fields (deferred from 08-01)
- `src/db/models.py` - Added NewsEvent, MacroData, StockFundamental ORM models (deferred from 08-01)

## Decisions Made

- `SentimentSnapshot` is returned to the caller (not stored in DB); the SentimentEngine in Plan 03 will consume it directly
- `_fetch_yfinance_info()` catches all exceptions and returns empty dict; `fetch_fundamentals()` treats empty dict as a failed fetch and returns without writing
- FRED series fetches use individual try/except blocks to allow partial success (3 of 4 series is better than 0 of 4)
- `session.add()` pattern used for NewsEvent INSERT (not pg_insert) since news rows are always new (URL dedup check happens before the add call)

## Deviations from Plan

### Auto-fixed Issues (Rule 3: Blocking)

**1. [Rule 3 - Blocking] Prerequisites from 08-01 missing from worktree**
- **Found during:** Task 1 setup
- **Issue:** This worktree did not have the ORM models (StockFundamental, MacroData, NewsEvent), config fields (fred_api_key, etc.), or pyproject.toml deps (feedparser, fredapi, asyncpraw, finnhub-python) that should have been added in Plan 08-01
- **Fix:** Added all Phase 08-01 prerequisites inline before implementing fetchers: ORM models, Settings fields, and pyproject.toml dependencies
- **Files modified:** `pyproject.toml`, `src/config.py`, `src/db/models.py`
- **Commit:** `feaab21` (included in Task 1 commit)

## Known Stubs

None. All fetchers are fully wired to real external APIs (with graceful degradation when keys missing). Impact scoring (LLM) for news events is intentionally deferred to Plan 03 -- `impact_score=None` and `category=None` are set explicitly and documented in the plan spec.

## Test Results

All 17 tests pass:
- `test_fundamental_fetcher.py`: 5/5 passed
- `test_macro_fetcher.py`: 3/3 passed
- `test_news_fetcher.py`: 5/5 passed
- `test_sentiment_fetcher.py`: 4/4 passed

---
*Phase: 08-fundamental-macro-sentiment-and-news-engines*
*Completed: 2026-03-25*
