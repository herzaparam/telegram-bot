# Phase 13: App Monitoring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 13-app-monitoring
**Areas discussed:** Failure alerting, Health & uptime, Pipeline metrics, Error tracking
**Mode:** auto (all recommended defaults selected)

---

## Failure Alerting

| Option | Description | Selected |
|--------|-------------|----------|
| Telegram (same bot) | Reuse existing bot, zero new infrastructure | :heavy_check_mark: |
| Separate Telegram channel | Dedicated alerts channel, keeps reports clean | |
| Telegram + webhook | Telegram for user, webhook for future integrations | |

**User's choice:** [auto] Telegram (same bot) — recommended default
**Notes:** All four trigger types selected: pipeline failure, data staleness, engine errors, LLM unavailability. Dedup per asset per run to prevent alert spam.

## Health & Uptime

| Option | Description | Selected |
|--------|-------------|----------|
| Expand /health + self-report | Richer health endpoint, pipeline self-reports via Telegram | :heavy_check_mark: |
| External uptime service | Use UptimeRobot or similar to ping /health | |
| Watchdog process | Separate process monitors pipeline completion | |

**User's choice:** [auto] Expand /health + pipeline self-report — recommended default
**Notes:** Missed-run detection added as a bonus — bot tracks expected schedule and alerts if no completion message arrives.

## Pipeline Metrics

| Option | Description | Selected |
|--------|-------------|----------|
| DB table + structlog | Historical trends in DB, real-time via structured logs | :heavy_check_mark: |
| structlog only | Logs only, query via log aggregation | |
| Prometheus + Grafana | Full metrics stack with dashboards | |

**User's choice:** [auto] DB table + structlog — recommended default
**Notes:** Enables future /stats Telegram command. Prometheus/Grafana overkill for 2GB VPS single-user setup.

## Error Tracking

| Option | Description | Selected |
|--------|-------------|----------|
| Enhanced structlog + Telegram | Structured error capture, alert on unhandled exceptions | :heavy_check_mark: |
| Sentry (free tier) | External crash reporting with grouping and trends | |
| Log file rotation + grep | Simple file-based error tracking | |

**User's choice:** [auto] Enhanced structlog + Telegram alerts — recommended default
**Notes:** No external dependencies. Fits 2GB VPS constraint. Sentry would add value but introduces external dependency and network calls.

## Claude's Discretion

- DB schema for metrics table
- Alert message formatting
- Health endpoint response schema
- Missed-run detection implementation

## Deferred Ideas

None.
