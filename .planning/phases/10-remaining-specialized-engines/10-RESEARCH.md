# Phase 10: Remaining Specialized Engines - Research

**Researched:** 2026-03-25
**Domain:** ML/AI inference, on-chain crypto analytics, behavioral anomaly detection, alternative data, network correlation, fractal/wavelet signal processing
**Confidence:** HIGH

## Summary

Phase 10 builds 8 new engines (6 real, 2 stubs) to complete the 15-engine suite. The existing codebase has a well-defined BaseEngine ABC and 7 working engines to follow as patterns. The core challenge is adding new dependencies (xgboost, onnxmltools, PyWavelets) while staying within the 1GB RAM budget, and wiring new data fetchers (DeFiLlama, GitHub API) into the existing ingest stage.

Key finding: onnxruntime 1.24.4 and scikit-learn 1.8.0 are already installed as transitive dependencies of pymupdf-layout and pmdarima respectively. Only xgboost, onnxmltools (for ONNX export), and PyWavelets need explicit installation. The Hurst exponent is already implemented in `quantitative.py` and can be reused by the emerging methods engine.

**Primary recommendation:** Build engines in dependency order -- stubs first (trivial), then OHLCV-only engines (behavioral, network, emerging), then data-backed engines (on-chain, GitHub), and finally the ML engine (most complex, needs training scripts + ONNX pipeline).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Price-derived features only for ML engine -- use existing OHLCV data to generate features (returns, volatility, RSI, MACD, volume ratios, lagged values). No external feature sources
- **D-02:** Offline train, ONNX deploy -- training scripts (CLI) generate ONNX models from historical data. Users retrain manually when performance degrades
- **D-03:** One model per asset class -- one XGBoost + one LSTM for stocks, one of each for crypto. 4 total ONNX models
- **D-04:** Include both inference code and training scripts as end-to-end deliverable
- **D-05:** Predict direction + magnitude -- next-day return direction and estimated magnitude. Score maps to -1/+1 range, confidence from model probability
- **D-06:** Weighted average ensemble -- 60% XGBoost, 40% LSTM. Confidence = min of both model confidences
- **D-07:** DeFiLlama for TVL (free, no auth) + CoinGecko for exchange flow data (free tier, already used). No paid APIs needed
- **D-08:** Exchange flow proxy for whale tracking -- track net exchange inflows/outflows
- **D-09:** On-chain engine focuses on TVL, exchange flows, whale activity. Leave NVT to ValuationEngine
- **D-10:** Support BTC + ETH + SOL -- the 3 most common watchlist cryptos
- **D-11:** TVL trend + ratio scoring -- track TVL 7-day and 30-day trends. Rising TVL = bullish, falling = bearish
- **D-12:** Daily fetch with pipeline -- on-chain data fetched during daily pipeline run
- **D-13:** Documented stub for Options Engine -- returns score=0/confidence=0 with reasoning
- **D-14:** Detect volume + price anomalies -- unusual volume spikes (>2 std dev), price gap anomalies, volume/price divergence
- **D-15:** GitHub activity only for crypto -- track commit frequency, contributor count, repo stars for major crypto projects
- **D-16:** Rolling correlation matrix -- compute rolling 30-day pairwise correlations across all watchlist assets
- **D-17:** Documented stub for Game Theory Order Book Engine -- returns score=0/confidence=0 with reasoning
- **D-18:** Fractal dimension (Hurst exponent) for trend/mean-reversion detection + wavelet decomposition for multi-scale trend analysis
- **D-19:** Extend existing ingest stage -- add on-chain and GitHub fetchers as sub-steps
- **D-20:** 2-3 new tables: on_chain_data, github_activity, ml_predictions
- **D-21:** One Alembic migration per table
- **D-22:** Lazy load ONNX models -- load only during ML engine's analyze(), release after
- **D-23:** Same Settings pattern as Phase 8 -- optional with graceful degradation
- **D-24:** All 15 engines appear in /scorecard

