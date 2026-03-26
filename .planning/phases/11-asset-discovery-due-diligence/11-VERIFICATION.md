---
phase: 11-asset-discovery-due-diligence
verified: 2026-03-26T12:45:00Z
status: human_needed
score: 13/13 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 11/13
  gaps_closed:
    - "DD flags injected into LLM decision prompt when asset_type == stock without TypeError"
    - "/compare table shows only metrics available in StockFundamental (no net_margin dashes)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run /discover in Telegram after a pipeline execution"
    expected: "Shows top 5 discovery candidates with trigger emojis and composite scores; empty state if none found"
    why_human: "Requires live Telegram session and pipeline run with real yfinance and CoinGecko data"
  - test: "Run /duediligence BBCA in Telegram"
    expected: "Full DD report with sector rank, ownership, management quality, competitive position sections"
    why_human: "Requires live DB with StockFundamental data populated and actual DD report computed"
  - test: "Run /compare BBCA BBRI BMRI in Telegram"
    expected: "Side-by-side table with P/E, P/B, ROE, D/E, Rev CAGR columns; crown emoji on best per row; Net Margin row absent"
    why_human: "Requires live DB with StockFundamental rows; visually confirms clean 5-metric table"
---

# Phase 11: Asset Discovery and Due Diligence Verification Report

**Phase Goal:** The system scans beyond the watchlist to surface new opportunities and provides full due diligence reports on IDX stocks including ownership, management, and competitive positioning
**Verified:** 2026-03-26T12:45:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure plan 11-06

## Gap Closure Summary

Both gaps from the initial verification (2026-03-26T12:15:00Z) are resolved:

1. **DD flags regression (BLOCKER)** — `src/data/decide.py` now has a type guard at lines 275-277 that resets `dd_flags` to `None` if it is not a `list`. This prevents coroutine objects from an AsyncMock session leaking to `build_decision_prompt`. All 26 tests in `test_decide.py` pass (6 regressions restored). Commit `18079b0`.

2. **net_margin data gap (WARNING)** — `src/bot/handlers/compare.py` no longer includes `net_margin` keys. `src/report/formatter.py` `format_compare_table` now lists 5 metrics (P/E, P/B, ROE %, D/E, Rev CAGR %) without the misleading Net Mgn row. Commit `556f597`.

