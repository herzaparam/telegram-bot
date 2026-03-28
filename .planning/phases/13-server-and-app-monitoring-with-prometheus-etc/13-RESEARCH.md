# Phase 13: Server and App Monitoring with Prometheus, etc - Research

**Researched:** 2026-03-28
**Domain:** Observability infrastructure (Prometheus, Grafana, node_exporter, Pushgateway)
**Confidence:** HIGH

## Summary

This phase adds a complete observability stack to the trade-agent system: Prometheus for metrics collection, Grafana for visualization and alerting, node_exporter for host metrics, and Pushgateway for the batch pipeline job. The application is a two-process Python system (FastAPI bot on port 8000, batch pipeline via cron) running on Docker Compose with TimescaleDB.

The core technical challenge is instrumenting two fundamentally different process types: (1) the bot is a long-running FastAPI service that can expose a `/metrics` endpoint directly, and (2) the pipeline is a batch job that runs daily and exits, requiring Pushgateway to persist metrics between scrapes. Both use `prometheus-client` (official Python library, v0.24.1) but with different export mechanisms.

**Primary recommendation:** Use `prometheus-client` 0.24.1 with `make_asgi_app()` mounted on FastAPI for the bot and `push_to_gateway()` for the pipeline. Grafana dashboards and alerting (including Telegram contact point) are fully provisionable as YAML/JSON files in git -- no manual UI configuration needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Full-depth instrumentation -- server metrics (CPU, RAM, disk via node_exporter), application metrics (pipeline run duration, per-engine scores/latency, LLM call count/cost/latency, fetch success rates), and database metrics (pg connections, query latency, hypertable size)
- **D-02:** Pipeline metrics exposed via Prometheus Pushgateway -- pipeline is a batch job (daily cron, exits after), so it pushes metrics to Pushgateway after each run. Bot exposes its own /metrics endpoint on port 8000.
- **D-03:** Prometheus + Grafana stack, deployed as services in docker-compose.prod.yml alongside existing db, bot, and pipeline services
- **D-04:** `prometheus-client` (official Python library) for instrumenting both bot and pipeline code. Manual /metrics endpoint integration on FastAPI bot; Pushgateway client for pipeline.
- **D-05:** Grafana dashboards provisioned as code (JSON files in git, auto-loaded on container startup). No persistent volume for Grafana -- dashboards are version-controlled.
- **D-06:** Docker services added: prometheus, grafana, node_exporter, pushgateway. Config files stored in a `monitoring/` directory at project root.
- **D-07:** Grafana built-in alerting (not Alertmanager) -- simpler setup, sufficient for this scale. Native Telegram contact point.
- **D-08:** Alerts delivered to a separate Telegram chat/group (not the trading signals chat). Requires a second `TELEGRAM_MONITORING_CHAT_ID` env var.
- **D-09:** Four critical alert conditions: (1) Pipeline failed to complete, (2) High resource usage, (3) Bot/service down, (4) Data staleness
- **D-10:** Two Grafana dashboard pages: (1) System Overview, (2) Pipeline Health
- **D-11:** Grafana accessible via VPS IP:3000 with built-in auth (admin user + password from env var). No reverse proxy required.

### Claude's Discretion
- Prometheus scrape intervals and retention period
- Specific panel layout, time ranges, and refresh rates within dashboards
- node_exporter collector configuration
- Pushgateway job naming conventions
- Grafana dashboard color scheme and thresholds

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core

| Library / Image | Version | Purpose | Why Standard |
|-----------------|---------|---------|--------------|
| prometheus-client (Python) | 0.24.1 | Instrument bot + pipeline code with counters, histograms, gauges | Official Prometheus Python client; only maintained option |
| prom/prometheus | v2.53.5 | Metrics collection and storage | Industry standard; scrapes /metrics endpoints and Pushgateway |
| grafana/grafana | 12.4.x | Dashboard visualization and alerting | De facto standard for Prometheus visualization; built-in Telegram alerting |
| prom/node-exporter | v1.9.1 | Host system metrics (CPU, RAM, disk, network) | Official Prometheus host metrics exporter |
| prom/pushgateway | v1.11.2 | Accept pushed metrics from batch pipeline job | Official Prometheus component for ephemeral/batch jobs |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| Grafana file provisioning | Auto-load datasources, dashboards, alert rules from YAML/JSON | On container startup -- no manual UI config |
| Grafana unified alerting | Built-in alert evaluation + notification routing | For all 4 alert conditions (D-09) via Telegram contact point |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pushgateway | Textfile collector | Requires shared volume between pipeline and Prometheus; Pushgateway is simpler for Docker |
| Grafana alerting | Alertmanager | More powerful routing/silencing, but adds another service and config complexity for 4 simple alerts |
| prometheus-client manual | prometheus-fastapi-instrumentator | Auto-instruments all routes; overkill for a bot with only /health and /metrics |