### Claude's Discretion
- XGBoost feature engineering specifics (which lagged features, window sizes)
- LSTM architecture (layers, hidden size, sequence length)
- Training script CLI interface and hyperparameter defaults
- DeFiLlama and CoinGecko endpoint selection and parsing
- GitHub repo mapping (which repos represent which crypto projects)
- Volume anomaly detection thresholds and scoring weights
- Correlation matrix computation method and regime change thresholds
- Hurst exponent and wavelet implementation details (library choice: pywt vs scipy)
- On-chain and GitHub data table column schemas and indexes
- How to wire 8 new engines into _get_engines_for_asset() in analyze.py
- Error handling and retry logic for new API calls

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENGN-04 | ML/AI engine (XGBoost, LSTM via ONNX, ensemble) | xgboost + onnxmltools for training/export, onnxruntime (already installed) for inference. D-01 through D-06 define the architecture |
| ENGN-06 | On-chain engine for crypto (TVL, whale tracking, exchange flows, NVT) | DeFiLlama free API for TVL (`/api/v2/historicalChainTvl/{chain}`), CoinGecko for exchange flow proxy. NVT stays in ValuationEngine per D-09 |
| ENGN-07 | Options engine (put/call ratio, max pain) -- limited scope | Stub engine per D-13, returns score=0/confidence=0 |
| ENGN-08 | Behavioral engine (volume anomaly, herding detection) | OHLCV-only, uses numpy/pandas for statistical anomaly detection per D-14 |
| ENGN-10 | Alternative data engine (GitHub activity) for crypto | GitHub REST API v3 for repo stats, optional GITHUB_TOKEN for rate limits |
| ENGN-11 | Network/graph engine (correlation analysis between assets) | Rolling correlation matrix from existing price data per D-16 |
| ENGN-13 | Game theory engine (order book imbalance, whale patterns) | Stub engine per D-17, returns score=0/confidence=0 |
| ENGN-14 | Emerging methods engine (fractal dimension, wavelet analysis) | PyWavelets for wavelet decomposition, existing _hurst_exponent in quantitative.py for fractal dimension reference |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python 3.13 runtime, strict mypy, ruff linting
- Two-process model: bot never imports pipeline modules; PostgreSQL is sole integration bus
- Sequential engine execution per asset, peak RAM under 1GB
- pydantic-settings for configuration, structlog for logging
- pytest with asyncio_mode="auto" for testing
- SQLAlchemy ORM with Alembic migrations
- All engines follow BaseEngine ABC contract: `analyze(asset_id, symbol, df) -> Signal`

## Standard Stack

### Core (New Dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| xgboost | 3.0+ | Gradient boosting for ML engine training | Industry standard for tabular ML, direct ONNX export support |
| onnxmltools | 1.12+ | Convert XGBoost models to ONNX format | Official converter for XGBoost to ONNX, works with skl2onnx |
| PyWavelets (pywt) | 1.8+ | Wavelet decomposition for emerging methods engine | De facto Python wavelet library, pure numpy backend |
| torch | 2.5+ | LSTM training only (not inference) | Standard for LSTM training; inference via ONNX Runtime |

### Already Available (Transitive Dependencies)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| onnxruntime | 1.24.4 | ONNX model inference for ML engine | Already installed (via pymupdf-layout) |
| scikit-learn | 1.8.0 | Feature scaling, train/test split for ML training | Already installed (via pmdarima) |
| scipy | 1.17.1 | Statistical functions for anomaly detection | Already installed (via scikit-learn) |
| numpy | 2.4.3 | Array operations across all engines | Already installed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyWavelets | scipy.signal.cwt | scipy only has CWT, pywt has DWT + MODWT which are better for discrete-level decomposition |
| torch for LSTM | tensorflow/keras | torch is lighter, better ONNX export, more active community |
| onnxmltools | xgboost built-in save_model | Built-in only saves XGBoost format, onnxmltools produces standard ONNX for runtime |

**Installation (production):**
```bash
uv add xgboost onnxmltools PyWavelets
```

**Installation (dev/training only -- torch is heavy, only needed for LSTM training):**
```bash
uv add --group dev torch --index-url https://download.pytorch.org/whl/cpu
```

