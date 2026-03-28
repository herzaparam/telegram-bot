# Phase 15: Prometheus Metrics Instrumentation - Research

**Researched:** 2026-03-29
**Domain:** Prometheus metrics instrumentation in async Python (prometheus_client, FastAPI/Starlette middleware)
**Confidence:** HIGH

## Summary

Phase 15 wires 5 orphaned Prometheus metrics (FETCH_SUCCESS, FETCH_FAILURE, ENGINE_DURATION, DATA_FRESHNESS_HOURS, BOT_REQUEST_COUNT) into application code. All metric objects are already defined in `src/monitoring/metrics.py` with correct label schemas. The Grafana dashboards (pipeline-health.json, system-overview.json) already have panels querying these metrics -- the panels are simply empty because the `.inc()`, `.observe()`, and `.set()` calls are never made.

The existing codebase has two strong instrumentation patterns to follow: `src/pipeline/runner.py` (PIPELINE_DURATION/STAGE_STATUS emitted at end of `run_stage`) and `src/llm/client.py` (LLM_CALL_COUNT/DURATION using `time.monotonic()` for timing). Both use simple import-and-call patterns with no custom abstractions.

**Primary recommendation:** Add metric emission calls at the 4 instrumentation points identified in CONTEXT.md, following the existing `time.monotonic()` + `.observe()` / `.inc()` / `.set()` patterns already established in the codebase. No new libraries, no new abstractions needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** FETCH_SUCCESS and FETCH_FAILURE counters emitted centrally in the ingest stage orchestration code (`src/data/ingest.py`), not inside individual fetcher functions
- **D-02:** Labels: `source` = yfinance|ccxt|coingecko, `asset_type` = stock|crypto -- matching the label schema already defined in `src/monitoring/metrics.py`
- **D-03:** ENGINE_DURATION histogram observed in the analyze_stage loop (`src/data/analyze.py`), wrapping each engine's `analyze()` call with a timer -- single instrumentation point for all 15 engines
- **D-04:** `engine_name` label derived from the engine class name or registry key
- **D-05:** DATA_FRESHNESS_HOURS gauge set by querying MAX(timestamp) from price_history after ingest completes, computing hours elapsed from that timestamp
- **D-06:** Per asset_type (stock|crypto) -- reflects actual data age in the database, survives pipeline restarts
- **D-07:** BOT_REQUEST_COUNT tracked via FastAPI/Starlette middleware that fires on every HTTP request
- **D-08:** Labels: method, endpoint, status -- catches all routes including /health and /metrics automatically

### Claude's Discretion
- Exact middleware implementation pattern (Starlette BaseHTTPMiddleware vs raw ASGI)
- Timer implementation for ENGINE_DURATION (time.perf_counter vs prometheus_client helpers)
- Whether DATA_FRESHNESS_HOURS query runs in the same DB session as ingest or opens a new one
- Test structure and mocking approach

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MON-09 | Grafana System Overview dashboard shows real data for all metric panels | BOT_REQUEST_COUNT middleware (system-overview.json has `up{job="bot"}` panel; bot_http_requests_total is scraped from /metrics endpoint alongside other bot metrics) |
| MON-10 | Grafana Pipeline Health dashboard shows real data for all metric panels | FETCH_SUCCESS/FAILURE, ENGINE_DURATION, DATA_FRESHNESS_HOURS -- all 4 pipeline-health panels referencing these metrics will populate once .inc()/.observe()/.set() calls are added |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| prometheus_client | already installed | Counter.inc(), Histogram.observe(), Gauge.set() | Already used throughout codebase; default registry shared by bot /metrics and pipeline pushgateway |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| starlette | already installed (via FastAPI) | BaseHTTPMiddleware for BOT_REQUEST_COUNT | D-07 middleware pattern |
| time (stdlib) | N/A | time.monotonic() for ENGINE_DURATION timer | D-03 timing pattern |
| asyncpg | already installed | Raw SQL query for MAX(timestamp) in DATA_FRESHNESS_HOURS | D-05 freshness query |