**Installation (Python dependency):**
```bash
uv add prometheus-client
```

## Architecture Patterns

### Recommended Project Structure
```
monitoring/
  prometheus/
    prometheus.yml           # Scrape config
  grafana/
    provisioning/
      datasources/
        prometheus.yml       # Prometheus datasource config
      dashboards/
        dashboards.yml       # Dashboard provider config
      alerting/
        contactpoints.yml    # Telegram contact point
        rules.yml            # Alert rules
        policies.yml         # Notification policies
    dashboards/
      system-overview.json   # Dashboard 1: System Overview
      pipeline-health.json   # Dashboard 2: Pipeline Health
src/
  monitoring/
    __init__.py
    metrics.py               # All Prometheus metric definitions (single registry)
    pushgateway.py           # push_to_gateway helper for pipeline
```

### Pattern 1: Centralized Metric Registry
**What:** Define ALL Prometheus metrics in a single `src/monitoring/metrics.py` module. Both bot and pipeline import from here.
**When to use:** Always -- prevents metric name collisions and makes the full metric catalog discoverable.
**Example:**
```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

# Use default registry for bot (scraped via /metrics)
# Pipeline creates a separate registry for Pushgateway

# --- Bot metrics (default registry, scraped by Prometheus) ---
BOT_REQUEST_COUNT = Counter(
    "bot_http_requests_total",
    "Total HTTP requests to bot",
    ["method", "endpoint", "status"],
)

# --- Pipeline metrics (pushed to Pushgateway) ---
PIPELINE_DURATION = Histogram(
    "pipeline_run_duration_seconds",
    "Total pipeline run duration",
    ["stage"],
    buckets=[5, 10, 30, 60, 120, 300, 600],
)

PIPELINE_STAGE_STATUS = Counter(
    "pipeline_stage_status_total",
    "Pipeline stage completion status",
    ["stage", "status"],  # status: completed/failed/skipped
)

FETCH_SUCCESS = Counter(
    "fetch_success_total",
    "Data fetch success count",
    ["source", "asset_type"],
)

FETCH_FAILURE = Counter(
    "fetch_failure_total",
    "Data fetch failure count",
    ["source", "asset_type"],
)

LLM_CALL_COUNT = Counter(
    "llm_call_total",
    "LLM API call count",
    ["model", "is_fallback"],
)

LLM_CALL_DURATION = Histogram(
    "llm_call_duration_seconds",
    "LLM API call latency",
    ["model"],
    buckets=[1, 2, 5, 10, 15, 30],
)

ENGINE_DURATION = Histogram(
    "engine_analysis_duration_seconds",
    "Per-engine analysis duration",
    ["engine_name"],
    buckets=[1, 2, 5, 10, 30],
)

DATA_FRESHNESS_HOURS = Gauge(
    "data_freshness_hours",
    "Hours since last price data ingestion",
    ["asset_type"],
)
```

### Pattern 2: FastAPI /metrics Endpoint via make_asgi_app
**What:** Mount the prometheus_client ASGI app at /metrics on the FastAPI bot.
**When to use:** For the bot process (long-running, scrapeable by Prometheus).
**Example:**
```python
# In src/bot/main.py
from prometheus_client import make_asgi_app

# After creating FastAPI app:
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

### Pattern 3: Pushgateway for Batch Pipeline
**What:** After pipeline completes, push all collected metrics to Pushgateway.
**When to use:** At the end of pipeline main(), after all stages complete.
**Example:**
```python
# src/monitoring/pushgateway.py
from prometheus_client import push_to_gateway, REGISTRY
from src.config import settings