**Version verification note:** onnxruntime 1.24.4, scikit-learn 1.8.0, scipy 1.17.1, and numpy 2.4.3 are already present in the venv as transitive dependencies. Do NOT add them as explicit dependencies to avoid version conflicts.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── engines/
│   ├── base.py              # BaseEngine ABC (existing)
│   ├── technical.py          # Existing
│   ├── quantitative.py       # Existing (has _hurst_exponent to reference)
│   ├── fundamental.py        # Existing
│   ├── macro.py              # Existing
│   ├── sentiment.py          # Existing
│   ├── event.py              # Existing
│   ├── valuation.py          # Existing
│   ├── ml_ai.py              # NEW: ENGN-04 ML/AI engine
│   ├── onchain.py            # NEW: ENGN-06 On-chain engine
│   ├── options.py            # NEW: ENGN-07 Options stub
│   ├── behavioral.py         # NEW: ENGN-08 Behavioral anomaly
│   ├── alternative.py        # NEW: ENGN-10 Alternative data (GitHub)
│   ├── network.py            # NEW: ENGN-11 Network/correlation
│   ├── game_theory.py        # NEW: ENGN-13 Game theory stub
│   └── emerging.py           # NEW: ENGN-14 Emerging methods
├── data/
│   ├── onchain_fetcher.py    # NEW: DeFiLlama + CoinGecko exchange flow fetcher
│   └── github_fetcher.py     # NEW: GitHub API repo stats fetcher
├── ml/
│   ├── features.py           # NEW: Feature engineering from OHLCV
│   ├── train_xgboost.py      # NEW: XGBoost training CLI
│   ├── train_lstm.py         # NEW: LSTM training CLI
│   └── models/               # NEW: Directory for saved ONNX model files
│       ├── xgboost_stock.onnx
│       ├── xgboost_crypto.onnx
│       ├── lstm_stock.onnx
│       └── lstm_crypto.onnx
└── db/
    └── migrations/
        ├── versions/xxx_add_on_chain_data.py    # NEW
        ├── versions/xxx_add_github_activity.py  # NEW
        └── versions/xxx_add_ml_predictions.py   # NEW
```

### Pattern 1: Stub Engine (Options, Game Theory)
**What:** Engine that returns score=0/confidence=0 with explanatory reasoning
**When to use:** Data source unavailable for current market/pipeline cadence
**Example:**
```python
# Source: CONTEXT.md D-13, D-17
class OptionsEngine(BaseEngine):
    """Options flow engine -- stub (D-13)."""

    @property
    def category(self) -> str:
        return "options"

    @property
    def supports_stocks(self) -> bool:
        return True

    @property
    def supports_crypto(self) -> bool:
        return False  # Only relevant for stocks with options

    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        return Signal(
            category="options",
            score=0.0,
            confidence=0.0,
            reasoning="Options flow data not available for IDX market",
            indicators={},
            data_quality={"stub": True, "todo": "Deribit for crypto options, IDX options when available"},
        )
```

### Pattern 2: OHLCV-Only Engine (Behavioral, Network, Emerging)
**What:** Engine that derives signals purely from existing price/volume data
**When to use:** Signal can be computed from the DataFrame passed to analyze()
**Example:** Follow TechnicalEngine pattern -- compute indicators, map to sub-scores, aggregate
```python
# Source: src/engines/technical.py pattern
class BehavioralEngine(BaseEngine):
    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning("behavioral_engine_error", error=str(exc))
            return Signal(category="behavioral", score=0.0, confidence=0.0, ...)
```

### Pattern 3: Constructor-Injected Data Engine (On-Chain, GitHub, ML)
**What:** Engine that receives pre-fetched data via constructor, not from df
**When to use:** Engine needs external data fetched during ingest stage
**Example:** Follow MacroEngine pattern -- `__init__(self, onchain_data=None)`
```python
# Source: src/engines/macro.py pattern
class OnChainEngine(BaseEngine):
    def __init__(self, onchain_data: dict[str, object] | None = None) -> None:
        self._data = onchain_data

    @property
    def supports_stocks(self) -> bool:
        return False  # Crypto only