No new packages needed. All dependencies are already installed.

## Architecture Patterns

### Pattern 1: Counter Instrumentation (FETCH_SUCCESS/FAILURE)
**What:** Import metric, call `.labels(...).inc()` at success/failure branch points in `ingest_stage()`
**When to use:** After each fetch completes or fails
**Example:**
```python
# Source: existing pattern in src/llm/client.py lines 67-68
from src.monitoring.metrics import FETCH_SUCCESS, FETCH_FAILURE

# On success:
FETCH_SUCCESS.labels(source=fetcher.source_name, asset_type=asset.asset_type).inc()

# On failure (in except block):
FETCH_FAILURE.labels(source=fetcher.source_name, asset_type=asset.asset_type).inc()
```

**Placement in ingest.py:** The `ingest_stage()` function (line 247) has a clear try/except around `fetcher.fetch()` at lines 312-323. FETCH_SUCCESS goes after line 316 (`_update_backoff_success`), FETCH_FAILURE goes in the except block before `handle_source_failure` at line 322.

**Label values:**
- `source`: `fetcher.source_name` -- IDXStockFetcher returns "yfinance", CryptoFetcher returns "ccxt" (or "coingecko" on fallback)
- `asset_type`: `asset.asset_type` -- "stock" or "crypto"

**Note on CoinGecko fallback:** The CryptoFetcher source_name is "ccxt". If CoinGecko fallback is used, the source label should reflect "coingecko". Check CryptoFetcher implementation to confirm if source_name changes on fallback or stays "ccxt".

### Pattern 2: Histogram Timer (ENGINE_DURATION)
**What:** Wrap `engine.analyze()` call with `time.monotonic()` start/end, call `.labels(engine_name=...).observe(duration)`
**When to use:** Around each engine's analyze() call in the engine loop
**Example:**
```python
# Source: existing pattern in src/llm/client.py lines 62-68
import time
from src.monitoring.metrics import ENGINE_DURATION

for engine in engines:
    start = time.monotonic()
    try:
        signal = engine.analyze(asset.id, asset.symbol, df)
        # ... existing logic ...
    except Exception as exc:
        # ... existing error handling ...
    finally:
        duration = time.monotonic() - start
        ENGINE_DURATION.labels(engine_name=engine.category).observe(duration)
```

**engine_name label:** Use `engine.category` (string attribute on BaseEngine). Every engine has a `category` attribute set in its `__init__`. This matches D-04 ("derived from the engine class name or registry key").

