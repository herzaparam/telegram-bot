---
phase: 15-prometheus-metrics-instrumentation
plan: 02
subsystem: monitoring
tags: [prometheus, starlette, middleware, metrics, counter]

# Dependency graph
requires:
  - phase: 13-server-app-monitoring
    provides: BOT_REQUEST_COUNT metric definition in src/monitoring/metrics.py
provides:
  - BOT_REQUEST_COUNT middleware wiring in bot process
  - MetricsMiddleware class for HTTP request counting
affects: [grafana-dashboards, alerting]

# Tech tracking
tech-stack:
  added: []
  patterns: [BaseHTTPMiddleware for Prometheus counter instrumentation]

key-files:
  created: []
  modified:
    - src/bot/main.py
    - tests/test_bot/test_metrics_endpoint.py

key-decisions:
  - "MetricsMiddleware uses BaseHTTPMiddleware for simplicity and consistency with Starlette patterns"

patterns-established:
  - "HTTP request counting via Starlette middleware with method/endpoint/status labels"

requirements-completed: [MON-09]

# Metrics
duration: 1min
completed: 2026-03-28
---

# Phase 15 Plan 02: Bot HTTP Request Counter Middleware Summary

**Starlette MetricsMiddleware wiring BOT_REQUEST_COUNT counter with method/endpoint/status labels on every bot HTTP request**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-28T18:20:30Z
- **Completed:** 2026-03-28T18:21:23Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- MetricsMiddleware class added to src/bot/main.py that increments BOT_REQUEST_COUNT on every HTTP request
- Labels include method (GET/POST), endpoint (/health, /telegram/webhook, /metrics), and status (200/403/503)
- Two new tests verifying counter increments on /health and /telegram/webhook endpoints

## Task Commits

Each task was committed atomically:

1. **Task 1: Add MetricsMiddleware to bot for BOT_REQUEST_COUNT** - `1cc0d9b` (feat)

## Files Created/Modified
- `src/bot/main.py` - Added MetricsMiddleware class, BOT_REQUEST_COUNT import, and middleware registration
- `tests/test_bot/test_metrics_endpoint.py` - Added two tests for counter verification with label assertions

## Decisions Made
None - followed plan as specified.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- BOT_REQUEST_COUNT is now actively incremented, Prometheus scrapes will show real bot HTTP request data
- Grafana System Overview dashboard can now display bot_http_requests_total metrics

---
## Self-Check: PASSED

All files exist, all commits verified.

*Phase: 15-prometheus-metrics-instrumentation*
*Completed: 2026-03-28*
