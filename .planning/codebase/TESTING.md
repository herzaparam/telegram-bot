# Testing Patterns

**Analysis Date:** 2026-03-24

## Test Framework

**Runner:**
- pytest 9.0.2+
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`

**Async support:**
- pytest-asyncio 1.3.0+
- `asyncio_mode = "auto"` — all `async def` test functions run automatically without explicit `@pytest.mark.asyncio` (though some tests still use the decorator for clarity)

**Assertion Library:**
- pytest built-in `assert`

**In-memory DB for integration tests:**
- aiosqlite (dev dependency) — used in `tests/test_pipeline/test_runner.py` with SQLAlchemy async engine

**Run Commands:**
```bash
pytest                     # Run all tests
pytest tests/test_data/    # Run specific module
pytest -x -vv              # Stop on first failure, verbose
pytest --tb=short          # Short tracebacks
```

## Test File Organization

**Location:** Separate `tests/` directory mirroring `src/` module structure

**Naming:**
- Test files: `test_<module>.py` (e.g., `test_validation.py` for `src/data/validation.py`)
- Test classes: `Test<FunctionOrClass>` (e.g., `TestValidateRows`, `TestLLMCompletion`)
- Test methods: `test_<behavior_description>` in plain English (e.g., `test_nan_open_rejected`, `test_all_success_means_completed`)

**Structure:**
```
tests/
├── __init__.py
├── conftest.py                    # Global fixtures (test_settings)
├── test_config.py
├── test_data/
│   ├── __init__.py
│   ├── conftest.py                # Data-layer shared fixtures
│   ├── test_crypto_fetcher.py
│   ├── test_idx_fetcher.py
│   ├── test_ingest.py
│   ├── test_migration.py
│   ├── test_price_repo.py
│   ├── test_staleness.py
│   └── test_validation.py
├── test_db/
│   ├── __init__.py
│   └── test_models.py
├── test_llm/
│   ├── __init__.py
│   └── test_client.py
└── test_pipeline/
    ├── __init__.py
    ├── test_runner.py
    └── test_tiers.py
```

## Test Structure

**Suite Organization:**
```python
class TestValidateRows:
    """Tests for validate_rows function."""

    def test_all_valid_rows_returned(
        self, five_ohlcv_rows: list[OHLCVRow]
    ) -> None:
        result = validate_rows(five_ohlcv_rows)
        assert len(result.valid) == 5
        assert len(result.rejected) == 0

    def test_nan_open_rejected(
        self, five_ohlcv_rows: list[OHLCVRow]
    ) -> None:
        five_ohlcv_rows[2] = OHLCVRow(...)
        result = validate_rows(five_ohlcv_rows)
        assert len(result.rejected) == 1
        assert "nan" in result.rejected[0][1].lower()
```

**Patterns:**
- All tests organized into classes, one class per function/component under test
- Each class has a docstring stating what it tests
- Each test method has a full return type annotation `-> None`
- One assertion group per test — tests are narrow and named for the specific behavior
- Test docstrings used when test name alone is insufficient (e.g., `"""fetch() returns list of OHLCVRow with source='yfinance'."""`)

**Setup:**
- `setup_method` used in `TestIDXStockFetcher` to instantiate the fetcher before each test
- No `setUp`/`tearDown` (unittest style) — prefer pytest fixtures and `setup_method`

**Teardown:**
- DB fixtures yield and clean up: `yield engine` → drop all tables → dispose engine

## Mocking

**Framework:** `unittest.mock` (`patch`, `AsyncMock`, `MagicMock`)

**Async mocking:**
```python
from unittest.mock import AsyncMock, MagicMock, patch

# Mock an async function
mock_session = AsyncMock()
fetcher_instance = AsyncMock()
fetcher_instance.fetch = AsyncMock(return_value=rows)

# Assert awaited
fetcher_instance.fetch.assert_awaited_once()
mock_sleep.assert_awaited_once_with(5.0)
```

**Patching by import path (context manager):**
```python
with (
    patch("src.data.ingest.IDXStockFetcher") as MockFetcher,
    patch("src.data.ingest.asyncpg.connect", return_value=mock_conn),
    patch("src.data.ingest.get_latest_date", return_value=datetime(...)),
    patch("src.data.ingest.validate_rows", return_value=ValidationResult(...)),
    patch("src.data.ingest.upsert_prices", return_value=3),
    patch("src.data.ingest.settings") as mock_settings,
):
    mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
    ...
```

**Module-level patching (decorator):**
```python
@patch("src.llm.client.litellm")
async def test_successful_completion(self, mock_litellm: MagicMock) -> None:
    mock_litellm.acompletion = AsyncMock(return_value=self._mock_response(...))
    result = await llm_completion(...)
    assert result.content == "hello world"
