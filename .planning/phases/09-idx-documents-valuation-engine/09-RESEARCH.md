# Phase 9: IDX Documents + Valuation Engine - Research

**Researched:** 2026-03-25
**Domain:** PDF financial document parsing, valuation modeling (DCF, peer comparison, scenario analysis), IDX website scraping
**Confidence:** MEDIUM-HIGH

## Summary

Phase 9 introduces two major subsystems: (1) an IDX financial document fetcher/parser that downloads laporan keuangan PDFs from idx.co.id and extracts structured financial data using pymupdf4llm + GPT, and (2) a ValuationEngine that computes DCF, peer comparison, and scenario analysis for IDX stocks (with lightweight crypto proxies). These feed into new `/valuation` and `/fundamentals` Telegram commands and a valuation summary section in the daily report.

The IDX website provides a JSON API endpoint for listing financial reports that can be accessed via httpx without a headless browser. PDF extraction uses pymupdf4llm (v0.0.17+) to convert pages to LLM-optimized markdown, then GPT-4o-mini extracts structured financial fields from Bahasa Indonesia text. The ValuationEngine follows the existing BaseEngine contract and zone-mapping scoring pattern from FundamentalEngine.

**Primary recommendation:** Build the IDX doc fetcher as a weekly-scheduled data fetcher (not a BaseFetcher subclass, since it does not produce OHLCVRow), the LLM doc parser as a module in `src/llm/doc_parser.py`, and the ValuationEngine in `src/engines/valuation.py` following the existing BaseEngine + constructor-injection pattern.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Auto-scrape idx.co.id for laporan keuangan using direct HTTP requests via httpx (not headless browser). Reverse-engineer download URLs for each watchlist stock
- **D-02:** Fetch both quarterly (Q1, Q2, Q3 interim) and annual reports. Keep last 4 quarterly + 2 annual reports per stock for trend analysis
- **D-03:** Weekly check frequency -- run the IDX doc fetcher once per week (financial reports update quarterly, daily is wasteful)
- **D-04:** Store both raw PDFs (in `data/financial_docs/` directory) and extracted data in DB. Allows re-parsing if extraction logic improves
- **D-05:** Graceful degradation on scraper failure -- fall back to existing yfinance fundamentals (FundamentalEngine), log error, send Telegram alert to user. Valuation runs with available data
- **D-06:** Extract core fields: revenue (pendapatan), net profit (laba bersih), total debt (utang), operating cash flow (arus kas operasi), equity (ekuitas) PLUS margins (gross, operating, net), management outlook/guidance text, and capex
- **D-07:** LLM handles Bahasa Indonesia in-prompt -- send Indonesian text to GPT-4o-mini with extraction prompt using Indonesian field names, LLM returns structured numeric/English output. Vision LLM fallback for complex/scanned pages per architecture
- **D-08:** PDF-extracted data enhances (not replaces) existing FundamentalEngine. FundamentalEngine keeps using yfinance for quick ratios. ValuationEngine reads PDF-extracted financials for DCF/peer analysis. Two complementary sources
- **D-09:** Cross-validate key metrics -- compare PDF-extracted revenue/profit with yfinance reported values when available. Flag discrepancies >10% for review
- **D-10:** Database schema: `financial_docs` table (PDF metadata: stock, period, download date, file path, parse status) + `financial_data` table (extracted fields per doc, one row per metric per period). Normalized and queryable
- **D-11:** DCF discount rate: formula-based WACC from risk-free rate (BI rate or US 10Y) + equity risk premium + beta. Growth rate from historical revenue CAGR capped at GDP growth. Transparent and reproducible
- **D-12:** Peer groups: sector-based from IDX classification (Banking, Telco, Consumer, etc.). Compare P/E, P/B, EV/EBITDA within sector using existing asset metadata
- **D-13:** Crypto valuation: lightweight proxies only -- NVT ratio for BTC/ETH, market cap / TVL for DeFi tokens. On-chain engine (Phase 10) will add more depth
- **D-14:** Scenario analysis: base = historical revenue CAGR, bull = +1 standard deviation, bear = -1 SD. Probability weights: 25% bull / 50% base / 25% bear. Data-driven and reproducible
- **D-15:** ValuationEngine follows BaseEngine contract: `analyze(asset_id, symbol, df) -> Signal` with score reflecting margin of safety (undervalued = positive, overvalued = negative)
- **D-16:** `/valuation BBCA` shows summary: fair value estimate, current price, margin of safety %, DCF range (bull/base/bear), peer comparison rank. Fits in one Telegram message
- **D-17:** `/fundamentals BBCA` shows ratio dashboard: P/E, P/B, ROE, margins, debt/equity, QoQ changes with trend arrows. Complementary to /valuation
- **D-18:** `/valuation` and `/fundamentals` are IDX stocks only. Crypto assets get: "Valuation not available for crypto assets -- use /report BTC for signal analysis"
- **D-19:** Daily report valuation summary (REPT-03): compact table per IDX stock -- ticker, current price, fair value, margin of safety %, verdict arrow. Quick scan format
- **D-20:** When no financial docs available (first run or scraper failed): show yfinance-based rough estimate with clear disclaimer "estimated from market data only -- no financial reports parsed yet"
- **D-21:** QoQ ratio change alerts (VALN-05): included in daily report only when significant changes detected after new quarterly report parsing. No push notifications