```

### Pattern 4: Network Engine (Needs All Assets)
**What:** Engine that needs cross-asset correlation data (not just single asset df)
**When to use:** Signal depends on relationships between assets
**Example:** Correlation matrix pre-computed during analyze_stage, injected via constructor
```python
class NetworkEngine(BaseEngine):
    def __init__(self, correlation_data: dict[str, float] | None = None) -> None:
        self._correlations = correlation_data
```

### Pattern 5: ML Engine (Lazy ONNX Loading per D-22)
**What:** Engine that loads ONNX models on demand and releases after
**When to use:** Heavy model files that should not persist in memory
```python
class MLAIEngine(BaseEngine):
    def __init__(self, asset_type: str = "stock") -> None:
        self._asset_type = asset_type

    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            return Signal(category="ml_ai", score=0.0, confidence=0.0, ...)

    def _analyze_impl(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        import onnxruntime as ort  # Lazy import per D-22
        features = self._extract_features(df)
        # Load, run, release
        xgb_session = ort.InferenceSession(f"src/ml/models/xgboost_{self._asset_type}.onnx")
        xgb_result = xgb_session.run(None, {"input": features})
        del xgb_session  # Release memory immediately
        # ... similar for LSTM
```

### Anti-Patterns to Avoid
- **Engine fetching its own data:** Never. Fetchers run in ingest stage, engines read from DB or constructor args
- **Keeping ONNX sessions alive between assets:** Violates D-22 RAM budget. Load per analyze(), delete after
- **Importing torch at module level in engine code:** torch is for training only. Engine uses onnxruntime
- **Hard-coding model paths without fallback:** Missing model file must return score=0/confidence=0, not crash

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XGBoost to ONNX conversion | Custom serialization | onnxmltools.convert_xgboost() | Handles opset versions, type mapping, edge cases |
| Wavelet decomposition | Manual DWT implementation | PyWavelets pywt.wavedec() | Numerically stable, supports many wavelet families |
| ONNX inference | Custom model loading | onnxruntime.InferenceSession | Hardware-optimized, handles all ONNX opsets |
| Feature scaling for ML | Manual normalization | sklearn.preprocessing.StandardScaler | Handles NaN, serializes with model via ONNX pipeline |
| Hurst exponent | New implementation | Reference existing _hurst_exponent in quantitative.py | Already tested and working in the codebase |
| HTTP retry for DeFiLlama/GitHub | Custom retry loops | tenacity (already used) | Consistent with existing fetcher pattern |

## Common Pitfalls

### Pitfall 1: ONNX Runtime Memory Leak
**What goes wrong:** InferenceSession objects hold GPU/CPU allocators. If not explicitly deleted, they accumulate across assets.
**Why it happens:** Python GC doesn't deterministically free C++ resources.
**How to avoid:** Explicit `del session` after each `run()` call. Use context manager pattern if wrapping. Run gc.collect() after ML engine per existing pattern in analyze_stage.
**Warning signs:** Pipeline RAM grows with each asset processed.

### Pitfall 2: XGBoost ONNX Opset Mismatch
**What goes wrong:** Model exported with opset N, but onnxruntime expects opset M.
**Why it happens:** onnxmltools default opset may not match onnxruntime version.
**How to avoid:** Pin target_opset in conversion: `convert_xgboost(model, initial_types=..., target_opset=18)`. Test round-trip: export then immediately load with ort.
**Warning signs:** "Unsupported opset" error during InferenceSession creation.

### Pitfall 3: DeFiLlama Rate Limiting
**What goes wrong:** DeFiLlama free API returns 429 if called too frequently.
**Why it happens:** Multiple chain requests in rapid succession.
**How to avoid:** Add 0.5s delay between DeFiLlama calls (3 chains: BTC, ETH, SOL). Use tenacity with exponential backoff. Cache results in on_chain_data table.
**Warning signs:** HTTP 429 responses, empty TVL data.

### Pitfall 4: GitHub API Rate Limits Without Token
**What goes wrong:** 60 requests/hour limit exhausted quickly with multiple repos.
**Why it happens:** Unauthenticated GitHub API has aggressive rate limits.
**How to avoid:** Make GITHUB_TOKEN optional in Settings (D-23). Without token: fetch only 3 repos (one per crypto). With token: 5000/hour, no concern. Always check X-RateLimit-Remaining header.
**Warning signs:** HTTP 403 with "rate limit exceeded" message.

### Pitfall 5: Feature/Target Leakage in ML Training
**What goes wrong:** Model appears accurate in training but fails in production.
**Why it happens:** Features computed using future data (e.g., rolling window includes target day).
**How to avoid:** Strict temporal split: train on data up to T-1, features computed only from data available at prediction time. Shift all features by 1 day.
**Warning signs:** Training accuracy >> 90% for price prediction (unrealistic).

### Pitfall 6: Correlation Matrix Singularity
**What goes wrong:** Rolling correlation produces NaN when an asset has zero variance in the window.
**Why it happens:** Asset didn't trade (holiday, halt) or has constant price over 30 days.
**How to avoid:** Check for zero variance before computing correlation. Fill NaN correlations with 0.0. Log warning.
**Warning signs:** NaN values in correlation output, engine returning NaN score.

### Pitfall 7: Missing ONNX Model Files on First Run
**What goes wrong:** Pipeline crashes because model files don't exist yet.
**Why it happens:** Training hasn't been run yet, or models directory not included in deployment.
**How to avoid:** ML engine checks for model file existence. If missing, returns score=0/confidence=0 with reasoning "Model not trained yet. Run training CLI to generate ONNX models." Never crash.
**Warning signs:** FileNotFoundError in ML engine.

## Code Examples

### DeFiLlama TVL Fetch
```python
# Source: DeFiLlama API docs (https://api-docs.defillama.com)
import httpx

DEFILLAMA_BASE = "https://api.llama.fi"

CHAIN_MAP = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
}

