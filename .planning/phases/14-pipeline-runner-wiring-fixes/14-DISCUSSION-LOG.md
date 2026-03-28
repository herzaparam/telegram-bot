# Phase 14: Pipeline Runner Wiring Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-03-28
**Phase:** 14-pipeline-runner-wiring-fixes
**Mode:** discuss
**Areas analyzed:** Default Stage List Strategy, Stage Validation, Timeout Mapping

## Gray Areas Discussed

### Default Stage List Strategy
- **Question:** How should the runner's default stage list be determined?
- **Options presented:**
  1. Derive from stage_funcs keys (Recommended)
  2. Keep hardcoded list, just fix it
  3. Both: derive but with explicit ordering
- **User chose:** Derive from stage_funcs keys
- **Rationale:** No hardcoded list needed. Python 3.7+ dict insertion order. main.py already defines correct order.

### Stage Validation
- **Question:** Should the runner validate that all default stages have a corresponding StageFunc?
- **Options presented:**
  1. Yes, fail fast with clear error (Recommended)
  2. Keep current behavior (warn and skip)
- **User chose:** Yes, fail fast with clear error
- **Rationale:** Catches configuration errors at pipeline start rather than producing mysterious missing-stage behavior.

## Corrections Made

No corrections — both recommendations accepted.