### Claude's Discretion
- idx.co.id URL structure and scraping implementation details
- pymupdf4llm extraction parameters and Vision LLM fallback trigger conditions
- LLM prompt design for financial data extraction and news analysis
- financial_docs and financial_data table column details and indexes
- WACC calculation specifics (risk premium values, beta source)
- Peer comparison metric weights and ranking algorithm
- NVT and TVL data sources for crypto proxies
- Scenario analysis terminal value methodology
- Telegram message formatting and emoji usage
- QoQ change threshold values for "significant" alerts
- Error handling and retry logic for each new component
- Alembic migration details for new tables
- How to wire ValuationEngine into `_get_engines_for_asset()` in analyze.py

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IDXD-01 | System downloads laporan keuangan (quarterly/annual) from idx.co.id | IDX API endpoint discovery, httpx-based fetcher pattern |
| IDXD-02 | GPT parses PDF reports in Bahasa Indonesia | pymupdf4llm extraction + LLM JSON mode parsing |
| IDXD-03 | System extracts revenue, net profit, debt, cash flow, management outlook | LLM prompt design with Indonesian field names, structured JSON output |
| ENGN-15 | Valuation engine (DCF, peer multiples, margin of safety) with fair value estimates | ValuationEngine following BaseEngine contract, DCF/peer/scenario patterns |
| VALN-01 | DCF model for IDX stocks using parsed financial data | WACC formula, growth rate estimation, terminal value calculation |
| VALN-02 | Comparable company analysis with sector peer grouping | Sector classification, multi-metric peer ranking |
| VALN-03 | Crypto valuation proxies (NVT ratio, stock-to-flow for BTC, revenue multiples for DeFi) | CoinGecko/blockchain.com for NVT data, DeFiLlama for TVL |
| VALN-04 | Scenario analysis (bull/base/bear) with probability-weighted returns | Revenue CAGR + std deviation methodology |
| VALN-05 | Quarter-over-quarter ratio tracking with change alerts | QoQ comparison logic, threshold-based alerting in daily report |
| TBOT-09 | /valuation BBCA shows DCF, peer comparison, fair value | Bot handler + formatter pattern from existing commands |
| TBOT-13 | /fundamentals BBCA deep ratio dashboard | Bot handler reading from financial_data + stock_fundamentals tables |
| REPT-03 | Valuation summary (fair value vs market price, margin of safety) | Daily report section formatter extending existing pattern |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Async Python pipeline** -- all I/O must be async; blocking calls wrapped in `run_in_executor`
- **Two-process boundary** -- bot MUST NOT import pipeline/llm modules; shared formatting lives in `src/report/`
- **pydantic-settings** for all config via `src/config.py`
- **SQLAlchemy ORM** for models in `src/db/models.py` with Alembic migrations
- **structlog JSON logging** with component binding
- **Per-asset error isolation** -- engines never crash the pipeline; `_failed_signal()` fallback
- **Sequential engine execution** with `gc.collect()` after each asset
- **HTML parse_mode** for all Telegram messages
- **Fetch-then-cache** pattern: fetchers store raw data in DB, engines read from DB

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pymupdf4llm | 0.0.17+ | PDF to LLM-optimized markdown | Built on PyMuPDF, fastest Python PDF parser, handles tables/multi-column, OCR when needed |
| PyMuPDF | 1.25+ | Underlying PDF engine for pymupdf4llm | Required dependency, C-based performance |
| httpx | 0.28.1+ (already installed) | HTTP client for idx.co.id API + PDF downloads | Already in project, async support, connection pooling |
| litellm | 1.82.6+ (already installed) | LLM calls for PDF parsing + vision fallback | Already in project, `llm_completion()` wrapper |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | (already via pandas) | WACC/DCF calculations, std deviation for scenarios | Statistical computations in ValuationEngine |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pymupdf4llm | pdfplumber | pdfplumber is table-focused but lacks LLM-optimized markdown output; pymupdf4llm is architecture decision |
| httpx for idx.co.id | Selenium/Playwright | Headless browser heavier, slower, unnecessary -- IDX has a JSON API endpoint (D-01 locked) |

