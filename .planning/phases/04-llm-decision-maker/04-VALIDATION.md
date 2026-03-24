---
phase: 4
slug: llm-decision-maker
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x with pytest-asyncio |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_llm/ tests/test_data/test_decide.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_llm/ tests/test_data/test_decide.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | LLM-01 | unit | `uv run pytest tests/test_data/test_decide.py -x -q` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | LLM-02 | unit | `uv run pytest tests/test_llm/test_client.py -x -q` | ✅ | ⬜ pending |
| 04-02-01 | 02 | 1 | LLM-05 | unit | `uv run pytest tests/test_data/test_decide.py -x -q` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | LLM-03 | unit | `uv run pytest tests/test_data/test_decide.py -x -q` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | LLM-01 | integration | `uv run pytest tests/test_data/test_decide.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_data/test_decide.py` — stubs for LLM-01, LLM-02, LLM-03, LLM-05
- [ ] `tests/test_data/conftest.py` — shared fixtures for mock signals, mock LLM responses

*Existing test infrastructure (pytest, conftest.py, pytest-asyncio) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LLM reasoning quality | LLM-01 | Subjective — requires human review of reasoning text | Review 3+ verdicts for clarity, accuracy, and appropriate length |
| Contradiction flagging in prose | LLM-02 | Requires judgment on whether contradiction is well-explained | Create opposing signals, verify reasoning mentions the conflict |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
