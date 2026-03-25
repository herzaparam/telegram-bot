---
phase: 08-fundamental-macro-sentiment-and-news-engines
plan: 04
subsystem: pipeline-integration
tags: [analyze, pipeline, formatter, engines, news, integration, tdd]

requires:
  - phase: 08-fundamental-macro-sentiment-and-news-engines
    plan: 02
    provides: fetch_fundamentals, fetch_macro_data, fetch_news, fetch_sentiment_data fetchers
  - phase: 08-fundamental-macro-sentiment-and-news-engines
    plan: 03
    provides: FundamentalEngine, MacroEngine, SentimentEngine, EventEngine, score_news_impact

provides:
  - Extended analyze_stage loading 6 engines with store-backed data (fundamentals, macro, sentiment, news)
  - fetch_global_data() orchestrating macro+news+sentiment fetch + LLM scoring before per-asset pipeline
  - _enhanced_ingest_stage wrapping ingest_stage + per-asset fundamental fetch
  - format_news_digest() HTML formatter for News & Events section in daily report
  - Daily report including News & Events section at the bottom

affects:
  - Pipeline end-to-end: full 6-engine signal generation per asset
  - Daily Telegram report: now includes news digest at bottom

tech-stack:
  added: []
  patterns:
    - "Store-backed data injection: analyze_stage loads fundamentals, macro, news from DB before running engines"
    - "Module-level sentiment cache: set_sentinel_cache() in analyze.py, populated by fetch_global_data"
    - "Graceful global fetch: each fetcher wrapped in try/except, partial success always preferred"
    - "News digest appended as last card in report card list, not hardcoded into header"
    - "HTML abs-sort for news: absolute impact_score sort descending, cap at 10, group by category"

key-files:
  created:
    - tests/test_data/test_analyze_extended.py
    - tests/test_report/test_formatter_news.py
    - .planning/phases/08-fundamental-macro-sentiment-and-news-engines/deferred-items.md
  modified:
    - src/data/analyze.py
    - src/pipeline/main.py
    - src/report/formatter.py
    - src/data/report.py
    - tests/test_data/test_analyze.py

key-decisions:
  - "analyze_stage loads fundamentals only for stock assets (crypto skip via conditional)"
  - "_sentiment_cache module global set by fetch_global_data -- avoids DB storage for ephemeral snapshot"
  - "fetch_global_data wraps each call in try/except for partial success (macro down != no news)"
  - "News digest appended as last card in cards list before split_report (D-19: bottom of report)"
  - "format_news_digest catches absent/None impact_score items before display"
  - "test_report_stage.py pre-existing failure logged to deferred-items.md (out of scope)"

patterns-established:
  - "6-engine pattern: TechnicalEngine + QuantitativeEngine + FundamentalEngine + MacroEngine + SentimentEngine + EventEngine per asset"
  - "Pipeline orchestration: fetch_global_data -> _enhanced_ingest_stage (price+fundamentals) -> analyze (6 engines) -> decide"

requirements-completed: [ENGN-02, ENGN-05, ENGN-09, ENGN-12, NEWS-03, NEWS-04]

duration: 11min
completed: 2026-03-25
---

# Phase 08 Plan 04: Pipeline Integration and News Report Summary

**Extended analyze_stage to load store-backed data and run 6 engines, added global data fetching to pipeline orchestration, and wired News & Events section into the daily Telegram report.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-25T09:56:18Z
- **Completed:** 2026-03-25T10:07:xx
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Extended `src/data/analyze.py` with three store-backed data helpers:
  - `_load_fundamentals(session, asset_id)` — queries StockFundamental, returns dict of 6 ratios
  - `_load_latest_macro(session)` — queries MacroData with max-date subquery, maps series_id to friendly name
  - `_load_recent_news(session)` — queries today's scored NewsEvent rows

- Extended `_get_engines_for_asset()` to accept context args (fundamentals, macro_data, sentiment_data, news_events) and instantiate all 6 engines with constructor injection

- Added `set_sentiment_cache()` / `_sentiment_cache` module global for pipeline-wide sentiment sharing

- Added `fetch_global_data()` to `src/pipeline/main.py`:
  - Calls `fetch_macro_data`, `fetch_news`, `fetch_sentiment_data` with individual try/except
  - Sets sentiment cache via `set_sentiment_cache()`
  - Queries watchlist symbols and calls `score_news_impact()` for LLM news scoring

- Added `_enhanced_ingest_stage()` wrapping `ingest_stage` + `fetch_fundamentals` per asset

- Updated pipeline `stage_funcs` to use `_enhanced_ingest_stage` for the "fetch" stage

- Added `format_news_digest()` to `src/report/formatter.py`:
  - Filters None-scored items, sorts by abs(impact_score) descending, caps at 10
  - Groups by category with human-readable labels (Central Bank, Earnings, etc.)
  - Shows direction indicator (green/red/white), headline, source, affected assets