**Installation:**
```bash
uv add pymupdf4llm
```

**Note:** httpx, litellm, pandas, numpy are already available in the project. Only pymupdf4llm needs to be added as a new dependency.

## Architecture Patterns

### Recommended Project Structure (new files)
```
src/
  data/
    idx_doc_fetcher.py      # IDX financial doc fetcher (weekly schedule)
  llm/
    doc_parser.py            # LLM-based PDF financial data extraction
  engines/
    valuation.py             # ValuationEngine (DCF, peer, scenario, crypto proxy)
  bot/handlers/
    valuation.py             # /valuation command handler
    fundamentals.py          # /fundamentals command handler
  report/
    formatter.py             # Extended with format_valuation_summary(), format_valuation_detail(), format_fundamentals_dashboard()
  db/
    models.py                # Extended with FinancialDoc, FinancialData models
    migrations/versions/
      008_financial_docs.py  # New Alembic migration
data/
  financial_docs/            # Raw PDF storage directory (gitignored)
tests/
  test_data/
    test_idx_doc_fetcher.py
  test_llm/
    test_doc_parser.py
  test_engines/
    test_valuation.py
  test_bot/
    test_valuation_handler.py
    test_fundamentals_handler.py
```

### Pattern 1: IDX Document Fetcher (Weekly Data Fetcher)
**What:** Async function that queries the IDX API for financial report metadata, downloads PDFs, and stores them locally + records in `financial_docs` table.
**When to use:** Run as part of fetch stage, gated by weekly frequency check (similar to fundamental_fetcher.py cache TTL pattern).
**Example:**
```python
# IDX API endpoint (verified from open-source scrapers)
IDX_REPORT_API = (
    "https://idx.co.id/umbraco/Surface/ListedCompany/GetFinancialReport"
    "?indexFrom=0&pageSize=10"
    "&year={year}&reportType=rdf&periode={periode}&kodeEmiten={code}"
)
# periode values: "tw1" (Q1), "tw2" (Q2), "tw3" (Q3), "tahunan" (annual)

async def fetch_idx_docs(session: AsyncSession, asset: Asset) -> None:
    """Fetch financial docs for IDX stock. Weekly frequency check."""
    # 1. Check if we already fetched this week
    # 2. Query IDX API for report metadata (JSON response)
    # 3. Filter attachments by filename keywords (financial report indicators)
    # 4. Download PDF via File_Path URL from attachment metadata
    # 5. Save to data/financial_docs/{symbol}/{period}.pdf
    # 6. Record in financial_docs table with parse_status='pending'
```

