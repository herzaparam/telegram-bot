---
phase: 6
slug: accuracy-tracking-scorecard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `uv run pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `uv run pytest tests/ -v --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | EVAL-01 | unit | `uv run pytest tests/test_data/test_evaluate.py -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | EVAL-01 | unit | `uv run pytest tests/test_db/test_evaluation_repo.py -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | EVAL-05 | unit | `uv run pytest tests/test_data/test_accuracy.py -x` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 2 | TBOT-04 | unit | `uv run pytest tests/test_bot/test_scorecard.py -x` | ❌ W0 | ⬜ pending |
| 06-02-03 | 02 | 2 | REPT-01 | unit | `uv run pytest tests/test_report/test_scorecard_section.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_data/test_evaluate.py` — stubs for EVAL-01 (evaluate stage, correctness classification, multi-window)
- [ ] `tests/test_db/test_evaluation_repo.py` — stubs for evaluation repository CRUD
- [ ] `tests/test_data/test_accuracy.py` — stubs for EVAL-05 (accuracy stats computation)
- [ ] `tests/test_bot/test_scorecard.py` — stubs for TBOT-04 (/scorecard command handler)
- [ ] `tests/test_report/test_scorecard_section.py` — stubs for REPT-01 (scorecard section in daily report)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| IDX holiday calendar correctness | EVAL-01 | Requires real calendar verification | Compare idx_holidays table against official IDX calendar for 2026 |
| Telegram scorecard message rendering | TBOT-04 | Visual formatting in Telegram client | Send /scorecard in test chat, verify emoji/layout renders correctly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