async def fetch_tvl_history(symbol: str, days: int = 30) -> list[dict]:
    """Fetch historical TVL for a chain from DeFiLlama."""
    chain = CHAIN_MAP.get(symbol)
    if not chain:
        return []
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{DEFILLAMA_BASE}/v2/historicalChainTvl/{chain}")
        resp.raise_for_status()
        data = resp.json()  # [{"date": unix_ts, "tvl": float}, ...]
        # Return last N days
        return data[-days:] if len(data) > days else data
```

### XGBoost Feature Engineering from OHLCV
```python
# Source: D-01 price-derived features
import numpy as np
import pandas as pd

def extract_features(df: pd.DataFrame, lookback: int = 60) -> np.ndarray:
    """Extract ML features from OHLCV DataFrame.

    Returns array of shape (1, n_features) for single-day prediction.
    """
    close = df["close"]
    volume = df["volume"]

    features = {}
    # Returns at multiple horizons
    for d in [1, 3, 5, 10, 20]:
        features[f"return_{d}d"] = float(close.iloc[-1] / close.iloc[-1-d] - 1)

    # Volatility
    log_returns = np.log(close / close.shift(1)).dropna()
    for w in [5, 10, 20]:
        features[f"volatility_{w}d"] = float(log_returns.iloc[-w:].std())

    # RSI (simplified)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    features["rsi_14"] = float(100 - (100 / (1 + rs.iloc[-1])))

    # Volume ratio
    features["volume_ratio_20d"] = float(volume.iloc[-1] / volume.iloc[-20:].mean())

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    features["macd"] = float(ema12.iloc[-1] - ema26.iloc[-1])

    # Lagged features
    for lag in [1, 2, 3, 5]:
        features[f"close_lag_{lag}"] = float(close.iloc[-1] / close.iloc[-1-lag] - 1)

    return np.array([list(features.values())], dtype=np.float32)
```

### ONNX Model Lazy Loading Pattern
```python
# Source: D-22 lazy load pattern
import os
import onnxruntime as ort

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "ml", "models")