### Pattern 2: LLM Doc Parser (pymupdf4llm + GPT)
**What:** Converts PDF to markdown via pymupdf4llm, then sends to GPT-4o-mini for structured extraction. Vision LLM fallback if text extraction is poor quality.
**When to use:** After PDF download, during fetch stage or as separate parse step.
**Example:**
```python
import pymupdf4llm

def extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF using pymupdf4llm."""
    md_text = pymupdf4llm.to_markdown(file_path)
    return md_text

async def parse_financial_doc(file_path: str, symbol: str) -> dict:
    """Parse financial doc using LLM."""
    text = await asyncio.get_event_loop().run_in_executor(
        None, extract_pdf_text, file_path
    )
    # Check quality -- if too short or garbled, use Vision LLM fallback
    if len(text.strip()) < 500:
        return await _vision_llm_fallback(file_path, symbol)

    messages = [
        {"role": "system", "content": FINANCIAL_EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Stock: {symbol}\n\n{text[:8000]}"},
    ]
    result = await llm_completion(
        messages, response_format={"type": "json_object"}
    )
    return json.loads(result.content)
```

### Pattern 3: ValuationEngine (BaseEngine subclass)
**What:** Reads financial_data from DB (constructor-injected), computes DCF/peer/scenario analysis, returns Signal with margin-of-safety score.
**When to use:** During analyze stage, for stock assets with available financial data.
**Example:**
```python
class ValuationEngine(BaseEngine):
    def __init__(
        self,
        financial_data: list[dict] | None = None,
        peer_data: list[dict] | None = None,
        macro_rates: dict[str, float] | None = None,
    ) -> None:
        self._financial_data = financial_data
        self._peer_data = peer_data
        self._macro_rates = macro_rates

    @property
    def category(self) -> str:
        return "valuation"

    @property
    def supports_crypto(self) -> bool:
        return True  # Lightweight proxies for crypto (D-13)

    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        # For stocks: DCF + peer comparison + scenario
        # For crypto: NVT ratio proxy
        # Score = margin of safety mapped to [-1, +1]
```

### Pattern 4: Bot Command Handler (read-only DB query)
**What:** Telegram command handlers that query DB for valuation/fundamental data and format responses.
**When to use:** For /valuation and /fundamentals commands.
**Note:** Bot handlers read from DB only -- they MUST NOT import from src/llm/ or src/pipeline/. Formatting functions live in src/report/formatter.py (shared layer).

### Anti-Patterns to Avoid
- **Importing pipeline modules from bot handlers:** Two-process boundary violation. Bot reads from DB, formatter in src/report/ is the shared layer.
- **Running LLM calls from bot handlers:** Bot process must not use LLM. Pre-compute valuation data during pipeline run, bot reads cached results.
- **Storing parsed data only in JSONB blob:** D-10 requires normalized `financial_data` table for queryable metrics. One row per metric per period, not a single JSON dump.
- **Daily IDX doc fetching:** D-03 locks weekly frequency. Financial reports update quarterly; daily fetching wastes bandwidth and risks rate limiting.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom PDF parser | pymupdf4llm `to_markdown()` | Handles tables, multi-column, OCR fallback automatically |
| Bahasa Indonesia financial term mapping | Manual regex extraction | GPT-4o-mini with structured prompt | Indonesian financial documents have varied formatting; LLM handles variation |
| Vision-based PDF reading | Custom OCR pipeline | litellm with vision model | Scanned PDFs need vision; litellm supports multimodal via same API |
| DCF terminal value | Custom perpetuity formula variants | Gordon Growth Model (`TV = FCF*(1+g)/(WACC-g)`) | Standard, well-understood, matches what analysts use |
| Telegram message splitting | Manual char counting | Existing `split_report()` in formatter.py | Already handles 4096-char limit with card-boundary splitting |

