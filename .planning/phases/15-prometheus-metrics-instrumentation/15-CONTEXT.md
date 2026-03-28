# Phase 15: Prometheus Metrics Instrumentation - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire 5 orphaned Prometheus metrics into application code so Grafana dashboards (System Overview, Pipeline Health) show real data. The metrics are already defined in `src/monitoring/metrics.py` — this phase adds the `.inc()`, `.observe()`, and `.set()` calls at the right places in the codebase. No new metric definitions, no dashboard changes, no new Grafana panels.

Gap closure from v1.0 milestone audit: `FETCH_SUCCESS`, `FETCH_FAILURE`, `ENGINE_DURATION`, `DATA_FRESHNESS_HOURS`, `BOT_REQUEST_COUNT`.

</domain>

<decisions>
## Implementation Decisions

### Fetch metric placement
- **D-01:** FETCH_SUCCESS and FETCH_FAILURE counters emitted centrally in the ingest stage orchestration code (`src/data/ingest.py`), not inside individual fetcher functions
- **D-02:** Labels: `source` = yfinance|ccxt|coingecko, `asset_type` = stock|crypto — matching the label schema already defined in `src/monitoring/metrics.py`

### Engine duration instrumentation
- **D-03:** ENGINE_DURATION histogram observed in the analyze_stage loop (`src/pipeline/stages/analyze.py`), wrapping each engine's `analyze()` call with a timer — single instrumentation point for all 15 engines
- **D-04:** `engine_name` label derived from the engine class name or registry key

### Data freshness calculation
- **D-05:** DATA_FRESHNESS_HOURS gauge set by querying MAX(timestamp) from price_history after ingest completes, computing hours elapsed from that timestamp
- **D-06:** Per asset_type (stock|crypto) — reflects actual data age in the database, survives pipeline restarts

### Bot request counting
- **D-07:** BOT_REQUEST_COUNT tracked via FastAPI/Starlette middleware that fires on every HTTP request
- **D-08:** Labels: method, endpoint, status — catches all routes including /health and /metrics automatically

### Claude's Discretion
- Exact middleware implementation pattern (Starlette BaseHTTPMiddleware vs raw ASGI)
- Timer implementation for ENGINE_DURATION (time.perf_counter vs prometheus_client helpers)
- Whether DATA_FRESHNESS_HOURS query runs in the same DB session as ingest or opens a new one
- Test structure and mocking approach

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Metric definitions
- `src/monitoring/metrics.py` — All 10 Prometheus metric objects with label schemas; the 5 orphaned ones are FETCH_SUCCESS, FETCH_FAILURE, ENGINE_DURATION, DATA_FRESHNESS_HOURS, BOT_REQUEST_COUNT

### Instrumentation targets
- `src/data/ingest.py` — Ingest stage orchestration; FETCH_SUCCESS/FAILURE to be emitted here
- `src/pipeline/stages/analyze.py` — analyze_stage loop over engines; ENGINE_DURATION to be observed here
- `src/bot/main.py` — FastAPI app; BOT_REQUEST_COUNT middleware to be added here

### Already-wired examples (patterns to follow)
- `src/pipeline/runner.py` — PIPELINE_DURATION and PIPELINE_STAGE_STATUS instrumentation (lines 19+)
- `src/llm/client.py` — LLM_CALL_COUNT and LLM_CALL_DURATION instrumentation (line 14+)
- `src/pipeline/main.py` — PIPELINE_LAST_SUCCESS and push_to_gateway usage

### Grafana dashboards (verification)
- `monitoring/grafana/dashboards/system-overview.json` — System Overview dashboard panels
- `monitoring/grafana/dashboards/pipeline-health.json` — Pipeline Health dashboard panels

### Gap source
- `.planning/v1.0-MILESTONE-AUDIT.md` — v1.0 audit that identified the 5 orphaned metrics

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/monitoring/metrics.py`: All metric objects already defined with correct label schemas — just need to import and call
- `src/monitoring/pushgateway.py`: push_to_gateway wrapper already used by pipeline main — pipeline metrics (including new ones) will be pushed automatically
- `src/pipeline/runner.py`: Existing PIPELINE_DURATION/STAGE_STATUS instrumentation pattern to follow

### Established Patterns
- Pipeline metrics use Pushgateway push (batch job model) — any new pipeline-side metrics follow this automatically via existing push_pipeline_metrics()
- Bot metrics scraped from /metrics endpoint on port 8000 — middleware metrics will be auto-exposed
- prometheus_client default registry shared across all modules — no registry wiring needed
- Two-process boundary: bot and pipeline never share imports, but both can import from src/monitoring/

### Integration Points
- `src/data/ingest.py` — Add FETCH_SUCCESS/FAILURE imports and .inc() calls around fetch operations
- `src/pipeline/stages/analyze.py` — Add ENGINE_DURATION import and timer around engine.analyze() calls
- `src/data/ingest.py` (or new post-ingest hook) — Add DATA_FRESHNESS_HOURS query and .set()
- `src/bot/main.py` — Add Starlette middleware for BOT_REQUEST_COUNT

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-prometheus-metrics-instrumentation*
*Context gathered: 2026-03-29*