def push_pipeline_metrics() -> None:
    """Push all collected metrics to Pushgateway after pipeline run."""
    gateway_url = settings.prometheus_pushgateway_url
    if gateway_url:
        push_to_gateway(gateway_url, job="trade_pipeline", registry=REGISTRY)
```

### Pattern 4: Grafana Provisioning Directory Structure
**What:** YAML config files tell Grafana where to find datasources, dashboards, and alerts on startup.
**When to use:** Always for this project (D-05: dashboards as code, no persistent volume).
**Example (datasource provisioning):**
```yaml
# monitoring/grafana/provisioning/datasources/prometheus.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

**Example (dashboard provider):**
```yaml
# monitoring/grafana/provisioning/dashboards/dashboards.yml
apiVersion: 1
providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: true
    editable: false
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: false
```

### Anti-Patterns to Avoid
- **Instrumenting inside tight loops:** Never create new metric objects inside per-asset loops. Define metrics at module level; only `.labels().observe()` / `.inc()` inside loops.
- **Using default registry for pipeline Pushgateway push:** If pipeline imports bot metrics from the same default registry, all default process/platform metrics get pushed too. Use a dedicated `CollectorRegistry` for pipeline-only metrics if clean separation is needed, OR accept the overlap (simpler, acceptable for this scale).
- **Grafana dashboard manual creation:** Creating dashboards via UI means they live only in Grafana's SQLite. Since D-05 says no persistent volume, they would be lost on container restart.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Host metrics (CPU/RAM/disk) | Custom Python psutil collector | node_exporter | Covers hundreds of system metrics, battle-tested, zero maintenance |
| Batch job metric persistence | File-based metric dump | Pushgateway | Purpose-built for this exact problem; handles Prometheus scraping correctly |
| Dashboard JSON generation | Custom JSON builder | Grafana UI export -> save to git | Grafana's JSON model is complex; export from UI, then provision from file |
| Telegram alert integration | Custom alert bot | Grafana Telegram contact point | Native integration, handles retries, formatting, and throttling |
| PostgreSQL metrics | Custom pg_stat queries | postgres_exporter OR TimescaleDB built-in stats | However, for this phase, basic pg metrics (connections, query latency) can be read via SQLAlchemy instrumentation -- dedicated postgres_exporter is optional and not in scope per D-06 |

**Key insight:** The monitoring stack is entirely off-the-shelf. The only custom code is (1) adding prometheus-client instrumentation calls to existing Python functions and (2) writing Grafana dashboard JSON (exported from UI, then committed).

## Common Pitfalls