**Key insight:** The LLM does the heavy lifting for the hardest part (parsing Indonesian financial PDFs with varied formatting). The valuation math itself is straightforward formulas -- the challenge is getting clean input data, which pymupdf4llm + GPT solves.

## Common Pitfalls

### Pitfall 1: IDX API Rate Limiting / Blocking
**What goes wrong:** idx.co.id may block or rate-limit automated requests, returning 403 or empty responses.
**Why it happens:** IDX website uses Cloudflare or similar protection; no official public API documentation.
**How to avoid:** Add appropriate User-Agent header, implement exponential backoff with tenacity, respect weekly-only frequency (D-03), add random jitter between requests. Store downloaded PDFs locally so re-downloads are unnecessary.
**Warning signs:** HTTP 403 responses, empty JSON responses, CAPTCHA redirects.

### Pitfall 2: PDF Quality Variation
**What goes wrong:** Some IDX financial PDFs are scanned images, not text-based. pymupdf4llm extracts little or no text.
**Why it happens:** Older reports or smaller companies may scan paper reports rather than generating PDFs digitally.
**How to avoid:** Check extracted text length/quality. If text is too short (<500 chars for a financial report), trigger Vision LLM fallback per D-07. Log which PDFs required vision fallback for monitoring.
**Warning signs:** Very short extracted text, garbled characters, no numeric content in output.

### Pitfall 3: LLM Extraction Inconsistency
**What goes wrong:** GPT returns different field names, missing fields, or incorrectly parsed numbers across different reports.
**Why it happens:** Financial report formatting varies by company. Numbers may include Indonesian formatting (dots as thousands separators, commas as decimals).
**How to avoid:** Use JSON mode (`response_format={"type": "json_object"}`), provide explicit field schema in system prompt, validate output against expected field set, implement cross-validation with yfinance (D-09).
**Warning signs:** JSON parse errors, missing required fields, values off by orders of magnitude vs. yfinance.

### Pitfall 4: DCF Sensitivity to Growth Rate Assumptions
**What goes wrong:** Small changes in growth rate or discount rate produce wildly different fair values.
**Why it happens:** DCF terminal value dominates total value; it's exponentially sensitive to (WACC - g) spread.
**How to avoid:** Cap growth rate at GDP growth (D-11), use scenario analysis with bull/base/bear ranges (D-14), always show margin of safety as a range rather than point estimate, clearly label assumptions.
**Warning signs:** Fair value more than 3x or less than 0.3x current price without clear justification.

### Pitfall 5: Two-Process Boundary Violation
**What goes wrong:** Bot handler imports ValuationEngine or LLM modules, breaking the memory constraint.
**Why it happens:** Tempting to compute valuations on-demand in the bot process.
**How to avoid:** Pre-compute valuation results during pipeline run, store in DB (valuation signal in signals table + financial_data table). Bot handlers only read from DB and format via src/report/formatter.py.
**Warning signs:** Bot process memory exceeding 192MB limit, import errors in bot process.

### Pitfall 6: Indonesian Number Formatting
**What goes wrong:** "1.234.567" is parsed as 1.234567 instead of 1,234,567. Revenue in millions vs billions confusion.
**Why it happens:** Indonesian uses dots as thousands separators (opposite of English convention). Financial reports often use "dalam jutaan rupiah" (in millions of rupiah) or "dalam miliar rupiah" (in billions).
**How to avoid:** Include explicit instructions in LLM prompt about Indonesian number formatting. Prompt should specify: "Numbers in Indonesian PDFs use dots as thousands separators. Convert all values to full numbers (not millions/billions). Return values in IDR." Cross-validate against yfinance (D-09).
**Warning signs:** Values differing from yfinance by exactly 1000x or 1000000x.