**Recommendation (Claude's discretion):** Use `time.monotonic()` + manual `.observe()` rather than `Histogram.time()` context manager. Reasons: (1) matches existing pattern in llm/client.py, (2) avoids nesting with try/except, (3) observation should happen in `finally` block to record duration even on failure.

### Pattern 3: Gauge Setting (DATA_FRESHNESS_HOURS)
**What:** After ingest completes, query MAX(time) from price_history for the asset, compute hours since that timestamp, call `.labels(asset_type=...).set(hours)`
**When to use:** After the raw asyncpg connection operations in ingest_stage, before conn.close()
**Example:**
```python
from datetime import UTC, datetime
from src.monitoring.metrics import DATA_FRESHNESS_HOURS

# After upsert, before conn.close():
latest_after = await get_latest_date(conn, asset.id)
if latest_after is not None:
    hours = (datetime.now(UTC) - latest_after).total_seconds() / 3600
    DATA_FRESHNESS_HOURS.labels(asset_type=asset.asset_type).set(hours)
```

**Placement:** The `ingest_stage()` already queries `latest_after = await get_latest_date(conn, asset.id)` at line 343. The freshness metric should be set right after this, using the same connection and the same `latest_after` result. No new DB query needed.

**Recommendation (Claude's discretion):** Use the same asyncpg connection already open in ingest_stage (not a new session). The `latest_after` value is already computed at line 343 -- just add the metric `.set()` call right after. This avoids an extra DB round-trip.

### Pattern 4: HTTP Request Middleware (BOT_REQUEST_COUNT)
**What:** Starlette middleware that increments BOT_REQUEST_COUNT on every request
**When to use:** Added to FastAPI app in `src/bot/main.py`

**Recommendation (Claude's discretion):** Use Starlette `BaseHTTPMiddleware` rather than raw ASGI. Reasons: (1) simpler to implement, (2) handles exception cases automatically, (3) sufficient for counter instrumentation. Raw ASGI would be needed for streaming responses, which this bot does not use.

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from src.monitoring.metrics import BOT_REQUEST_COUNT

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: StarletteRequest, call_next
    ) -> StarletteResponse:
        response = await call_next(request)
        BOT_REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=str(response.status_code),
        ).inc()
        return response

# In app setup (before mount):
app.add_middleware(MetricsMiddleware)
```

**Ordering concern:** Middleware must be added BEFORE `app.mount("/metrics", metrics_app)` to ensure /metrics requests are also counted. In FastAPI/Starlette, middleware wraps the entire app including mounted sub-applications.

**Label cardinality:** The `endpoint` label uses `request.url.path` which gives exact paths like `/health`, `/telegram/webhook`, `/metrics`. This is a bounded set (~5 routes) so label cardinality is not a concern.

### Anti-Patterns to Avoid
- **Decorating individual fetcher methods:** D-01 explicitly states central emission in ingest.py, not per-fetcher. This avoids missing new fetchers that might be added later.
- **Creating wrapper/helper abstractions:** The codebase has zero abstraction layers for metrics -- direct `metric.labels(...).inc()` calls. Don't add a `track_metric()` helper.
- **Using prometheus_client multiprocess mode:** Not needed. Bot is single-process (uvicorn). Pipeline pushes to Pushgateway. Default in-process registry works.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP request counting | Custom logging + counting | Starlette BaseHTTPMiddleware + Counter | Middleware catches all routes including error responses |
| Timer for histograms | Custom decorator/context manager | time.monotonic() + .observe() | Matches existing pattern, no abstraction needed |
| Data freshness calculation | Polling loop or separate cron | Inline in ingest_stage after existing get_latest_date call | Data is already available, just needs math + .set() |

## Common Pitfalls

### Pitfall 1: Forgetting to handle the CoinGecko fallback source label
**What goes wrong:** FETCH_SUCCESS always shows source=ccxt for crypto, even when CoinGecko fallback was used
**Why it happens:** CryptoFetcher.source_name is "ccxt" but actual data may come from CoinGecko
**How to avoid:** Check CryptoFetcher implementation -- if source_name stays "ccxt" on fallback, the label is still correct (it represents the fetcher, not the API). If CoinGecko rows have source="coingecko" in OHLCVRow, use that instead. The CONTEXT.md D-02 lists coingecko as a valid source value.
**Warning signs:** All crypto fetches show source=ccxt even when CoinGecko fallback fires

### Pitfall 2: Middleware counting /metrics requests creates feedback loop
**What goes wrong:** Every Prometheus scrape increments BOT_REQUEST_COUNT, which inflates the count
**Why it happens:** /metrics endpoint is hit every 15-30s by Prometheus scraper
**How to avoid:** This is expected behavior per D-08 ("catches all routes including /health and /metrics automatically"). The dashboard queries use `rate()` or `increase()` which normalize for scrape frequency. No filtering needed.
**Warning signs:** N/A -- this is by design

### Pitfall 3: DATA_FRESHNESS_HOURS not set for assets with no price data
**What goes wrong:** New assets or assets that fail all fetches never set the freshness gauge
**Why it happens:** `get_latest_date()` returns None when no rows exist
**How to avoid:** Only call `.set()` when `latest_after is not None`. The gauge stays at its last value (or 0 if never set). This is correct -- no data means freshness is unknown, not zero.
**Warning signs:** Freshness gauge shows 0 for assets that should show stale

### Pitfall 4: ENGINE_DURATION not observed on early return
**What goes wrong:** If analyze_stage returns early (no price data, line 513), no engine durations are recorded
**Why it happens:** The early return happens before the engine loop
**How to avoid:** This is correct behavior -- no engines ran, so no durations to record. No mitigation needed.

### Pitfall 5: Middleware added after mount doesn't wrap mounted apps
**What goes wrong:** Requests to /metrics are not counted by BOT_REQUEST_COUNT
**Why it happens:** In FastAPI, `add_middleware()` must be called before the app starts (or at least the order matters for middleware stack building)
**How to avoid:** Add `app.add_middleware(MetricsMiddleware)` after the `app = FastAPI(...)` line but before `app.mount("/metrics", ...)`. In practice, FastAPI rebuilds the middleware stack on startup, so ordering of add_middleware vs mount in source code doesn't matter for runtime behavior. But placing it right after app creation is clearest.

## Code Examples

### Ingest Stage Instrumentation (FETCH_SUCCESS/FAILURE + DATA_FRESHNESS_HOURS)

Current code in `src/data/ingest.py` lines 311-323:
```python
# Current:
try:
    rows = await fetcher.fetch(...)
    await _update_backoff_success(session, fetcher.source_name)
except Exception as exc:
    await _update_backoff_failure(session, fetcher.source_name)
    _alert_collector.add_fetch_failure(asset.symbol, str(exc))
    handle_source_failure("price_ohlcv", exc)
    return
```

After instrumentation:
```python
from src.monitoring.metrics import DATA_FRESHNESS_HOURS, FETCH_FAILURE, FETCH_SUCCESS

# In try block after _update_backoff_success:
FETCH_SUCCESS.labels(source=fetcher.source_name, asset_type=asset.asset_type).inc()

# In except block before handle_source_failure:
FETCH_FAILURE.labels(source=fetcher.source_name, asset_type=asset.asset_type).inc()

# After get_latest_date (line 343), before staleness check:
if latest_after is not None:
    freshness_hours = (datetime.now(UTC) - latest_after).total_seconds() / 3600
    DATA_FRESHNESS_HOURS.labels(asset_type=asset.asset_type).set(freshness_hours)
```

### Analyze Stage Instrumentation (ENGINE_DURATION)

Current code in `src/data/analyze.py` lines 570-582:
```python
for engine in engines:
    try:
        signal = engine.analyze(asset.id, asset.symbol, df)
        signals.append(signal)
        log.info("engine_completed", ...)
    except Exception as exc:
        log.warning("engine_failed", ...)
        signals.append(_failed_signal(engine.category, str(exc)))
```

After instrumentation:
```python
import time
from src.monitoring.metrics import ENGINE_DURATION

for engine in engines:
    start = time.monotonic()
    try:
        signal = engine.analyze(asset.id, asset.symbol, df)
        signals.append(signal)
        log.info("engine_completed", ...)
    except Exception as exc:
        log.warning("engine_failed", ...)
        signals.append(_failed_signal(engine.category, str(exc)))
    finally:
        duration = time.monotonic() - start
        ENGINE_DURATION.labels(engine_name=engine.category).observe(duration)
```

### Bot Middleware (BOT_REQUEST_COUNT)

New middleware class in `src/bot/main.py`:
```python
from starlette.middleware.base import BaseHTTPMiddleware
from src.monitoring.metrics import BOT_REQUEST_COUNT

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        BOT_REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=str(response.status_code),
        ).inc()
        return response