def _run_onnx_inference(model_name: str, features: np.ndarray) -> tuple[float, float] | None:
    """Load ONNX model, run inference, return (prediction, probability).

    Returns None if model file doesn't exist.
    """
    model_path = os.path.join(MODEL_DIR, f"{model_name}.onnx")
    if not os.path.exists(model_path):
        return None

    session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    try:
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: features})
        prediction = float(outputs[0][0])  # Predicted return
        probability = float(outputs[1][0][1]) if len(outputs) > 1 else 0.5  # Probability
        return prediction, probability
    finally:
        del session  # Explicit release per D-22
```

### Volume Anomaly Detection
```python
# Source: D-14 behavioral anomaly
def detect_volume_anomaly(df: pd.DataFrame, std_threshold: float = 2.0) -> dict:
    """Detect unusual volume spikes and price/volume divergence."""
    volume = df["volume"]
    close = df["close"]

    vol_mean = volume.rolling(20).mean()
    vol_std = volume.rolling(20).std()

    latest_vol = volume.iloc[-1]
    z_score = (latest_vol - vol_mean.iloc[-1]) / vol_std.iloc[-1] if vol_std.iloc[-1] > 0 else 0.0

    # Volume spike detection
    is_spike = abs(z_score) > std_threshold

    # Price/volume divergence: price rising but volume falling (or vice versa)
    price_change_5d = (close.iloc[-1] / close.iloc[-6] - 1) if len(close) > 5 else 0.0
    vol_change_5d = (volume.iloc[-5:].mean() / volume.iloc[-10:-5].mean() - 1) if len(volume) > 10 else 0.0
    divergence = (price_change_5d > 0 and vol_change_5d < -0.2) or (price_change_5d < 0 and vol_change_5d > 0.2)

    return {
        "volume_z_score": float(z_score),
        "is_spike": is_spike,
        "divergence": divergence,
        "price_change_5d": float(price_change_5d),
        "vol_change_5d": float(vol_change_5d),
    }
```

### GitHub Repo Stats Fetch
```python
# Source: D-15 GitHub activity, GitHub REST API v3
CRYPTO_REPOS = {
    "BTC": "bitcoin/bitcoin",
    "ETH": "ethereum/go-ethereum",
    "SOL": "solana-labs/solana",
}

async def fetch_github_activity(symbol: str, token: str | None = None) -> dict | None:
    """Fetch GitHub repo activity metrics."""
    repo = CRYPTO_REPOS.get(symbol)
    if not repo:
        return None

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"https://api.github.com/repos/{repo}", headers=headers)
        if resp.status_code != 200:
            return None
        data = resp.json()

        # Get recent commit activity
        commits_resp = await client.get(
            f"https://api.github.com/repos/{repo}/stats/commit_activity",
            headers=headers,
        )
        weekly_commits = 0
        if commits_resp.status_code == 200:
            activity = commits_resp.json()
            if activity and len(activity) > 0:
                weekly_commits = activity[-1].get("total", 0)

        return {
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "weekly_commits": weekly_commits,
            "updated_at": data.get("pushed_at"),
        }