## Code Examples

### IDX API Request Pattern
```python
# Source: Verified from open-source idx-scraper (github.com/tegardp/idx-scraper)
import httpx

IDX_REPORT_URL = (
    "https://idx.co.id/umbraco/Surface/ListedCompany/GetFinancialReport"
)

async def _query_idx_reports(
    client: httpx.AsyncClient, code: str, year: int, periode: str
) -> list[dict]:
    """Query IDX API for financial report listings."""
    params = {
        "indexFrom": "0",
        "pageSize": "10",
        "year": str(year),
        "reportType": "rdf",
        "periode": periode,  # "tw1", "tw2", "tw3", "tahunan"
        "kodeEmiten": code,
    }
    resp = await client.get(
        IDX_REPORT_URL,
        params=params,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    # Returns list of report entries with Attachments containing File_Path
    return data.get("Results", [])
```

### pymupdf4llm Text Extraction
```python
# Source: PyMuPDF4LLM GitHub README
import pymupdf4llm

def extract_pdf_to_markdown(file_path: str, max_pages: int = 20) -> str:
    """Extract PDF text as LLM-optimized markdown.

    pymupdf4llm.to_markdown is synchronous (CPU-bound) --
    must be called via run_in_executor in async context.
    """
    pages = list(range(min(max_pages, 100)))  # Limit pages for cost control
    md_text = pymupdf4llm.to_markdown(file_path, pages=pages)
    return md_text
```

### Financial Extraction LLM Prompt Pattern
```python
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
```

### DCF Calculation Pattern
```python
def _compute_dcf(
    fcf: float,           # Latest free cash flow (operating CF - capex)
    growth_rate: float,   # Revenue CAGR (capped at GDP growth ~5%)
    wacc: float,          # Weighted average cost of capital
    shares_outstanding: float,
    projection_years: int = 5,
    terminal_growth: float = 0.03,  # Long-term growth (inflation proxy)
) -> float:
    """Compute DCF fair value per share.

    Uses two-stage model: explicit projection + terminal value.
    """
    projected_fcf = []
    for year in range(1, projection_years + 1):
        projected = fcf * (1 + growth_rate) ** year
        discounted = projected / (1 + wacc) ** year
        projected_fcf.append(discounted)

    # Terminal value (Gordon Growth Model)
    terminal_fcf = fcf * (1 + growth_rate) ** projection_years * (1 + terminal_growth)
    terminal_value = terminal_fcf / (wacc - terminal_growth)
    discounted_terminal = terminal_value / (1 + wacc) ** projection_years

    enterprise_value = sum(projected_fcf) + discounted_terminal
    return enterprise_value / shares_outstanding if shares_outstanding > 0 else 0.0
```

### Margin of Safety Score Mapping
```python
def _margin_of_safety_to_score(margin: float) -> float:
    """Map margin of safety to engine score [-1, +1].

    margin > 0 means undervalued (positive score)
    margin < 0 means overvalued (negative score)

    Zones:
      margin > 0.40 -> +0.8 (deeply undervalued)
      margin > 0.20 -> +0.5
      margin > 0.05 -> +0.2
      margin > -0.05 -> 0.0 (fairly valued)
      margin > -0.20 -> -0.3
      margin > -0.40 -> -0.6
      margin <= -0.40 -> -0.8 (deeply overvalued)
    """
    if margin > 0.40:
        return 0.8
    if margin > 0.20:
        return 0.5
    if margin > 0.05:
        return 0.2
    if margin > -0.05:
        return 0.0
    if margin > -0.20:
        return -0.3
    if margin > -0.40:
        return -0.6
    return -0.8
```