# After app = FastAPI(...):
app.add_middleware(MetricsMiddleware)
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio (asyncio_mode=auto) |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_monitoring/ tests/test_data/test_ingest.py tests/test_data/test_analyze.py tests/test_bot/test_metrics_endpoint.py -x -q` |
| Full suite command | `pytest` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MON-10 | FETCH_SUCCESS/FAILURE counters increment on fetch operations | unit | `pytest tests/test_data/test_ingest.py -x -q` | Exists (needs new test cases) |
| MON-10 | ENGINE_DURATION histogram records per-engine analyze() timing | unit | `pytest tests/test_data/test_analyze.py -x -q` | Exists (needs new test cases) |
| MON-10 | DATA_FRESHNESS_HOURS gauge set after ingest | unit | `pytest tests/test_data/test_ingest.py -x -q` | Exists (needs new test cases) |
| MON-09 | BOT_REQUEST_COUNT increments on HTTP requests | unit | `pytest tests/test_bot/test_metrics_endpoint.py -x -q` | Exists (needs new test cases) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_monitoring/ tests/test_data/test_ingest.py tests/test_data/test_analyze.py tests/test_bot/ -x -q`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. Test files for ingest, analyze, and bot already exist. New test cases will be added to existing files.

## Open Questions

1. **CoinGecko fallback source label**
   - What we know: CryptoFetcher has source_name="ccxt". D-02 lists "coingecko" as a valid source label.
   - What's unclear: Whether CryptoFetcher changes source_name when using CoinGecko fallback, or if OHLCVRow carries source info
   - Recommendation: Check CryptoFetcher implementation during implementation. If source_name stays "ccxt" even on CoinGecko fallback, use "ccxt" consistently (the fetcher is the unit, not the API). If the implementer finds CoinGecko fallback needs separate tracking, emit a separate FETCH_SUCCESS with source="coingecko".