```

## Database Schema (New Tables)

### on_chain_data
```python
class OnChainData(Base):
    __tablename__ = "on_chain_data"
    __table_args__ = (UniqueConstraint("asset_id", "date", "metric", name="uq_onchain_asset_date_metric"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    metric: Mapped[str] = mapped_column(String(30), nullable=False)  # "tvl", "exchange_inflow", "exchange_outflow"
    value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # "defillama", "coingecko"
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### github_activity
```python
class GitHubActivity(Base):
    __tablename__ = "github_activity"
    __table_args__ = (UniqueConstraint("asset_id", "date", name="uq_github_activity_asset_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    repo: Mapped[str] = mapped_column(String(100), nullable=False)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    weekly_commits: Mapped[int] = mapped_column(Integer, default=0)
    contributors: Mapped[int] = mapped_column(Integer, default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### ml_predictions
```python
class MLPrediction(Base):
    __tablename__ = "ml_predictions"
    __table_args__ = (UniqueConstraint("asset_id", "date", name="uq_ml_predictions_asset_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    xgboost_pred: Mapped[float | None] = mapped_column(Float, nullable=True)
    xgboost_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    lstm_pred: Mapped[float | None] = mapped_column(Float, nullable=True)
    lstm_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    ensemble_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    features_hash: Mapped[str | None] = mapped_column(String(32), nullable=True)  # For cache invalidation
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| XGBoost native format | ONNX Runtime inference | 2023+ | Unified runtime for all ML models, CPU-optimized |
| Standalone wavelet libs | PyWavelets (pywt) | Stable since 2020 | Standard library, no alternatives needed |
| Direct API calls per asset | Batched fetcher + DB cache | Established pattern | Prevents rate limiting, enables offline engine execution |

## Open Questions

1. **CoinGecko Exchange Flow Data Availability**
   - What we know: CoinGecko has exchange data, but specific inflow/outflow endpoints may require Pro API
   - What's unclear: Whether free tier returns sufficient exchange flow data for whale tracking proxy
   - Recommendation: Try free tier first (`/exchanges/{id}/volume_chart`), fall back to TVL-only scoring if exchange flow unavailable. Engine still produces valid signals from TVL alone

2. **LSTM Training Data Volume**
   - What we know: We have ~2 years of OHLCV data (from auto-backfill)
   - What's unclear: Whether 500 trading days is enough for LSTM to learn meaningful patterns
   - Recommendation: Use 60-day sequence length with 500+ days of history. If model doesn't converge, XGBoost alone (weight 100%) is a valid fallback

3. **torch as Production Dependency**
   - What we know: torch is ~2GB installed, only needed for training (not inference)
   - What's unclear: Whether to include torch in main deps or dev-only
   - Recommendation: Put torch in dev dependency group only. Training scripts are CLI tools run manually. Production pipeline only needs onnxruntime (already installed)

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| onnxruntime | ML engine inference | Yes | 1.24.4 | -- |
| scikit-learn | ML feature scaling | Yes | 1.8.0 | -- |
| scipy | Anomaly detection stats | Yes | 1.17.1 | -- |
| numpy | All engines | Yes | 2.4.3 | -- |
| xgboost | ML engine training | No | -- | Must install: `uv add xgboost` |
| onnxmltools | XGBoost ONNX export | No | -- | Must install: `uv add onnxmltools` |
| PyWavelets | Emerging methods engine | No | -- | Must install: `uv add PyWavelets` |
| torch | LSTM training only | No | -- | Install as dev dep only |
| DeFiLlama API | On-chain engine | Yes (free) | -- | No auth needed |
| GitHub API | Alternative data engine | Yes (free) | -- | 60 req/hr without token, 5000 with |

**Missing dependencies with no fallback:**
- xgboost, onnxmltools, PyWavelets must be installed before implementation

**Missing dependencies with fallback:**
- torch (LSTM training): Can be deferred; XGBoost-only ML engine is functional without LSTM

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_engines/ -x -q` |
| Full suite command | `pytest` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENGN-04 | ML engine produces valid signal with ONNX inference | unit | `pytest tests/test_engines/test_ml_ai.py -x` | Wave 0 |
| ENGN-04 | ML engine returns score=0 when model files missing | unit | `pytest tests/test_engines/test_ml_ai.py::TestMLAIEngineNoModel -x` | Wave 0 |
| ENGN-06 | On-chain engine scores BTC/ETH/SOL from TVL data | unit | `pytest tests/test_engines/test_onchain.py -x` | Wave 0 |
| ENGN-06 | On-chain engine returns score=0 for stocks | unit | `pytest tests/test_engines/test_onchain.py::TestOnChainStocks -x` | Wave 0 |
| ENGN-07 | Options stub returns score=0/confidence=0 | unit | `pytest tests/test_engines/test_options.py -x` | Wave 0 |
| ENGN-08 | Behavioral engine detects volume spike >2 std dev | unit | `pytest tests/test_engines/test_behavioral.py -x` | Wave 0 |
| ENGN-08 | Behavioral engine detects price/volume divergence | unit | `pytest tests/test_engines/test_behavioral.py::TestDivergence -x` | Wave 0 |
| ENGN-10 | Alternative data engine scores crypto from GitHub data | unit | `pytest tests/test_engines/test_alternative.py -x` | Wave 0 |
| ENGN-10 | Alternative data engine returns score=0 for stocks | unit | `pytest tests/test_engines/test_alternative.py::TestAltStocks -x` | Wave 0 |
| ENGN-11 | Network engine detects correlation regime changes | unit | `pytest tests/test_engines/test_network.py -x` | Wave 0 |
| ENGN-13 | Game theory stub returns score=0/confidence=0 | unit | `pytest tests/test_engines/test_game_theory.py -x` | Wave 0 |
| ENGN-14 | Emerging methods engine computes Hurst + wavelet signals | unit | `pytest tests/test_engines/test_emerging.py -x` | Wave 0 |
| SC-01 | All 15 engines appear in pipeline run signals | integration | `pytest tests/test_data/test_analyze.py -x` | Wave 0 |
| SC-02 | Pipeline peak RAM stays under 1GB | manual-only | Memory profiling with tracemalloc | N/A |
| SC-03 | Failed engine returns score=0, pipeline continues | unit | `pytest tests/test_engines/ -k "error or fail" -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_engines/ -x -q`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_engines/test_ml_ai.py` -- covers ENGN-04 (mock ONNX sessions)
- [ ] `tests/test_engines/test_onchain.py` -- covers ENGN-06
- [ ] `tests/test_engines/test_options.py` -- covers ENGN-07 (trivial)
- [ ] `tests/test_engines/test_behavioral.py` -- covers ENGN-08
- [ ] `tests/test_engines/test_alternative.py` -- covers ENGN-10
- [ ] `tests/test_engines/test_network.py` -- covers ENGN-11
- [ ] `tests/test_engines/test_game_theory.py` -- covers ENGN-13 (trivial)
- [ ] `tests/test_engines/test_emerging.py` -- covers ENGN-14
- [ ] `tests/test_data/test_onchain_fetcher.py` -- covers DeFiLlama/CoinGecko fetching
- [ ] `tests/test_data/test_github_fetcher.py` -- covers GitHub API fetching
- [ ] Framework install: `uv add xgboost onnxmltools PyWavelets` (production deps)

## Sources

### Primary (HIGH confidence)
- `src/engines/base.py` -- BaseEngine contract and Signal dataclass (read directly)
- `src/engines/technical.py` -- Reference OHLCV-only engine pattern (read directly)
- `src/engines/macro.py` -- Reference constructor-injected data engine pattern (read directly)
- `src/engines/quantitative.py` -- Existing _hurst_exponent implementation (read directly)
- `src/data/analyze.py` -- _get_engines_for_asset() registration and analyze_stage (read directly)
- `src/config.py` -- Settings class pattern for new API keys (read directly)
- `src/db/models.py` -- All existing ORM models and naming conventions (read directly)
- DeFiLlama API docs (https://api-docs.defillama.com) -- Free TVL endpoints confirmed

### Secondary (MEDIUM confidence)
- [sklearn-onnx XGBoost tutorial](https://onnx.ai/sklearn-onnx/auto_tutorial/plot_gexternal_xgboost.html) -- XGBoost ONNX conversion pattern
- GitHub REST API v3 docs -- Repo stats and commit activity endpoints

### Tertiary (LOW confidence)
- CoinGecko exchange flow endpoints -- May require Pro tier for detailed inflow/outflow. Needs validation during implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified (installed or available via pip), versions confirmed
- Architecture: HIGH -- follows 7 existing engine implementations exactly
- Pitfalls: HIGH -- based on direct codebase analysis and known ML deployment issues
- On-chain data sources: MEDIUM -- DeFiLlama confirmed free, CoinGecko exchange flow needs validation

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable domain, libraries well-established)