### Database Schema Pattern
```python
# financial_docs table -- PDF metadata and parse tracking
class FinancialDoc(Base):
    __tablename__ = "financial_docs"
    __table_args__ = (
        UniqueConstraint("asset_id", "doc_type", "period", name="uq_financial_docs_asset_period"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "quarterly", "annual"
    period: Mapped[str] = mapped_column(String(10), nullable=False)    # "Q1-2025", "FY-2025"
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, parsed, failed
    downloaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

# financial_data table -- extracted metrics (one row per metric per period)
class FinancialData(Base):
    __tablename__ = "financial_data"
    __table_args__ = (
        UniqueConstraint("doc_id", "metric_name", name="uq_financial_data_doc_metric"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_id: Mapped[int] = mapped_column(Integer, ForeignKey("financial_docs.id"), nullable=False)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)  # "revenue", "net_profit", etc.
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # For text fields like outlook
    period: Mapped[str] = mapped_column(String(10), nullable=False)       # "Q3-2025"
    period_date: Mapped[date] = mapped_column(Date, nullable=False)       # Period end date for ordering
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pdfplumber / tabula-py for table extraction | pymupdf4llm for LLM-optimized markdown | 2024-2025 | Better LLM context, handles varied layouts |
| Manual regex parsing of financial data | LLM-based structured extraction | 2024 | Handles variation in report formatting |
| Single-model DCF | Multi-scenario with probability weights | Standard practice | More realistic range estimates |
| yfinance-only fundamentals | PDF-extracted + yfinance cross-validation | This phase | Deeper data, authoritative source |

**Deprecated/outdated:**
- pdf4llm: Old alias for pymupdf4llm, now redirects to pymupdf4llm package
- pdfplumber: Still maintained but lacks LLM-specific markdown output

## Open Questions

1. **IDX API Stability**
   - What we know: The API endpoint `idx.co.id/umbraco/Surface/ListedCompany/GetFinancialReport` is used by multiple open-source scrapers and appears stable
   - What's unclear: Whether IDX has added CAPTCHA, rate limiting, or IP blocking since these scrapers were last updated. The website returned 403 during this research session.
   - Recommendation: Implement robust error handling with tenacity retry + exponential backoff. On persistent failure, fall back to yfinance fundamentals (D-05). Test against live API during implementation.

2. **Shares Outstanding Source**
   - What we know: DCF requires shares outstanding to convert enterprise value to per-share fair value
   - What's unclear: Whether to extract from PDF or use yfinance `.info["sharesOutstanding"]`
   - Recommendation: Use yfinance as primary source for shares outstanding (already fetched in fundamental_fetcher.py), fall back to PDF extraction if needed. Add `shares_outstanding` field to StockFundamental model if not already present.

3. **Crypto NVT Data Source**
   - What we know: blockchain.com provides free NVT chart data; CoinGecko provides market cap; DeFiLlama provides TVL
   - What's unclear: Whether blockchain.com has a free API for NVT, or if calculation must be done from raw on-chain data
   - Recommendation: For Phase 9, use a simple calculation: NVT = market_cap / estimated_daily_volume. CoinGecko API already provides both. Mark as "proxy" quality. Phase 10 on-chain engine will provide proper NVT.

4. **Sector Classification for Peer Groups**
   - What we know: IDX classifies stocks by sector (Banking, Telco, Consumer, etc.)
   - What's unclear: Whether sector metadata is available via the IDX API or needs manual mapping
   - Recommendation: Start with a hardcoded `IDX_SECTOR_MAP` dict (only 3-6 stocks in watchlist initially). Expand to API-based lookup if watchlist grows significantly.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio (auto mode) |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_engines/test_valuation.py tests/test_data/test_idx_doc_fetcher.py tests/test_llm/test_doc_parser.py -x` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IDXD-01 | IDX API query + PDF download | unit (mock httpx) | `pytest tests/test_data/test_idx_doc_fetcher.py::TestFetchIdxDocs -x` | Wave 0 |