- Updated `src/data/report.py` to query today's NewsEvent rows and append news digest as last report card

## Task Commits

Each task was committed atomically (TDD: RED, then GREEN):

1. **Task 1 RED: failing tests for extended analyze_stage** - `a85d5d5` (test)
2. **Task 1 GREEN: extended analyze_stage + pipeline main** - `e52a135` (feat)
3. **Task 2 RED: failing tests for format_news_digest** - `920a3d9` (test)
4. **Task 2 GREEN: format_news_digest + report wiring** - `8212d34` (feat)

## Files Created

- `tests/test_data/test_analyze_extended.py` - 11 tests for extended analyze_stage and fetch_global_data
- `tests/test_report/test_formatter_news.py` - 14 tests for format_news_digest

## Files Modified

- `src/data/analyze.py` - Added 3 DB helpers, extended _get_engines_for_asset, sentiment cache, updated analyze_stage
- `src/pipeline/main.py` - Added fetch_global_data, _enhanced_ingest_stage, updated stage_funcs
- `src/report/formatter.py` - Added format_news_digest function
- `src/data/report.py` - Import format_news_digest + NewsEvent, query news, append news section
- `tests/test_data/test_analyze.py` - Updated mock patches and signal count expectations to match 6-engine output

## Decisions Made

- `analyze_stage` loads fundamentals only for stock assets (`asset.asset_type == "stock"`) since FundamentalEngine handles None gracefully
- `_sentiment_cache` is a module-level global in analyze.py, set once by `fetch_global_data` in main.py — avoids DB round-trip for SentimentSnapshot on every per-asset analyze call
- `fetch_global_data` catches individual fetcher errors — FRED down does not prevent news or sentiment fetching
- News digest appended as the last item in the `cards` list passed to `split_report` (not in header) so it appears at bottom of the report (D-19)
- Pre-existing failing test `test_send_daily_report_with_decisions` logged to deferred-items.md (out of scope — existed before 08-04)

## Deviations from Plan

### Setup Fix (not a code deviation)

**Cherry-pick of Phase 08-01 through 08-03 code commits into worktree**
- **Found during:** Pre-execution check
- **Issue:** This worktree (worktree-agent-afa734fe) was at main HEAD which lacked the code commits from sibling worktrees for plans 08-01 through 08-03 (engines, fetchers, ORM models)
- **Fix:** Cherry-picked 8 commits from sibling worktree branches (worktree-agent-ac0c6c05, worktree-agent-a6bd01e4, worktree-agent-adf1a051). Resolved 2 trivial merge conflicts in config.py and models.py (comment text only)
- **Impact:** None — plan executed exactly as written after setup

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing test_analyze.py to match 6-engine output**
- **Found during:** Task 1 GREEN phase
- **Issue:** Existing tests expected 2 signals (technical + quantitative only). After extending to 6 engines, those tests failed with wrong mock setup and signal count assertions
- **Fix:** Added mock patches for `_load_fundamentals`, `_load_latest_macro`, `_load_recent_news`, updated signal count expectations from 2 to 6
- **Files modified:** `tests/test_data/test_analyze.py`

**2. [Rule 1 - Bug] Fixed test_caps_at_ten_headlines substring collision**
- **Found during:** Task 2 GREEN phase
- **Issue:** Test used `f"Headline {i}"` identifiers; "Headline 1" substring matched "Headline 10", "Headline 11", etc., causing false headline count of 11
- **Fix:** Changed identifiers to zero-padded `f"Item-{i:03d}-news"` format for unique matching
- **Files modified:** `tests/test_report/test_formatter_news.py`

## Known Stubs

None. All integration wiring is complete:
- `_load_fundamentals` → `StockFundamental` table (written by `fetch_fundamentals` in enhanced ingest stage)
- `_load_latest_macro` → `MacroData` table (written by `fetch_macro_data` in fetch_global_data)
- `_load_recent_news` → `NewsEvent` table (written by `fetch_news`, scored by `score_news_impact` in fetch_global_data)
- `_sentiment_cache` → populated from `SentimentSnapshot` returned by `fetch_sentiment_data`

## Self-Check: PASSED

All created and modified files verified present. All task commits verified:
- `a85d5d5`: test(08-04) RED phase for extended analyze_stage and fetch_global_data
- `e52a135`: feat(08-04) GREEN phase for extended analyze_stage + pipeline main
- `920a3d9`: test(08-04) RED phase for format_news_digest and news report integration
- `8212d34`: feat(08-04) GREEN phase for format_news_digest + report wiring

All 551 tests pass (excluding pre-existing broken test `test_send_daily_report_with_decisions` which fails before 08-04 changes).
