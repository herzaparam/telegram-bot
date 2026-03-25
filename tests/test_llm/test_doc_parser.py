"""Tests for LLM-based financial document parser."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.client import LLM_UNAVAILABLE, LLMResult
from src.llm.doc_parser import (
    FINANCIAL_EXTRACTION_SYSTEM,
    REQUIRED_FIELDS,
    _should_use_vision,
    extract_pdf_to_markdown,
    parse_financial_doc,
)

_SAMPLE_MARKDOWN = """
# Laporan Keuangan PT Bank Central Asia Tbk
## Periode: Q3 2025

### Laba Rugi Konsolidasi
| Item | Jumlah (jutaan rupiah) |
|------|----------------------|
| Pendapatan Neto | 45.678.900 |
| Laba Bersih | 12.345.678 |

### Neraca
| Item | Jumlah (jutaan rupiah) |
|------|----------------------|
| Total Liabilitas | 890.123.456 |
| Total Ekuitas | 234.567.890 |
""" * 3  # Repeat to exceed 500 chars

_VALID_LLM_JSON = json.dumps({
    "revenue": 45678900000000,
    "net_profit": 12345678000000,
    "total_debt": 890123456000000,
    "operating_cash_flow": 5000000000000,
    "equity": 234567890000000,
    "gross_margin": 0.45,
    "operating_margin": 0.35,
    "net_margin": 0.27,
    "capex": -2000000000000,
    "management_outlook": "Management expects continued growth driven by digital banking.",
    "period": "Q3 2025",
    "currency_unit": "jutaan rupiah",
})


class TestParseFinancialDoc:
    """Test parse_financial_doc main entry point."""

    async def test_returns_dict_with_all_required_keys(self) -> None:
        """Test 1: parse_financial_doc returns dict with all required keys."""
        with (
            patch("src.llm.doc_parser.extract_pdf_to_markdown", return_value=_SAMPLE_MARKDOWN),
            patch("src.llm.doc_parser.llm_completion", new_callable=AsyncMock) as mock_llm,
        ):
            mock_llm.return_value = LLMResult(content=_VALID_LLM_JSON, model_used="gpt-4o-mini")
            result = await parse_financial_doc("/fake/report.pdf", "BBCA.JK")

        assert result is not None
        for field in REQUIRED_FIELDS:
            assert field in result, f"Missing required field: {field}"

    async def test_returns_none_when_llm_unavailable(self) -> None:
        """Test 2: parse_financial_doc returns None when LLM returns LLM_UNAVAILABLE."""
        with (
            patch("src.llm.doc_parser.extract_pdf_to_markdown", return_value=_SAMPLE_MARKDOWN),
            patch("src.llm.doc_parser.llm_completion", new_callable=AsyncMock) as mock_llm,
        ):
            mock_llm.return_value = LLM_UNAVAILABLE
            result = await parse_financial_doc("/fake/report.pdf", "BBCA.JK")

        assert result is None

    async def test_returns_none_when_json_parsing_fails(self) -> None:
        """Test 3: parse_financial_doc returns None when JSON parsing fails."""
        with (
            patch("src.llm.doc_parser.extract_pdf_to_markdown", return_value=_SAMPLE_MARKDOWN),
            patch("src.llm.doc_parser.llm_completion", new_callable=AsyncMock) as mock_llm,
        ):
            mock_llm.return_value = LLMResult(
                content="This is not valid JSON at all",
                model_used="gpt-4o-mini",
            )
            result = await parse_financial_doc("/fake/report.pdf", "BBCA.JK")

        assert result is None

    async def test_calls_vision_fallback_when_text_too_short(self) -> None:
        """Test 6: parse_financial_doc calls _vision_llm_fallback when text is too short."""
        with (
            patch("src.llm.doc_parser.extract_pdf_to_markdown", return_value="short"),
            patch(
                "src.llm.doc_parser._vision_llm_fallback",
                new_callable=AsyncMock,
            ) as mock_vision,
        ):
            mock_vision.return_value = json.loads(_VALID_LLM_JSON)
            result = await parse_financial_doc("/fake/report.pdf", "BBCA.JK")

        mock_vision.assert_called_once_with("/fake/report.pdf", "BBCA.JK")
        assert result is not None


class TestShouldUseVision:
    """Test _should_use_vision helper."""

    def test_returns_true_when_text_short(self) -> None:
        """Test 4: _should_use_vision returns True when extracted text < 500 chars."""
        assert _should_use_vision("short text") is True

    def test_returns_false_when_text_long(self) -> None:
        """Test 5: _should_use_vision returns False when extracted text >= 500 chars."""
        assert _should_use_vision("x" * 500) is False


class TestFinancialExtractionPrompt:
    """Test prompt constants."""

    def test_prompt_contains_indonesian_mappings(self) -> None:
        """Test 7: FINANCIAL_EXTRACTION_SYSTEM contains Indonesian field name mappings."""
        assert "pendapatan" in FINANCIAL_EXTRACTION_SYSTEM.lower()
        assert "laba bersih" in FINANCIAL_EXTRACTION_SYSTEM.lower()
        assert "liabilitas" in FINANCIAL_EXTRACTION_SYSTEM.lower()
        assert "ekuitas" in FINANCIAL_EXTRACTION_SYSTEM.lower()


class TestExtractPdfToMarkdown:
    """Test PDF extraction wrapper."""

    def test_calls_pymupdf4llm_with_correct_args(self) -> None:
        """Test 8: extract_pdf_to_markdown calls pymupdf4llm.to_markdown with correct args."""
        with patch("src.llm.doc_parser.pymupdf4llm") as mock_pymupdf:
            mock_pymupdf.to_markdown.return_value = "extracted markdown"
            result = extract_pdf_to_markdown("/fake/report.pdf", max_pages=10)

        mock_pymupdf.to_markdown.assert_called_once_with(
            "/fake/report.pdf", pages=list(range(10))
        )
        assert result == "extracted markdown"