| IDXD-02 | pymupdf4llm extraction + LLM parsing | unit (mock LLM) | `pytest tests/test_llm/test_doc_parser.py::TestParseFinancialDoc -x` | Wave 0 |
| IDXD-03 | Field extraction validation | unit | `pytest tests/test_llm/test_doc_parser.py::TestExtractFields -x` | Wave 0 |
| ENGN-15 | ValuationEngine analyze() returns valid Signal | unit | `pytest tests/test_engines/test_valuation.py::TestValuationEngine -x` | Wave 0 |
| VALN-01 | DCF calculation correctness | unit | `pytest tests/test_engines/test_valuation.py::TestDCF -x` | Wave 0 |
| VALN-02 | Peer comparison ranking | unit | `pytest tests/test_engines/test_valuation.py::TestPeerComparison -x` | Wave 0 |
| VALN-03 | Crypto NVT proxy returns Signal | unit | `pytest tests/test_engines/test_valuation.py::TestCryptoProxy -x` | Wave 0 |
| VALN-04 | Scenario analysis bull/base/bear | unit | `pytest tests/test_engines/test_valuation.py::TestScenarioAnalysis -x` | Wave 0 |
| VALN-05 | QoQ ratio change detection | unit | `pytest tests/test_engines/test_valuation.py::TestQoQAlerts -x` | Wave 0 |
| TBOT-09 | /valuation handler response | unit (mock DB) | `pytest tests/test_bot/test_valuation_handler.py -x` | Wave 0 |
| TBOT-13 | /fundamentals handler response | unit (mock DB) | `pytest tests/test_bot/test_fundamentals_handler.py -x` | Wave 0 |
| REPT-03 | Valuation summary formatting | unit | `pytest tests/test_report/test_formatter_valuation.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_engines/test_valuation.py tests/test_data/test_idx_doc_fetcher.py tests/test_llm/test_doc_parser.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_data/test_idx_doc_fetcher.py` -- covers IDXD-01
- [ ] `tests/test_llm/test_doc_parser.py` -- covers IDXD-02, IDXD-03
- [ ] `tests/test_engines/test_valuation.py` -- covers ENGN-15, VALN-01 through VALN-05
- [ ] `tests/test_bot/test_valuation_handler.py` -- covers TBOT-09
- [ ] `tests/test_bot/test_fundamentals_handler.py` -- covers TBOT-13
- [ ] `tests/test_report/test_formatter_valuation.py` -- covers REPT-03

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/engines/base.py`, `src/engines/fundamental.py`, `src/data/fundamental_fetcher.py`, `src/data/analyze.py` -- established patterns for engine + fetcher implementation
- `plan/ARCHITECTURE.md` -- IDX Financial Doc Parser Flow, database schema, LLM cost estimates
- PyMuPDF4LLM GitHub README -- API usage, `to_markdown()` function, page chunking
- IDX scraper (github.com/tegardp/idx-scraper) -- verified IDX API endpoint and parameter structure

### Secondary (MEDIUM confidence)
- idx.co.id API endpoint structure -- verified by multiple open-source scrapers, but site returned 403 during research (may need User-Agent/cookie handling)
- NVT ratio data sources -- CoinGecko provides market cap and volume; blockchain.com provides NVT charts; calculation is straightforward
- pymupdf4llm version 0.0.17+ -- latest from PyPI search results (March 2026)

### Tertiary (LOW confidence)
- IDX API rate limits -- no official documentation found; based on community usage patterns
- Specific attachment filtering keywords for financial reports -- from scraper source code, may need adjustment

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pymupdf4llm is architecture decision, all other libs already in project
- Architecture: HIGH - follows established BaseEngine, fetcher, and bot handler patterns exactly
- IDX API: MEDIUM - endpoint verified from multiple scrapers but site returned 403 during research
- Valuation methodology: HIGH - DCF/peer/scenario patterns are standard finance formulas
- Pitfalls: HIGH - based on codebase patterns and financial data processing experience

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (IDX API stability should be re-verified before implementation)
