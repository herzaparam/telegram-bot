# Phase 13: Server and App Monitoring with Prometheus, etc - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Add observability infrastructure to the trading signal system: Prometheus metrics collection from both server and application layers, Grafana dashboards for visualization, and alerting via Telegram for critical conditions. Covers the bot process, pipeline batch job, TimescaleDB, and host system.

</domain>

<decisions>
## Implementation Decisions

### Metrics Scope
- **D-01:** Full-depth instrumentation — server metrics (CPU, RAM, disk via node_exporter), application metrics (pipeline run duration, per-engine scores/latency, LLM call count/cost/latency, fetch success rates), and database metrics (pg connections, query latency, hypertable size)
- **D-02:** Pipeline metrics exposed via Prometheus Pushgateway — pipeline is a batch job (daily cron, exits after), so it pushes metrics to Pushgateway after each run. Bot exposes its own /metrics endpoint on port 8000.

### Stack Choice
- **D-03:** Prometheus + Grafana stack, deployed as services in docker-compose.prod.yml alongside existing db, bot, and pipeline services
- **D-04:** `prometheus-client` (official Python library) for instrumenting both bot and pipeline code. Manual /metrics endpoint integration on FastAPI bot; Pushgateway client for pipeline.
- **D-05:** Grafana dashboards provisioned as code (JSON files in git, auto-loaded on container startup). No persistent volume for Grafana — dashboards are version-controlled.
- **D-06:** Docker services added: prometheus, grafana, node_exporter, pushgateway. Config files stored in a `monitoring/` directory at project root.

### Alerting Rules
- **D-07:** Grafana built-in alerting (not Alertmanager) — simpler setup, sufficient for this scale. Native Telegram contact point.
- **D-08:** Alerts delivered to a separate Telegram chat/group (not the trading signals chat). Requires a second `TELEGRAM_MONITORING_CHAT_ID` env var.
- **D-09:** Four critical alert conditions:
  1. Pipeline failed to complete (daily run didn't finish or exited with errors)
  2. High resource usage (CPU > 90% for 5min, RAM > 85%, disk > 80%)
  3. Bot/service down (health check fails for > 2 minutes)
  4. Data staleness (no new price data ingested for > 24 hours)

### Dashboard Design
- **D-10:** Two Grafana dashboard pages: (1) System Overview — CPU, RAM, disk, container status, DB connections. (2) Pipeline Health — run duration, engine success rates, LLM latency/cost, data freshness, fetch errors.
- **D-11:** Grafana accessible via VPS IP:3000 with built-in auth (admin user + password from env var). No reverse proxy required for this phase.

### Claude's Discretion
- Prometheus scrape intervals and retention period
- Specific panel layout, time ranges, and refresh rates within dashboards
- node_exporter collector configuration
- Pushgateway job naming conventions
- Grafana dashboard color scheme and thresholds

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing infrastructure
- `docker-compose.prod.yml` -- Current production Docker Compose with db, bot, pipeline services and resource limits
- `docker-compose.yml` -- Dev Docker Compose (db only)
- `Dockerfile` -- Application container build

### Application entry points
- `src/bot/main.py` -- FastAPI bot app with existing /health endpoint (line 87). /metrics endpoint to be added here.
- `src/pipeline/main.py` -- Pipeline CLI entry point. Pushgateway integration hooks here.
- `src/logging.py` -- structlog JSON logging setup. Metrics complement this.

### Configuration
- `src/config.py` -- pydantic-settings Settings class. New monitoring env vars (TELEGRAM_MONITORING_CHAT_ID, GRAFANA_ADMIN_PASSWORD) to be added here.

### Pipeline orchestration
- `src/pipeline/runner.py` -- PipelineRunner with per-stage checkpointing. Instrument stage durations and success/failure counts here.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/bot/main.py` FastAPI app: Already has /health endpoint. /metrics can be added as another route using prometheus_client.generate_latest()
- `src/logging.py` structlog: JSON structured logging already in place. Metrics add quantitative observability alongside qualitative logs.
- `src/config.py` Settings: pydantic-settings pattern for env vars. Add GRAFANA_ADMIN_PASSWORD, TELEGRAM_MONITORING_CHAT_ID, PROMETHEUS_PUSHGATEWAY_URL.
- `docker-compose.prod.yml`: Existing resource limits and health check patterns to follow for new services.

### Established Patterns
- Two-process model (bot + pipeline) — instrumentation must respect this boundary. Bot has /metrics, pipeline uses Pushgateway.
- Per-asset, per-stage checkpointing in PipelineRunner — natural points to emit Histogram/Counter metrics for each stage.
- Data source tier system (CRITICAL/IMPORTANT/SUPPLEMENTARY) — tier failures can be labeled in metrics.
- AlertCollector in `src/data/alerts.py` — existing alert pattern for data issues; monitoring alerts are a separate concern (infrastructure-level via Grafana, not application-level).

### Integration Points
- `docker-compose.prod.yml` — Add prometheus, grafana, node_exporter, pushgateway services
- `src/bot/main.py` — Add /metrics endpoint
- `src/pipeline/runner.py` — Instrument run_pipeline() and run_stage() with Prometheus counters/histograms, push to Pushgateway on completion
- `src/llm/client.py` — Instrument llm_completion() with latency histogram and call counter
- `src/data/ingest.py` — Instrument fetch success/failure counters per data source
- `src/config.py` — Add monitoring-related settings

</code_context>

<specifics>
## Specific Ideas

- Monitoring alerts go to a separate Telegram chat/group to keep trading signal delivery clean
- Dashboards are provisioned as code (JSON in git) — no manual dashboard creation that could be lost

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-server-and-app-monitoring-with-prometheus-etc*
*Context gathered: 2026-03-28*
