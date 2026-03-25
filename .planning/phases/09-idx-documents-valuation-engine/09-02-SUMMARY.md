---
phase: 09-idx-documents-valuation-engine
plan: 02
subsystem: llm
tags: [pymupdf4llm, pdf-parsing, gpt-4o-mini, gpt-4o-vision, indonesian-finance, structured-extraction]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: LLM client wrapper (llm_completion, LLM_UNAVAILABLE)
provides:
  - parse_financial_doc() for extracting structured financial data from Indonesian PDFs
  - extract_pdf_to_markdown() for PDF text extraction via pymupdf4llm
  - Vision fallback for scanned/image-based PDF documents
affects: [09-03-valuation-engine, 09-04-wiring]

# Tech tracking
tech-stack:
  added: [pymupdf4llm, pymupdf/fitz]
  patterns: [vision-fallback-for-scanned-pdfs, indonesian-number-format-handling]

key-files:
  created:
    - src/llm/doc_parser.py
    - tests/test_llm/test_doc_parser.py
  modified:
    - pyproject.toml

key-decisions:
  - "Vision fallback triggers at <500 chars extracted text threshold"
  - "GPT-4o used for vision fallback (not GPT-4o-mini which lacks vision)"
  - "Text truncated to 8000 chars max for LLM cost control"

patterns-established:
  - "PDF extraction pattern: pymupdf4llm.to_markdown via run_in_executor for async safety"
  - "Vision fallback pattern: fitz page-to-image with base64 encoding for multimodal LLM"

requirements-completed: [IDXD-02, IDXD-03]

# Metrics
duration: 5min
completed: 2026-03-25
---

# Phase 09 Plan 02: LLM Document Parser Summary

**LLM-based Indonesian financial PDF parser using pymupdf4llm + GPT-4o-mini with GPT-4o vision fallback for scanned documents**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-25T11:58:41Z
- **Completed:** 2026-03-25T12:03:21Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- pymupdf4llm dependency installed for LLM-optimized PDF text extraction
- LLM document parser extracts 12 structured financial fields from Indonesian PDF reports
- Vision fallback using GPT-4o for scanned/image-based PDFs when text extraction yields <500 chars
- Indonesian number formatting handled via prompt instructions (dot thousands separators, jutaan/miliar units)
- 8 tests covering all paths including success, LLM unavailable, invalid JSON, and vision fallback

## Task Commits

Each task was committed atomically:

1. **Task 1: Install pymupdf4llm dependency** - `2b99dda` (chore)
2. **Task 2 RED: Failing tests for doc parser** - `600df70` (test)
3. **Task 2 GREEN: Implement doc parser** - `c0e23df` (feat)

## Files Created/Modified
- `src/llm/doc_parser.py` - LLM-based financial document parser with parse_financial_doc(), extract_pdf_to_markdown(), vision fallback
- `tests/test_llm/test_doc_parser.py` - 8 unit tests covering all behaviors
- `pyproject.toml` - Added pymupdf4llm dependency and mypy overrides

## Decisions Made
- Vision fallback threshold set at 500 characters -- below this, text extraction likely failed (scanned PDF)
- GPT-4o used for vision fallback since GPT-4o-mini lacks reliable vision support for dense financial tables
- Max text for LLM capped at 8000 chars to control token costs while capturing key financial sections
- PDF images rendered at 150 DPI for vision -- balances quality with base64 payload size

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- parse_financial_doc() ready for ValuationEngine (Plan 03) to consume
- extract_pdf_to_markdown() available for any PDF processing needs
- Vision fallback ensures scanned Indonesian financial reports can still be processed

---
*Phase: 09-idx-documents-valuation-engine*
*Completed: 2026-03-25*
