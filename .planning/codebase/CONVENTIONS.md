# Coding Conventions

**Analysis Date:** 2026-03-24

## Naming Patterns

**Files:**
- `snake_case.py` for all modules: `idx_stocks.py`, `price_repo.py`, `ingest.py`
- Descriptive names matching module purpose: `validation.py`, `staleness.py`, `backfill.py`
- Private helpers prefixed with underscore in module scope: `_download_inner`, `_check_row`, `_read_backoff_state`

**Classes:**
- `PascalCase` for all classes: `IDXStockFetcher`, `CryptoFetcher`, `PipelineRunner`, `ValidationResult`
- Enums use `PascalCase` class name, `UPPER_CASE` members: `DataTier.CRITICAL`, `DataTier.IMPORTANT`

**Functions:**
- `snake_case` for all functions and methods: `validate_rows`, `upsert_prices`, `get_latest_date`
- Private module-level helpers prefixed with `_`: `_check_row`, `_download_with_retry`, `_should_weekly_refresh`
- `async` functions co-located with sync equivalents when needed (e.g., sync `_download_inner`, async `fetch`)

**Variables:**
- `snake_case` throughout: `asset_id`, `source_name`, `run_date`
- Module-level loggers always named `logger`: `logger = structlog.get_logger(__name__)`
- Exception: `src/llm/client.py` uses `log = structlog.get_logger()` (no `__name__`)
- Type aliases in `UPPER_CASE`: `StageFunc = Callable[...]`
- Constants in `UPPER_CASE`: `LLM_UNAVAILABLE`, `SOURCE_TIERS`, `SEED_ASSETS`

**Types:**
- `PascalCase` for all type names and dataclasses: `OHLCVRow`, `StageResult`, `LLMResult`

## Code Style

**Formatting:**
- Tool: ruff-format (Astral), version 0.15.7
- Configured via `.pre-commit-config.yaml` with `ruff-format` hook
- No separate `.prettierrc` or `pyproject.toml` `[tool.ruff.format]` section — defaults apply (88 char line length implied)

**Linting:**
- Tool: ruff, version 0.15.7 (same binary)
- Hook runs `ruff --fix` on commit
- `noqa` suppression used sparingly for legitimate cases:
  - `# noqa: E741` for short variable names in tuple unpacking (`o, h, l, c, v`)
  - `# noqa: PLW0603` for intentional `global` use in `reset_alert_collector`
  - `# noqa: ANN001` in migration `env.py` for missing type annotation on legacy callback

**Type Checking:**
- mypy in strict mode (`strict = true`) targeting Python 3.13
- pydantic mypy plugin enabled
- Overrides for untyped third-party packages: `yfinance`, `ccxt`, `asyncpg` → `ignore_missing_imports = true`

## Import Organization

**Order:**
1. `from __future__ import annotations` (when needed for forward references)
2. Standard library: `asyncio`, `dataclasses`, `datetime`, `math`, etc.
3. Third-party: `structlog`, `pandas`, `sqlalchemy`, `pydantic`, `tenacity`
4. Internal `src.*` imports

**`from __future__ import annotations`:**
- Used consistently across `src/data/` modules and `src/db/price_repo.py`
- Not used in `src/pipeline/runner.py`, `src/pipeline/tiers.py`, `src/llm/client.py`, `src/config.py`
- Add it to any new `src/data/` or `src/db/` file

**Path Aliases:**
- None — all internal imports use full `src.*` paths: `from src.data.base import OHLCVRow`

## Error Handling

**Strategy:** Tiered failure handling based on data source criticality.

**Patterns:**
- **CRITICAL sources** (e.g., `price_ohlcv`): raise `SourceCriticalError` to skip the asset
- **IMPORTANT sources** (e.g., `orderbook`): return `DegradedResult`, processing continues degraded
- **SUPPLEMENTARY sources** (e.g., `news_sentiment`): return `SkippedResult`, processing unaffected
- LLM calls never raise — return `LLM_UNAVAILABLE` sentinel on total failure (`src/llm/client.py`)
- Specific exception types caught in fetchers: `(KeyError, ValueError, TypeError)` for row conversion
- Broad `except Exception` used only at top-level pipeline boundaries (runner, LLM client)
- `tenacity` decorators (`@retry`) for transient network failures in `_download_inner`

**Raising custom exceptions:**
```python
# In src/pipeline/tiers.py
class SourceCriticalError(Exception):
    """Raised when a critical data source fails."""

# Usage in handle_source_failure:
raise SourceCriticalError(f"Critical source {source_name} failed: {error}")
```

## Logging

**Framework:** structlog (`structlog.get_logger(__name__)`)

**Setup:** `src/logging.py` — call `setup_logging(log_level, log_format)` at process start

**Patterns:**
- Module-level logger: `logger = structlog.get_logger(__name__)` at top of each module
- Contextual binding: `self._log = logger.bind(component="idx_fetcher")` in `__init__`
- Stage/run binding: `log = self._log.bind(stage=stage, run_date=str(run_date))` within methods
- Event names use `snake_case` strings: `"fetching_idx_stock"`, `"ohlcv_row_rejected"`, `"asset_failed"`
- Key-value pairs passed as keyword arguments: `logger.warning("event_name", key=value, key2=value2)`
- Log levels: `info` for normal flow, `warning` for recoverable issues, `error` for unrecoverable

**Production format:** JSON (`log_format="json"`)
**Development format:** ConsoleRenderer (`log_format="console"`)

## Comments

**Module docstrings:**
- Every module has a top-level docstring describing purpose and key behaviors
- Example: `src/data/validation.py` — "Rejects rows with null/NaN fields, invalid high/low relationships..."

**Function/method docstrings:**
- All public functions have Google-style docstrings with `Args:` and `Returns:` sections
- Private helpers (`_check_row`, `_download_inner`) also have docstrings
- Docstrings describe behavior, not implementation

**Inline comments:**
- Used for non-obvious logic: `# yfinance end date is EXCLUSIVE, so add 1 day`
- Used to label sections within larger functions: `# Check for existing run`, `# Get active assets`
- Avoid restating code

## Function Design

**Size:** Functions kept focused; complex orchestration broken into private helpers

**Parameters:**
- Prefer explicit keyword arguments for optional parameters with defaults
- `table: str = "price_history"` pattern used in `upsert_prices`, `get_latest_date`

**Return Values:**
- Dataclasses used for structured return values: `ValidationResult`, `StageResult`, `LLMResult`
- Frozen dataclasses (`@dataclass(frozen=True)`) for immutable results: `StageResult`, `LLMResult`, `DegradedResult`, `SkippedResult`
- `None` return for void async operations
- `list[T]` return for collections; empty list `[]` returned rather than `None` for empty results

## Module Design

**Exports:**
- No `__all__` definitions — rely on naming convention (`_private` prefix) for encapsulation
- Module-level singletons for shared state: `settings = Settings()`, `_alert_collector = AlertCollector()`

**Barrel Files:**
- `__init__.py` files are empty (used only for package declaration)
- No re-exports through `__init__.py`

**Abstract Base Classes:**
- Used for fetcher contract: `class BaseFetcher(ABC)` in `src/data/base.py`
- `@abstractmethod` for `source_name` property and `fetch` method

**Enums:**
- `StrEnum` used for string-valued enums: `class DataTier(StrEnum)` in `src/pipeline/tiers.py`

---

*Convention analysis: 2026-03-24*