```

**Helper methods for mock construction:**
```python
def _mock_response(self, content: str = "test response", model: str = "gpt-4o-mini") -> MagicMock:
    """Create a mock litellm response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.model = model
    return response
```

**What to Mock:**
- External API calls (yfinance, ccxt, litellm, asyncpg)
- Database connections (`asyncpg.connect`)
- Settings object when testing with specific config values
- `asyncio.sleep` when testing backoff behavior

**What NOT to Mock:**
- SQLAlchemy ORM models (use in-memory aiosqlite instead)
- Internal pure functions (`validate_rows`, `_check_row`) — test them directly
- `structlog` — use `structlog.testing.capture_logs()` context manager instead

## Fixtures and Factories

**Shared data fixtures** in `tests/test_data/conftest.py`:
```python
@pytest.fixture()
def sample_ohlcv_rows() -> list[OHLCVRow]:
    """Three valid OHLCV rows for BBCA.JK (asset_id=1)."""
    base = datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc)
    return [OHLCVRow(time=base.replace(day=20), asset_id=1, ...)]

@pytest.fixture()
def five_ohlcv_rows(sample_ohlcv_rows: list[OHLCVRow]) -> list[OHLCVRow]:
    """Extends sample_ohlcv_rows with 2 more rows (5 total)."""
    ...

@pytest.fixture()
def mock_yfinance_df() -> pd.DataFrame:
    """pandas DataFrame mimicking yfinance daily download output."""
    ...

@pytest.fixture()
def mock_ccxt_ohlcv() -> list[list[float]]:
    """List of 5 OHLCV candles as returned by ccxt fetch_ohlcv."""
    ...
```

**DB integration fixtures** in `tests/test_pipeline/test_runner.py`:
```python
@pytest.fixture()
async def async_engine():
    """In-memory aiosqlite engine with schema created."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_sqlite_friendly_create_all)
    yield engine
    ...

@pytest.fixture()
async def seeded_session_factory(session_factory):
    """Seeds DB with 3 test assets (BTC, ETH, BBCA)."""
    ...

@pytest.fixture()
def runner(seeded_session_factory):
    """PipelineRunner bound to the seeded test DB."""
    return PipelineRunner(seeded_session_factory)
```

**Factory helpers** (module-level private functions in test files):
```python
def _make_asset(asset_type: str = "stock", asset_id: int = 1) -> MagicMock:
    """Create a mock Asset object with sensible defaults."""
    ...

def _make_rows(n: int = 3, source: str = "yfinance", asset_id: int = 1) -> list[OHLCVRow]:
    """Create n mock OHLCVRow objects."""
    ...
```

**Location:**
- Shared fixtures: `tests/conftest.py` (global), `tests/test_data/conftest.py` (data-layer)
- DB/runner fixtures: defined locally in `tests/test_pipeline/test_runner.py`
- Mock connection fixtures: defined locally in `tests/test_data/test_price_repo.py`

## Coverage

**Requirements:** Not enforced (no `--cov` in pytest config, no minimum threshold)

**View Coverage:**
```bash
pytest --cov=src --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- Pure function testing: `tests/test_data/test_validation.py`, `tests/test_data/test_staleness.py`, `tests/test_pipeline/test_tiers.py`
- All external dependencies mocked
- Synchronous tests use plain `def test_*`, async use `async def test_*`

**Integration Tests (in-memory):**
- `tests/test_pipeline/test_runner.py` — full `PipelineRunner` against aiosqlite
- JSONB columns swapped to JSON, UUID to CHAR(32) via `_sqlite_friendly_create_all` helper
- Tests verify database state after operations using separate sessions

**Model/Schema Tests:**
- `tests/test_db/test_models.py` — SQLAlchemy introspection tests, no DB connection needed
- Verify column sets, constraint presence, FK targets, nullable flags using `sqlalchemy.inspect`

**CLI Argument Tests:**
- `TestCLIArgParsing` in `test_runner.py` — import parser and call `parse_args([...])`
- Also `test_backfill_cli_parses_args` in `test_ingest.py`

## Common Patterns

**Async Testing:**
```python
# asyncio_mode = "auto" in pyproject.toml — no decorator needed
async def test_something(self) -> None:
    result = await some_async_func()
    assert result == expected
```

**Error Testing:**
```python
with pytest.raises(SourceCriticalError):
    await ingest_stage(mock_session, asset)

# With match pattern:
with pytest.raises(SourceCriticalError, match="Critical source price_ohlcv failed"):
    handle_source_failure("price_ohlcv", RuntimeError("API down"))

# Frozen dataclass mutation:
with pytest.raises(AttributeError):
    result.content = "changed"  # type: ignore[misc]
```

**Structlog capture:**
```python
with structlog.testing.capture_logs() as captured:
    validate_rows(five_ohlcv_rows, asset_symbol="BBCA.JK")

warning_logs = [e for e in captured if e.get("log_level") == "warning"]
assert len(warning_logs) >= 1
assert warning_logs[0]["event"] == "ohlcv_row_rejected"
assert warning_logs[0]["asset"] == "BBCA.JK"
```

**Tenacity retry override (disable waits in tests):**
```python
from tenacity import wait_none

original_wait = _download_inner.retry.wait
_download_inner.retry.wait = wait_none()
try:
    rows = await self.fetcher.fetch(...)
finally:
    _download_inner.retry.wait = original_wait
```

**Deferred import inside test body:**
```python
# Import after patching to pick up mocked modules
with patch("src.data.ingest.IDXStockFetcher") as MockFetcher:
    from src.data.ingest import ingest_stage
    await ingest_stage(mock_session, asset)
```

**Settings override using patch.dict:**
```python
with patch.dict("os.environ", {"DATABASE_URL": "postgresql+asyncpg://...", ...}, clear=True):
    from src.config import Settings
    s = Settings()
assert s.database_url == "..."
```

---

*Testing analysis: 2026-03-24*
