---
phase: 13
slug: server-and-app-monitoring-with-prometheus-etc
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2+ with pytest-asyncio |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | Metric definitions | unit | `uv run pytest tests/test_monitoring/ -x` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | /metrics endpoint | unit | `uv run pytest tests/test_bot/test_metrics.py -x` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 1 | Pushgateway push | unit | `uv run pytest tests/test_monitoring/test_pushgateway.py -x` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 1 | Pipeline metrics | unit | `uv run pytest tests/test_pipeline/test_runner_metrics.py -x` | ❌ W0 | ⬜ pending |
| 13-02-02 | 02 | 1 | LLM metrics | unit | `uv run pytest tests/test_llm/test_client_metrics.py -x` | ❌ W0 | ⬜ pending |
| 13-03-01 | 03 | 2 | Docker Compose valid | smoke | `docker compose -f docker-compose.prod.yml config` | ✅ | ⬜ pending |
| 13-03-02 | 03 | 2 | Prometheus config valid | smoke | `docker run --rm -v ./monitoring/prometheus:/etc/prometheus prom/prometheus:v2.53.5 promtool check config /etc/prometheus/prometheus.yml` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_monitoring/__init__.py` — new test package
- [ ] `tests/test_monitoring/test_metrics.py` — metric definition tests
- [ ] `tests/test_monitoring/test_pushgateway.py` — pushgateway push tests
- [ ] `tests/test_bot/test_metrics.py` — /metrics endpoint test
- [ ] `tests/test_pipeline/test_runner_metrics.py` — pipeline runner metrics tests
- [ ] `tests/test_llm/test_client_metrics.py` — LLM client metrics tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Grafana dashboards render correctly | D-10 | Visual verification needed | Open Grafana, check both System Overview and Pipeline Health pages render with panels |
| Telegram alerts delivered | D-08 | Requires real Telegram channel | Trigger a test alert in Grafana, verify it arrives in monitoring chat |
| node_exporter reports host metrics | D-01 | Requires Docker host environment | Check Prometheus targets, verify node_exporter shows host CPU/RAM not container metrics |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