2. **BOT_REQUEST_COUNT in system-overview dashboard**
   - What we know: system-overview.json does NOT have a panel for bot_http_requests_total. It only has `up{job="bot"}`.
   - What's unclear: Whether MON-09 ("System Overview dashboard shows real data for all metric panels") requires adding a new panel for bot_http_requests
   - Recommendation: MON-09 is satisfied if ALL existing panels show data. The system-overview panels (CPU, memory, disk, bot status, network, uptime) all use node_exporter or `up` metrics, not bot_http_requests. BOT_REQUEST_COUNT is emitted for scraping by Prometheus and could be queried ad-hoc. No dashboard change needed per CONTEXT.md scope ("No new metric definitions, no dashboard changes, no new Grafana panels").

## Sources

### Primary (HIGH confidence)
- `src/monitoring/metrics.py` -- all 10 metric definitions, label schemas verified
- `src/data/ingest.py` -- ingest_stage code, fetch try/except block, get_latest_date call
- `src/data/analyze.py` -- analyze_stage engine loop, engine.category attribute
- `src/bot/main.py` -- FastAPI app setup, existing /metrics mount
- `src/pipeline/runner.py` -- existing PIPELINE_DURATION/STAGE_STATUS instrumentation pattern
- `src/llm/client.py` -- existing LLM_CALL_COUNT/DURATION timing pattern
- `monitoring/grafana/dashboards/pipeline-health.json` -- panels querying fetch_success_total, fetch_failure_total, engine_analysis_duration_seconds, data_freshness_hours
- `monitoring/grafana/dashboards/system-overview.json` -- panels querying node_exporter and up{job="bot"}

### Secondary (MEDIUM confidence)
- prometheus_client Python library -- `Histogram.time()` context manager confirmed available but not recommended (existing codebase uses manual timing)
- Starlette BaseHTTPMiddleware -- standard pattern for request counting in FastAPI apps

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and used in codebase
- Architecture: HIGH -- all 4 instrumentation points identified with exact line numbers; existing patterns provide clear templates
- Pitfalls: HIGH -- limited scope means few edge cases; main risks documented

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable -- no library updates expected to affect this)