### Pitfall 1: Pushgateway Metric Accumulation
**What goes wrong:** Pushgateway retains metrics until explicitly deleted. If pipeline pushes counters that reset to 0 on each run, Pushgateway shows the last-pushed value forever (even after pipeline hasn't run for days).
**Why it happens:** Pushgateway is a cache, not a time-series store. It doesn't know when metrics are "stale."
**How to avoid:** Use `push_to_gateway()` (replaces all metrics for the job) rather than `pushadd_to_gateway()`. Include a `pipeline_last_success_timestamp` gauge that Grafana can alert on if too old.
**Warning signs:** Dashboard shows "pipeline ran 2 days ago" but Pushgateway still shows old counter values.

### Pitfall 2: Docker Network Connectivity Between Services
**What goes wrong:** Prometheus can't scrape bot's /metrics or Pushgateway because services are on different Docker networks.
**Why it happens:** Docker Compose services are on the same default network, but if you specify custom networks or use `network_mode: host` for node_exporter, connectivity breaks.
**How to avoid:** Keep all monitoring services on the default Docker Compose network. For node_exporter, use `network_mode: host` (required for host metrics) but configure Prometheus to scrape it via `host.docker.internal` or the host's IP, not the container name.
**Warning signs:** Prometheus targets page shows "connection refused" for some targets.

### Pitfall 3: node_exporter in Docker Requires Special Mounts
**What goes wrong:** node_exporter inside Docker reports container metrics, not host metrics.
**Why it happens:** By default, Docker containers see their own /proc and /sys, not the host's.
**How to avoid:** Use `--path.rootfs=/host` flag and mount `/:/host:ro,rslave`. Also set `pid: host` and `network_mode: host`.
**Warning signs:** CPU/memory metrics don't match `htop` on the host.

### Pitfall 4: Grafana Provisioned Alerts Can't Be Edited in UI
**What goes wrong:** Team tries to tweak alert thresholds in Grafana UI but changes don't persist.
**Why it happens:** File-provisioned resources are read-only in the UI. Changes require editing YAML and restarting Grafana.
**How to avoid:** Document this clearly. All alert threshold changes go through git commits -> docker restart.
**Warning signs:** UI shows "This resource is provisioned" warning banner.

### Pitfall 5: ASGI Mount Path Trailing Slash
**What goes wrong:** Prometheus gets 307 redirect or 404 when scraping `/metrics` from FastAPI.
**Why it happens:** `app.mount("/metrics", metrics_app)` serves at `/metrics/` (with trailing slash). Prometheus scrapes `/metrics` (no trailing slash) and gets redirected.
**How to avoid:** Set `metrics_path: /metrics/` in prometheus.yml scrape config, OR use a plain FastAPI route with `generate_latest()` instead of `make_asgi_app()`.
**Warning signs:** Prometheus target shows "context deadline exceeded" or "301 redirect" errors.

### Pitfall 6: Grafana Alert Contact Point Requires Bot Token at Provisioning Time
**What goes wrong:** Grafana Telegram contact point fails because bot token is hardcoded in YAML rather than using env var substitution.
**Why it happens:** Grafana provisioning YAML supports `$__env{VAR_NAME}` syntax but it's easy to miss.
**How to avoid:** Use environment variable substitution in contact point YAML: `bottoken: $__env{TELEGRAM_BOT_TOKEN}` and `chatid: $__env{TELEGRAM_MONITORING_CHAT_ID}`.
**Warning signs:** Alert fires but no Telegram message arrives.

## Code Examples

### Adding /metrics to FastAPI Bot
```python
# src/bot/main.py -- additions
from prometheus_client import make_asgi_app

# After: app = FastAPI(...)
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

### Instrumenting Pipeline Stage Durations
```python
# In src/pipeline/runner.py -- inside run_stage()
from src.monitoring.metrics import PIPELINE_DURATION, PIPELINE_STAGE_STATUS

# After stage completes:
PIPELINE_DURATION.labels(stage=stage).observe(elapsed)
PIPELINE_STAGE_STATUS.labels(stage=stage, status=final_status).inc()
```

### Instrumenting LLM Calls
```python
# In src/llm/client.py
import time
from src.monitoring.metrics import LLM_CALL_COUNT, LLM_CALL_DURATION

async def llm_completion(...) -> LLMResult:
    start = time.monotonic()
    try:
        response = await litellm.acompletion(**kwargs)
        duration = time.monotonic() - start
        model_used = response.model or model
        LLM_CALL_COUNT.labels(model=model_used, is_fallback="false").inc()
        LLM_CALL_DURATION.labels(model=model_used).observe(duration)
        return LLMResult(...)
    except Exception as exc:
        duration = time.monotonic() - start
        LLM_CALL_COUNT.labels(model="none", is_fallback="true").inc()
        LLM_CALL_DURATION.labels(model=model).observe(duration)
        return LLM_UNAVAILABLE
```

### Pushing Pipeline Metrics to Pushgateway
```python
# At end of src/pipeline/main.py async_main()
from src.monitoring.pushgateway import push_pipeline_metrics

# After all stages and post-pipeline work:
try:
    push_pipeline_metrics()
except Exception:
    logger.exception("pushgateway_push_error")
```

### Prometheus Scrape Config
```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'bot'
    static_configs:
      - targets: ['bot:8000']
    metrics_path: /metrics/

  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['pushgateway:9091']

  - job_name: 'node_exporter'
    static_configs:
      - targets: ['host.docker.internal:9100']

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### Docker Compose Services (additions to docker-compose.prod.yml)
```yaml
  prometheus:
    image: prom/prometheus:v2.53.5
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.25"
    depends_on:
      - bot
    restart: unless-stopped

  grafana:
    image: grafana/grafana:12.4.0
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_MONITORING_CHAT_ID=${TELEGRAM_MONITORING_CHAT_ID}
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
    ports:
      - "3000:3000"
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: "0.25"
    depends_on:
      - prometheus
    restart: unless-stopped

  node_exporter:
    image: prom/node-exporter:v1.9.1
    command:
      - '--path.rootfs=/host'
    network_mode: host
    pid: host
    volumes:
      - '/:/host:ro,rslave'
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: "0.1"
    restart: unless-stopped

  pushgateway:
    image: prom/pushgateway:v1.11.2
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: "0.1"
    restart: unless-stopped
```

### Grafana Telegram Contact Point Provisioning
```yaml
# monitoring/grafana/provisioning/alerting/contactpoints.yml
apiVersion: 1
contactPoints:
  - orgId: 1
    name: telegram-monitoring
    receivers:
      - uid: telegram-monitoring-1
        type: telegram
        settings:
          bottoken: $__env{TELEGRAM_BOT_TOKEN}
          chatid: $__env{TELEGRAM_MONITORING_CHAT_ID}
          message: |
            {{ template "default.message" . }}
```

### Grafana Alert Rules Example (Pipeline Failure)
```yaml
# monitoring/grafana/provisioning/alerting/rules.yml
apiVersion: 1
groups:
  - orgId: 1
    name: trade-agent-alerts
    folder: Alerts
    interval: 1m
    rules:
      - uid: pipeline-no-success
        title: Pipeline failed to complete
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 86400
              to: 0
            datasourceUid: prometheus
            model:
              expr: pipeline_last_success_timestamp
              instant: true
          - refId: C
            relativeTimeRange:
              from: 0
              to: 0
            datasourceUid: __expr__
            model:
              type: threshold
              expression: A
              conditions:
                - evaluator:
                    type: lt
                    params:
                      - $__now - 86400
        for: 5m
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Alertmanager for all alerting | Grafana unified alerting | Grafana 9+ (2022) | Simpler: no separate Alertmanager service needed for basic alert routing |
| prometheus-client generate_latest() route | make_asgi_app() ASGI mount | client_python 0.17+ | Cleaner async integration; avoids blocking event loop on metric serialization |
| Manual Grafana dashboard setup | File provisioning + JSON export | Grafana 5+ (2018, matured in 9+) | Dashboards as code; survives container restarts without persistent volumes |
| Prometheus 3.x (latest major) | Prometheus 2.53.x (LTS) | 2024 | Prometheus 3.x exists but 2.53.x is the stable/LTS line; :latest tag still points to 2.x |

## Open Questions

1. **PostgreSQL metrics depth**
   - What we know: D-01 mentions "pg connections, query latency, hypertable size" but D-06 lists only prometheus, grafana, node_exporter, pushgateway (no postgres_exporter).
   - What's unclear: Whether to instrument these via application-level SQLAlchemy metrics or add postgres_exporter.
   - Recommendation: Instrument at the application level (connection pool size from SQLAlchemy, query duration via pipeline stage timings). Skip dedicated postgres_exporter -- it's not in the decided service list. If deeper DB metrics are needed later, postgres_exporter can be added.

2. **node_exporter network_mode: host on VPS**
   - What we know: node_exporter needs `network_mode: host` and `pid: host` for accurate host metrics.
   - What's unclear: Whether the VPS firewall exposes port 9100 externally (security concern).
   - Recommendation: Use `network_mode: host` but bind node_exporter to localhost only (`--web.listen-address=127.0.0.1:9100`). Prometheus scrapes it via `host.docker.internal:9100` or `172.17.0.1:9100` (Docker host IP).

3. **Dashboard JSON creation workflow**
   - What we know: Dashboards must be provisioned as JSON files in git (D-05).
   - What's unclear: Whether to write dashboard JSON by hand or use a temporary Grafana instance to build visually then export.
   - Recommendation: Write dashboard JSON programmatically or use a reference template. The two dashboards (System Overview + Pipeline Health) are standard enough that template-based JSON is feasible without a running Grafana instance.

## Environment Availability

> External dependencies are Docker images pulled at deploy time on the VPS. No local tools beyond Docker are needed.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker + Compose | All services | Assumed (existing prod runs on it) | -- | -- |
| prometheus-client (pip) | Python instrumentation | Not yet installed | 0.24.1 (to add) | -- |
| prom/prometheus (Docker) | Metrics collection | Pulled at deploy | v2.53.5 | -- |
| grafana/grafana (Docker) | Dashboards + alerting | Pulled at deploy | 12.4.0 | -- |
| prom/node-exporter (Docker) | Host metrics | Pulled at deploy | v1.9.1 | -- |
| prom/pushgateway (Docker) | Pipeline batch metrics | Pulled at deploy | v1.11.2 | -- |

**Missing dependencies with no fallback:** None -- all are standard Docker images.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio |
| Config file | pyproject.toml |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements -> Test Map

Since no specific requirement IDs are mapped to this phase, validation focuses on the instrumentation code correctness:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| Metric definitions importable without side effects | unit | `uv run pytest tests/test_monitoring/ -x` | Wave 0 |
| /metrics endpoint returns prometheus text format | unit | `uv run pytest tests/test_bot/test_metrics.py -x` | Wave 0 |
| push_pipeline_metrics calls push_to_gateway correctly | unit | `uv run pytest tests/test_monitoring/test_pushgateway.py -x` | Wave 0 |
| Pipeline runner emits stage duration metrics | unit | `uv run pytest tests/test_pipeline/test_runner_metrics.py -x` | Wave 0 |
| LLM client emits call count and latency metrics | unit | `uv run pytest tests/test_llm/test_client_metrics.py -x` | Wave 0 |
| Docker Compose config is valid YAML | smoke | `docker compose -f docker-compose.prod.yml config` | manual |
| Prometheus config is valid | smoke | `docker run --rm -v ./monitoring/prometheus:/etc/prometheus prom/prometheus:v2.53.5 promtool check config /etc/prometheus/prometheus.yml` | manual |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green + `docker compose -f docker-compose.prod.yml config` passes

### Wave 0 Gaps
- [ ] `tests/test_monitoring/__init__.py` -- new test package
- [ ] `tests/test_monitoring/test_metrics.py` -- metric definition tests
- [ ] `tests/test_monitoring/test_pushgateway.py` -- pushgateway push tests
- [ ] `tests/test_bot/test_metrics.py` -- /metrics endpoint test

## Project Constraints (from CLAUDE.md)

- Python 3.13 on CPython
- uv package manager (not pip directly)
- Strict mypy with pydantic plugin
- ruff linting (line length 120, py313 target)
- Two-process model: bot MUST NOT import from src.pipeline or src.llm
- Bot on port 8000, FastAPI with uvicorn
- docker-compose.prod.yml for production services
- pydantic-settings for env var configuration
- structlog for JSON logging
- Bot memory limit 192M, pipeline memory limit 1280M

## Sources

### Primary (HIGH confidence)
- [prometheus-client PyPI](https://pypi.org/project/prometheus-client/) -- v0.24.1, January 2026
- [Grafana provisioning docs](https://grafana.com/docs/grafana/latest/administration/provisioning/) -- file provisioning for datasources, dashboards, alerting
- [Grafana Telegram contact point docs](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/configure-telegram/)
- [Prometheus Pushgateway Python docs](https://prometheus.github.io/client_python/exporting/pushgateway/) -- push_to_gateway API
- [Grafana alerting file provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/)

### Secondary (MEDIUM confidence)
- [prom/prometheus Docker Hub](https://hub.docker.com/r/prom/prometheus) -- v2.53.5 latest stable
- [prom/node-exporter Docker Hub](https://hub.docker.com/r/prom/node-exporter) -- v1.9.1
- [prom/pushgateway releases](https://github.com/prometheus/pushgateway/releases) -- v1.11.2
- [Grafana Docker docs](https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/) -- v12.4.x

### Tertiary (LOW confidence)
- None -- all findings verified with primary/secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components are the canonical/official tools for this problem domain
- Architecture: HIGH -- Prometheus + Grafana + Pushgateway is the textbook pattern for this exact use case (long-running service + batch job)
- Pitfalls: HIGH -- well-documented in official docs and community; ASGI mount trailing slash and node_exporter Docker mounts are commonly reported issues

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable ecosystem, slow-moving versions)
