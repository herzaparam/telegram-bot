"""LLM-based financial document parser for Indonesian PDF reports.

Extracts structured financial data from laporan keuangan PDFs using
pymupdf4llm for text extraction and GPT-4o-mini for field parsing.
Vision fallback (GPT-4o) triggers for scanned/low-quality documents.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import pymupdf4llm
import structlog

from src.llm.client import LLM_UNAVAILABLE, llm_completion

log = structlog.get_logger()

FINANCIAL_EXTRACTION_SYSTEM = """\
You are a financial data extraction specialist. Extract structured financial data
from Indonesian financial reports (laporan keuangan).

Output valid JSON with these exact keys:
- revenue: total revenue (pendapatan/penjualan neto) in IDR, full number
- net_profit: net profit (laba bersih) in IDR, full number
- total_debt: total liabilities (total liabilitas/utang) in IDR, full number
- operating_cash_flow: operating cash flow (arus kas dari aktivitas operasi) in IDR
- equity: total equity (total ekuitas) in IDR, full number
- gross_margin: gross margin as decimal (e.g. 0.35 for 35%)
- operating_margin: operating margin as decimal
- net_margin: net margin as decimal
- capex: capital expenditure in IDR, full number (negative = spending)
- management_outlook: 1-2 sentence summary of management guidance/outlook (in English)
- period: reporting period (e.g. "Q3 2025", "FY 2025")
- currency_unit: the unit stated in the report header (e.g. "jutaan rupiah", "miliar rupiah")

IMPORTANT:
- Indonesian numbers use dots as thousands separators (1.234.567 = 1234567)
- Reports often state "dalam jutaan rupiah" (in millions) or "miliar rupiah" (billions)
- Convert ALL values to full IDR amounts (multiply by unit if needed)
- If a field is not found, set it to null
- Return ONLY valid JSON, no other text"""

REQUIRED_FIELDS = [
    "revenue",
    "net_profit",
    "total_debt",
    "operating_cash_flow",
    "equity",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "capex",
    "management_outlook",
    "period",
    "currency_unit",
]

_MIN_TEXT_LENGTH = 500  # Below this, trigger vision fallback
_MAX_TEXT_FOR_LLM = 8000  # Truncate to control token cost
_VISION_MAX_PAGES = 5  # Max pages to send as images for vision fallback


def extract_pdf_to_markdown(file_path: str, max_pages: int = 20) -> str:
    """Extract text from PDF as LLM-optimized markdown.

    Args:
        file_path: Path to the PDF file.
        max_pages: Maximum number of pages to extract.

    Returns:
        Markdown string of extracted text.
    """
    return pymupdf4llm.to_markdown(file_path, pages=list(range(max_pages)))  # type: ignore[no-any-return]


def _should_use_vision(text: str) -> bool:
    """Check if vision fallback should be used.

    Returns True when extracted text is too short, indicating the PDF
    may be scanned/image-based rather than text-based.
    """
    return len(text.strip()) < _MIN_TEXT_LENGTH


async def _vision_llm_fallback(file_path: str, symbol: str) -> dict[str, Any] | None:
    """Extract financial data using vision model for scanned PDFs.

    Reads PDF pages as images and sends them to GPT-4o for extraction.

    Args:
        file_path: Path to the PDF file.
        symbol: Stock ticker symbol.

    Returns:
        Parsed dict of financial fields or None on failure.
    """
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(file_path)
        image_contents: list[dict[str, Any]] = []

        for page_num in range(min(len(doc), _VISION_MAX_PAGES)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            b64_img = base64.b64encode(img_bytes).decode("utf-8")
            image_contents.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64_img}",
                        "detail": "high",
                    },
                }
            )

        doc.close()

        if not image_contents:
            log.warning("vision_no_pages", file_path=file_path)
            return None

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": FINANCIAL_EXTRACTION_SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Stock: {symbol}\n\nExtract financial data from these report pages:"},
                    *image_contents,
                ],
            },
        ]

        result = await llm_completion(
            messages,  # type: ignore[arg-type]
            model="gpt-4o",
            response_format={"type": "json_object"},
        )

        if result is LLM_UNAVAILABLE:
            log.warning("vision_llm_unavailable", symbol=symbol)
            return None

        parsed: dict[str, Any] = json.loads(result.content)
        log.info("vision_extraction_ok", symbol=symbol, model=result.model_used)
        return parsed

    except Exception:
        log.exception("vision_fallback_failed", symbol=symbol, file_path=file_path)
        return None


async def parse_financial_doc(file_path: str, symbol: str) -> dict[str, Any] | None:
    """Parse financial document and extract structured data.

    Main entry point. Extracts text from PDF, then uses LLM to parse
    financial fields. Falls back to vision model for scanned documents.

    Args:
        file_path: Path to the PDF file.
        symbol: Stock ticker symbol (e.g. "BBCA.JK").

    Returns:
        Dict with financial fields or None on any failure.
    """
    try:
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, extract_pdf_to_markdown, file_path)

        if _should_use_vision(text):
            log.info(
                "using_vision_fallback",
                symbol=symbol,
                text_length=len(text.strip()),
            )
            return await _vision_llm_fallback(file_path, symbol)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": FINANCIAL_EXTRACTION_SYSTEM},
            {"role": "user", "content": f"Stock: {symbol}\n\n{text[:_MAX_TEXT_FOR_LLM]}"},
        ]

        result = await llm_completion(
            messages,
            response_format={"type": "json_object"},
        )

        if result is LLM_UNAVAILABLE:
            log.warning("doc_parser_llm_unavailable", symbol=symbol)
            return None

        parsed: dict[str, Any] = json.loads(result.content)
        log.info(
            "doc_extraction_ok",
            symbol=symbol,
            model=result.model_used,
            fields_found=[k for k in REQUIRED_FIELDS if parsed.get(k) is not None],
        )
        return parsed

    except json.JSONDecodeError:
        log.warning("doc_parser_invalid_json", symbol=symbol)
        return None
    except Exception:
        log.exception("doc_parser_failed", symbol=symbol, file_path=file_path)
        return None