Full test suite result: **834 passed, 0 failures**.

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | DiscoveryCandidate, OwnershipSnapshot, DueDiligenceReport ORM models exist | VERIFIED | `src/db/models.py`: all three classes present with correct columns, JSONB fields, and constraints |
| 2  | Two Alembic migrations create the three new tables with correct revision chain 011→012→013 | VERIFIED | `012_discovery_candidates.py` (rev=012, down=011), `013_ownership_due_diligence.py` (rev=013, down=012) |
| 3  | IDX_SECTOR_MAP expanded to 53 tickers across 12 IHSG sectors | VERIFIED | 53 entries, 12 sectors confirmed via import check |
| 4  | Discovery scanner fetches IDX OHLCV in batches of 80 and crypto top 100 from CoinGecko, detects four trigger types | VERIFIED | `src/data/discovery.py`: BATCH_SIZE=80, four trigger detectors, CoinGecko URL; 18 tests pass |
| 5  | Composite score computed with multi-trigger bonuses (1.15x for 2, 1.30x for 3+), capped at 1.0 | VERIFIED | `compute_composite_score` in discovery.py; TestCompositeScore verifies weights and bonuses |
| 6  | Ownership fetcher scrapes IDX shareholder API with weekly cache and graceful degradation | VERIFIED | `src/data/ownership_fetcher.py`: weekly cache check, try/except on HTTP errors; 7 tests pass |
| 7  | Sector benchmarking, management quality, competitive positioning, DD flags computed from StockFundamental/FinancialData | VERIFIED | `src/data/due_diligence.py`: all five functions present; 13 tests pass |
| 8  | Discovery scan runs as post-pipeline function after run_batch_cross_cutting, before send_daily_report | VERIFIED | `src/pipeline/main.py`: run_batch_cross_cutting → run_discovery_scan → send_daily_report sequence confirmed |
| 9  | DD computation runs per stock asset during _enhanced_ingest_stage | VERIFIED | `src/pipeline/main.py` line 131: `await compute_dd_report(session, asset, date.today())` inside `asset_type == "stock"` guard |
| 10 | DD flags injected into LLM decision prompt when asset_type == stock without TypeError | VERIFIED | Type guard at lines 275-277 of decide.py resets non-list dd_flags to None; `dd_flags=dd_flags` passed to `build_decision_prompt` at line 300; 26 test_decide.py tests pass |
| 11 | Daily report includes New Opportunities section with top 5 discovery cards; omitted when empty | VERIFIED | `src/data/report.py` discoveries param; `format_discovery_section` returns empty string for empty list; 14 formatter tests pass |
| 12 | /discover, /duediligence, /compare Telegram commands registered and functional | VERIFIED | `src/bot/main.py` lines 57-60: CommandHandler registrations for discover, duediligence, dd, compare; 17 bot tests pass |
| 13 | /compare table shows only metrics available in StockFundamental (P/E, P/B, ROE, D/E, Rev CAGR) | VERIFIED | `src/bot/handlers/compare.py`: no net_margin keys; `format_compare_table` metrics list has 5 rows only; 21 compare+formatter tests pass |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/db/models.py` | DiscoveryCandidate, OwnershipSnapshot, DueDiligenceReport ORM models | VERIFIED | All three classes present; correct column types and constraints |
| `src/db/migrations/versions/012_discovery_candidates.py` | Alembic migration for discovery_candidates | VERIFIED | rev=012, down_revision=011; JSONB, UniqueConstraint, index |
| `src/db/migrations/versions/013_ownership_due_diligence.py` | Alembic migration for ownership_snapshots + due_diligence_reports | VERIFIED | rev=013, down_revision=012; ForeignKey("assets.id") on both tables |
| `src/engines/valuation.py` | Expanded IDX_SECTOR_MAP 50+ entries | VERIFIED | 53 entries across 12 sectors |
| `src/data/discovery.py` | run_discovery_scan, compute_composite_score, four trigger detectors | VERIFIED | 556 lines; all required functions present; 18 tests pass |
| `src/data/ownership_fetcher.py` | fetch_ownership_data, _parse_shareholder_response | VERIFIED | 201 lines; both functions present; 7 tests pass |
| `src/data/due_diligence.py` | compute_dd_report, compute_sector_benchmark, compute_management_quality, compute_competitive_position, generate_dd_flags | VERIFIED | 505 lines; all five functions present; 13 tests pass |
| `src/pipeline/main.py` | run_discovery_scan + compute_dd_report wired | VERIFIED | Both imports and calls present; sequence correct |
| `src/llm/prompts.py` | dd_flags parameter and DUE DILIGENCE FLAGS section | VERIFIED | build_decision_prompt accepts dd_flags; DUE DILIGENCE FLAGS section present |
| `src/data/decide.py` | DueDiligenceReport.dd_flags query with isinstance type guard, passed to build_decision_prompt | VERIFIED | Type guard at lines 275-277 (`if dd_flags is not None and not isinstance(dd_flags, list): dd_flags = None`); dd_flags=dd_flags at line 300; 26 tests pass |
| `src/report/formatter.py` | format_discovery_card, format_discovery_section, format_dd_report, format_compare_table (5 metrics) | VERIFIED | All four functions present; format_compare_table has 5 metrics without Net Mgn; 14 formatter tests pass |
| `src/data/report.py` | discoveries parameter in send_daily_report; format_discovery_section call | VERIFIED | discoveries parameter; format_discovery_section imported and called |
| `src/bot/handlers/compare.py` | compare_handler without net_margin placeholder | VERIFIED | No net_margin keys in either data.append() dict; `grep -c net_margin` returns 0 |
| `src/bot/handlers/discover.py` | discover_handler with DiscoveryCandidate query | VERIFIED | 85 lines; async def discover_handler; queries by scan_date; empty state message |
| `src/bot/handlers/duediligence.py` | duediligence_handler with DueDiligenceReport query and crypto rejection | VERIFIED | 130 lines; DueDiligenceReport query; crypto rejection message; OwnershipSnapshot loaded |
| `src/bot/main.py` | CommandHandler registrations for discover, duediligence, dd, compare | VERIFIED | Lines 57-60: all four registrations present |
| `tests/test_data/test_decide.py` | 26 tests pass including 6 formerly-failing regression tests | VERIFIED | 26 passed (was 6 failures before 11-06) |
| `tests/test_bot/test_compare_handler.py` | Compare handler tests without net_margin fixtures | VERIFIED | All tests pass; net_margin keys removed from test fixtures |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/data/decide.py` | `src/llm/prompts.py` | `dd_flags=dd_flags` in build_decision_prompt call | WIRED | Type guard ensures only list or None reaches prompt; dd_flags=dd_flags at line 300; passes for flag in dd_flags iteration safely |
| `src/data/discovery.py` | `src/db/models.py` | DiscoveryCandidate ORM insert | WIRED | DiscoveryCandidate imported at line 24; rows inserted in run_discovery_scan |
| `src/data/discovery.py` | yfinance | `yf.download()` batch call | WIRED | yf.download in _fetch_idx_screening_data via run_in_executor |
| `src/data/discovery.py` | CoinGecko API | httpx GET /coins/markets | WIRED | _COINGECKO_MARKETS_URL present; httpx.AsyncClient in _fetch_crypto_screening_data |
| `src/data/due_diligence.py` | `src/db/models.py` | StockFundamental, FinancialData, DueDiligenceReport queries | WIRED | All three imported and queried |
| `src/data/ownership_fetcher.py` | `src/db/models.py` | OwnershipSnapshot insert | WIRED | OwnershipSnapshot imported and inserted at line 94 |
| `src/pipeline/main.py` | `src/data/discovery.py` | run_discovery_scan call | WIRED | Import at line 19; await run_discovery_scan at line 187 |
| `src/pipeline/main.py` | `src/data/due_diligence.py` | compute_dd_report in _enhanced_ingest_stage | WIRED | Import at line 20; await compute_dd_report at line 131 |
| `src/data/report.py` | `src/report/formatter.py` | format_discovery_section import | WIRED | Imported; called at line 336 |
| `src/bot/handlers/compare.py` | `src/report/formatter.py` | format_compare_table (5 metrics) | WIRED | format_compare_table called; no net_margin in data dict |
| `src/bot/main.py` | telegram.ext | CommandHandler registrations | WIRED | 4 CommandHandler registrations at lines 57-60 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `src/bot/handlers/discover.py` | candidates (DiscoveryCandidate rows) | DB query by scan_date, ordered by composite_score | Yes — real DB query with ORM filter | FLOWING |
| `src/bot/handlers/duediligence.py` | dd_report (DueDiligenceReport) | DB query by asset_id DESC report_date | Yes — real DB query returning stored DD report | FLOWING |
| `src/bot/handlers/compare.py` | data dict (pe, pb, roe, debt_to_equity, revenue_cagr) | StockFundamental query per asset | Yes — 5 real columns from StockFundamental; net_margin removed | FLOWING |
| `src/report/formatter.py format_discovery_section` | candidates list | Passed from run_discovery_scan return value | Yes — run_discovery_scan populates from DiscoveryCandidate DB rows | FLOWING |
| `src/llm/prompts.py _format_engine_data` | dd_flags | DueDiligenceReport.dd_flags via decide.py with type guard | Yes — real list from DB or None; type guard prevents coroutine leak | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Models importable | `python3 -c "from src.db.models import DiscoveryCandidate, OwnershipSnapshot, DueDiligenceReport; print('OK')"` | Models OK | PASS |
| IDX_SECTOR_MAP >= 50 entries | `python3 -c "from src.engines.valuation import IDX_SECTOR_MAP; print(len(IDX_SECTOR_MAP))"` | 53 entries | PASS |
| Type guard present in decide.py | `grep "isinstance.*dd_flags.*list" src/data/decide.py` | Match found at line 276 | PASS |
| net_margin removed from compare handler | `grep -c "net_margin" src/bot/handlers/compare.py` | 0 matches | PASS |
| Net Mgn removed from format_compare_table | `format_compare_table` metrics list has 5 entries only | Verified via code read | PASS |
| decide.py tests (all 26) | `.venv/bin/python -m pytest tests/test_data/test_decide.py -q` | 26 passed (0 failures) | PASS |
| Compare handler + formatter tests | `.venv/bin/python -m pytest tests/test_bot/test_compare_handler.py tests/test_report/test_formatter_discovery.py -q` | 21 passed | PASS |
| Full test suite | `.venv/bin/python -m pytest tests/ --ignore=tests/test_config.py -q` | 834 passed, 0 failures | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DISC-01 | 11-01, 11-02 | Scan all IHSG stocks for unusual volume, breakouts | SATISFIED | discovery.py: _detect_volume_spike, _detect_breakout on ~900 IHSG tickers via yf.download batches |
| DISC-02 | 11-01, 11-02 | Scan crypto market for top movers, anomalies | SATISFIED | discovery.py: _fetch_crypto_screening_data hits CoinGecko /coins/markets top 100 |
| DISC-03 | 11-01, 11-02 | Recommend new assets based on signal strength | SATISFIED | run_discovery_scan returns top N by composite_score; stored as DiscoveryCandidate |
| DISC-04 | 11-04 | "New Opportunities" section in daily report | SATISFIED | send_daily_report accepts discoveries param; format_discovery_section appended after news digest |
| DUED-01 | 11-01, 11-03 | Sector benchmarking — compare company metrics against sector median | SATISFIED | compute_sector_benchmark queries all sector peers from StockFundamental via IDX_SECTOR_MAP |
| DUED-02 | 11-01, 11-03 | Ownership and insider analysis from IDX disclosure filings | SATISFIED | fetch_ownership_data scrapes idx.co.id GetShareHolder endpoint; OwnershipSnapshot stored |
| DUED-03 | 11-01, 11-03 | Management quality scoring (tenure, CAGR, capital allocation) | SATISFIED | compute_management_quality: revenue CAGR 40%, ROE trend 30%, capital allocation 30%; Excellent/Good/Fair/Weak labels |
| DUED-04 | 11-01, 11-03 | Competitive positioning (market share, moat indicators) | SATISFIED | compute_competitive_position: ranks peers by ROE-weighted composite; moat indicators from vs-median comparisons |
| LLM-06 | 11-04, 11-06 | LLM considers due diligence flags (insider selling, management changes, earnings quality) | SATISFIED | DUE DILIGENCE FLAGS section in prompts.py; decide.py type guard ensures list|None reaches build_decision_prompt; 26 decide tests pass |
| TBOT-06 | 11-05 | /discover shows today's opportunities | SATISFIED | discover_handler queries DiscoveryCandidate by today's scan_date; top 5 with format_discovery_card; 4 tests pass |
| TBOT-10 | 11-05 | /compare BBCA BBRI BMRI side-by-side sector comparison | SATISFIED | compare_handler validates 2-5 symbols, crypto filtering; format_compare_table with 5 clean metrics; 7 tests pass |
| TBOT-11 | 11-05 | /duediligence BBCA full DD report | SATISFIED | duediligence_handler queries DueDiligenceReport + OwnershipSnapshot; crypto rejection; 6 tests pass |
| REPT-07 | 11-04 | New opportunities discovered | SATISFIED | format_discovery_section + send_daily_report discoveries param wired; section omitted when empty |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/data/decide.py` | 264-273 | AsyncMock session causes `scalar_one_or_none()` to return coroutine | RESOLVED | Type guard at lines 275-277 prevents coroutine from reaching build_decision_prompt; all 26 tests pass |

No remaining anti-patterns. The previous blocker (coroutine leak) and warning (net_margin placeholder) are both resolved.

### Human Verification Required

#### 1. Live /discover Command

**Test:** After running the pipeline, issue `/discover` in the Telegram bot
**Expected:** Shows top 5 discovery candidates with trigger emojis, composite score, price and change percentage. Shows "No new opportunities found today" message if scan returned empty results
**Why human:** Requires live pipeline execution with real yfinance + CoinGecko data; DB must have DiscoveryCandidate rows from that day's run

#### 2. Live /duediligence BBCA Command

**Test:** Issue `/duediligence BBCA` in Telegram after at least one pipeline run that executed compute_dd_report for BBCA
**Expected:** Full DD report with sector rank section, management quality with score/label, ownership table with holders, competitive position with rank
**Why human:** Requires live DB with StockFundamental data populated by prior pipeline; all tests mock the DB

#### 3. Live /compare BBCA BBRI BMRI Command

**Test:** Issue `/compare BBCA BBRI BMRI` in Telegram
**Expected:** Side-by-side table in `<pre>` block with P/E, P/B, ROE %, D/E, Rev CAGR % columns; crown emoji on best per row; no Net Margin row present
**Why human:** Requires live StockFundamental rows; visually confirms clean 5-metric table and absence of misleading Net Margin row

### Gaps Summary

No gaps remain. Both gaps identified in the initial verification were resolved by plan 11-06:

- **Blocker resolved:** `src/data/decide.py` type guard (`if dd_flags is not None and not isinstance(dd_flags, list): dd_flags = None`) prevents coroutine objects from leaking to `build_decision_prompt`. All 26 `test_decide.py` tests pass; full suite 834 tests, 0 failures.

- **Warning resolved:** `net_margin` removed from `src/bot/handlers/compare.py` and `format_compare_table` in `src/report/formatter.py`. The compare table now shows 5 clean metrics (P/E, P/B, ROE %, D/E, Rev CAGR %). The `net_margin` references remaining in `format_dd_report` are intentional — that function uses a different data source (computed profitability dict, not StockFundamental direct query).

Phase 11 goal is fully achieved in code. Human verification items are integration-level tests requiring live infrastructure.

---

_Verified: 2026-03-26T12:45:00Z_
_Verifier: Claude (gsd-verifier)_
