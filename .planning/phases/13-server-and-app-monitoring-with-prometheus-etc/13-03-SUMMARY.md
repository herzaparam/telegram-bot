---
phase: 13-server-and-app-monitoring-with-prometheus-etc
plan: 03
subsystem: infra
tags: [prometheus, grafana, node-exporter, pushgateway, docker-compose, monitoring, alerting, telegram]

# Dependency graph
requires:
  - phase: 13-server-and-app-monitoring-with-prometheus-etc
    provides: "metric definitions (Plan 01) and instrumentation hooks (Plan 02)"
provides:
  - "Prometheus scrape config targeting bot, pushgateway, node_exporter, and self"
  - "Grafana provisioning with datasource, dashboard provider, Telegram alerting"
  - "Six alert rules: pipeline failure, CPU, memory, disk, bot down, data staleness"
  - "System Overview dashboard (CPU, memory, disk, bot status, network, uptime)"
  - "Pipeline Health dashboard (stage duration, LLM metrics, fetch rates, engine perf, data freshness)"
  - "Docker Compose services: prometheus, grafana, node_exporter, pushgateway"
affects: [deployment, operations]

# Tech tracking
tech-stack:
  added: [prom/prometheus:v2.53.5, grafana/grafana:12.4.0, prom/node-exporter:v1.9.1, prom/pushgateway:v1.11.2]
  patterns: [grafana-file-provisioning, prometheus-scrape-config, grafana-dashboard-as-code, grafana-unified-alerting]

key-files:
  created:
    - monitoring/prometheus/prometheus.yml
    - monitoring/grafana/provisioning/datasources/prometheus.yml
    - monitoring/grafana/provisioning/dashboards/dashboards.yml
    - monitoring/grafana/provisioning/alerting/contactpoints.yml
    - monitoring/grafana/provisioning/alerting/rules.yml
    - monitoring/grafana/provisioning/alerting/policies.yml
    - monitoring/grafana/dashboards/system-overview.json
    - monitoring/grafana/dashboards/pipeline-health.json
  modified:
    - docker-compose.prod.yml

key-decisions:
  - "node_exporter bound to 127.0.0.1:9100 for security; Prometheus reaches it via Docker bridge gateway IP 172.17.0.1"
  - "metrics_path set to /metrics/ (trailing slash) to match FastAPI mount redirect behavior"
  - "Grafana admin password defaults to 'admin' if GRAFANA_ADMIN_PASSWORD not set"
  - "Pipeline service gets PROMETHEUS_PUSHGATEWAY_URL as direct environment override in docker-compose"

patterns-established:
  - "Grafana dashboards as code: JSON files in monitoring/grafana/dashboards/, auto-loaded via file provider"
  - "Grafana alerting as code: YAML files in monitoring/grafana/provisioning/alerting/, read-only in UI"
  - "Monitoring directory structure: monitoring/{prometheus,grafana}/{config files}"

requirements-completed: [MON-07, MON-08, MON-09, MON-10, MON-11]

# Metrics
duration: 2min
completed: 2026-03-28
---

# Phase 13 Plan 03: Monitoring Infrastructure Summary

**Full Prometheus+Grafana stack with 4 scrape targets, 2 dashboards (14 panels), 6 alert rules, and Telegram notifications**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-28T16:56:33Z
- **Completed:** 2026-03-28T16:59:03Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Prometheus configured to scrape bot /metrics/, pushgateway, node_exporter (host), and itself at 15s intervals with 30-day retention
- Grafana auto-provisions Prometheus datasource, 2 dashboards, Telegram contact point, notification policy, and 6 alert rules on startup
- System Overview dashboard: CPU usage, memory usage, disk usage (gauge), bot status (stat), network I/O, uptime
- Pipeline Health dashboard: stage durations (p95), success rate, LLM latency/count, fetch success/failure, engine duration, data freshness (gauge), time since last success
- Six alert rules covering pipeline failure (24h), high CPU (>90%), high memory (>85%), high disk (>80%), bot down (2min), data staleness (24h)
- Docker Compose updated with prometheus, grafana, node_exporter, and pushgateway services

## Task Commits

Each task was committed atomically:

1. **Task 1: Create monitoring directory structure, Prometheus config, and Docker Compose services** - `e6dbcfd` (feat)
2. **Task 2: Create Grafana dashboard JSON files (System Overview + Pipeline Health)** - `8bbc514` (feat)

## Files Created/Modified
- `monitoring/prometheus/prometheus.yml` - Scrape config for 4 targets (bot, pushgateway, node_exporter, prometheus)
- `monitoring/grafana/provisioning/datasources/prometheus.yml` - Prometheus datasource auto-provisioning
- `monitoring/grafana/provisioning/dashboards/dashboards.yml` - Dashboard file provider config
- `monitoring/grafana/provisioning/alerting/contactpoints.yml` - Telegram contact point with env var substitution
- `monitoring/grafana/provisioning/alerting/rules.yml` - 6 alert rules (pipeline, CPU, memory, disk, bot, data)
- `monitoring/grafana/provisioning/alerting/policies.yml` - Notification routing to Telegram
- `monitoring/grafana/dashboards/system-overview.json` - System Overview dashboard (6 panels)
- `monitoring/grafana/dashboards/pipeline-health.json` - Pipeline Health dashboard (8 panels)
- `docker-compose.prod.yml` - Added prometheus, grafana, node_exporter, pushgateway services + prometheus_data volume

## Decisions Made
- node_exporter binds to 127.0.0.1:9100 (not exposed externally) with Prometheus reaching via Docker bridge gateway IP 172.17.0.1
- metrics_path /metrics/ with trailing slash to handle FastAPI mount redirect (Pitfall 5 from research)
- GRAFANA_ADMIN_PASSWORD defaults to "admin" if env var not set (convenience for development)
- Pipeline service receives PROMETHEUS_PUSHGATEWAY_URL as direct docker-compose environment override

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

Environment variables to add to `.env` or deployment config:
- `GRAFANA_ADMIN_PASSWORD` - Grafana admin password (defaults to "admin")
- `TELEGRAM_MONITORING_CHAT_ID` - Telegram chat ID for monitoring alerts (separate from trading signals chat)
- `TELEGRAM_BOT_TOKEN` - Already exists, used by Grafana for alert delivery

## Next Phase Readiness
- Monitoring infrastructure complete; ready for deployment
- Plan 01 (metrics definitions) and Plan 02 (instrumentation) provide the application-level metrics that these dashboards visualize
- Grafana accessible on port 3000 with admin credentials

---
*Phase: 13-server-and-app-monitoring-with-prometheus-etc*
*Completed: 2026-03-28*
