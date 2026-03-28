# Phase 13: Server and App Monitoring with Prometheus, etc - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 13-server-and-app-monitoring-with-prometheus-etc
**Areas discussed:** Metrics scope, Stack choice, Alerting rules, Dashboard design

---

## Metrics Scope

### Instrumentation Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Full depth | Server metrics (CPU/RAM/disk via node_exporter), app metrics (pipeline run duration, per-engine scores/latency, LLM call count/cost/latency, fetch success rates), DB metrics (pg connections, query latency, hypertable size) | ✓ |
| App + server only | Server metrics + pipeline/bot app metrics, but skip detailed per-engine and DB-level instrumentation | |
| Server health only | Just CPU, RAM, disk, uptime — no application-level metrics from Python code | |

**User's choice:** Full depth
**Notes:** None

### Pipeline Metrics Exposure

| Option | Description | Selected |
|--------|-------------|----------|
| Pushgateway | Pipeline pushes metrics to Prometheus Pushgateway after each run — natural fit since pipeline is a batch job. Bot exposes its own /metrics on port 8000. | ✓ |
| Shared via bot | Pipeline writes metrics to DB, bot reads and exposes them on /metrics. Simpler but couples the two processes. | |
| Separate exporter | Standalone Python process exposing pipeline metrics. Extra RAM cost on 2GB VPS. | |

**User's choice:** Pushgateway
**Notes:** None

---

## Stack Choice

### Monitoring Stack

| Option | Description | Selected |
|--------|-------------|----------|
| Prometheus + Grafana | Industry standard. Prometheus ~40MB idle, Grafana ~100MB. Total ~175-250MB with node_exporter and Pushgateway. Fits 2GB budget. | ✓ |
| VictoriaMetrics + Grafana | Lighter Prometheus-compatible TSDB (~30MB). Saves ~10-20MB but less ecosystem support. | |
| Grafana Alloy + Grafana Cloud | Ship metrics to free-tier Grafana Cloud. Only run agent locally (~50MB). No local storage. | |

**User's choice:** Prometheus + Grafana
**Notes:** None

### Deployment Method

| Option | Description | Selected |
|--------|-------------|----------|
| Docker Compose | Add services to docker-compose.prod.yml. Config files in monitoring/ directory. | ✓ |
| System packages | Install via apt/systemd. Lighter but harder to reproduce. | |
| Separate compose file | New docker-compose.monitoring.yml alongside existing compose. | |

**User's choice:** Docker Compose
**Notes:** None

### Python Client Library

| Option | Description | Selected |
|--------|-------------|----------|
| prometheus-client | Official Prometheus Python client. Mature, well-documented. Manual /metrics endpoint integration. | ✓ |
| prometheus-fastapi-instrumentator | Auto-instruments FastAPI routes. Less control but zero-config for HTTP metrics. | |
| Both combined | prometheus-client for custom app metrics + prometheus-fastapi-instrumentator for automatic HTTP metrics. | |

**User's choice:** prometheus-client
**Notes:** None

### Dashboard Persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Provisioned dashboards | Dashboards-as-code in JSON files, auto-loaded on startup. Dashboards live in git. | ✓ |
| Persistent volume | Mount Grafana's /var/lib/grafana to Docker volume. Preserves manual edits. | |
| Both | Provisioned base dashboards + persistent volume for ad-hoc custom dashboards. | |

**User's choice:** Provisioned dashboards
**Notes:** None

---

## Alerting Rules

### Alert Delivery

| Option | Description | Selected |
|--------|-------------|----------|
| Telegram | Reuse existing Telegram bot to send alerts. Grafana native Telegram contact point. | ✓ |
| Telegram + email | Telegram for critical, email digest for warnings. Needs SMTP config. | |
| Grafana only | Dashboard-only alert status. No push notifications. | |

**User's choice:** Telegram
**Notes:** None

### Critical Alert Conditions

| Option | Description | Selected |
|--------|-------------|----------|
| Pipeline failed to complete | Daily pipeline didn't finish or exited with errors. | ✓ |
| High resource usage | CPU > 90% for 5min, RAM > 85%, disk > 80%. | ✓ |
| Bot/service down | Bot health check fails for > 2 minutes. | ✓ |
| Data staleness | No new price data ingested for > 24 hours. | ✓ |

**User's choice:** All four conditions
**Notes:** None

### Alerting Engine

| Option | Description | Selected |
|--------|-------------|----------|
| Grafana alerting | Simpler setup. Define alert rules in Grafana provisioning. Native Telegram contact point. | ✓ |
| Alertmanager | More powerful routing, grouping, silencing. Separate service (~30MB). | |
| Both | Alertmanager for Prometheus rules, Grafana for dashboard-specific alerts. | |

**User's choice:** Grafana alerting
**Notes:** None

### Alert Chat Destination

| Option | Description | Selected |
|--------|-------------|----------|
| Same chat | All bot messages in one place. Monitoring alerts infrequent. | |
| Separate chat/group | Keep signal delivery clean. Monitoring alerts in dedicated group. | ✓ |

**User's choice:** Separate chat/group
**Notes:** User wants to keep trading signals clean from monitoring noise. Requires second TELEGRAM_MONITORING_CHAT_ID.

---

## Dashboard Design

### Dashboard Organization

| Option | Description | Selected |
|--------|-------------|----------|
| Two pages | Page 1: System (CPU, RAM, disk, containers). Page 2: App (pipeline runs, engine stats, LLM costs, data freshness). | ✓ |
| Single page | Everything on one scrollable page with collapsible sections. | |
| Three pages | System + Pipeline + Bot/Telegram. Most granular. | |

**User's choice:** Two pages
**Notes:** User initially asked what "two dashboards" meant — clarified that dashboards are just pages within the single Grafana web app, not separate services.

### Grafana Access

| Option | Description | Selected |
|--------|-------------|----------|
| Auth required | Grafana built-in login (admin + password from env). Access via VPS IP:3000. | ✓ |
| Behind reverse proxy | Nginx/Caddy with HTTPS + auth. More secure but extra setup. | |
| Localhost only | SSH tunnel access only. Most secure, less convenient. | |

**User's choice:** Auth required (built-in)
**Notes:** None

## Claude's Discretion

- Prometheus scrape intervals and retention period
- Specific panel layout, time ranges, and refresh rates within dashboards
- node_exporter collector configuration
- Pushgateway job naming conventions
- Grafana dashboard color scheme and thresholds

## Deferred Ideas

None
