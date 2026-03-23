# Comprehensive Reference: All Known Methods for Stock & Cryptocurrency Price Prediction

---

## 1. FUNDAMENTAL ANALYSIS METHODS

### 1.1 Discounted Cash Flow (DCF)
- **Description**: Estimates intrinsic value by projecting future free cash flows and discounting them to present value using WACC.
- **Applies to**: Stocks
- **Formula**: `V₀ = Σ [FCFₜ / (1 + WACC)^t] + Terminal Value / (1 + WACC)^n`
- **Terminal Value**: `FCFₙ × (1 + g) / (WACC - g)` (Gordon Growth)

### 1.2 Dividend Discount Model (DDM)
- **Description**: Values a stock as the present value of all expected future dividends.
- **Applies to**: Stocks (dividend-paying)
- **Formula (Gordon Growth)**: `P₀ = D₁ / (r - g)`
- **Multi-stage DDM**: Uses different growth rates for different periods.

### 1.3 Residual Income Model (RIM)
- **Description**: Values equity as book value plus the present value of expected future residual income (earnings above cost of equity).
- **Applies to**: Stocks
- **Formula**: `V₀ = BV₀ + Σ [RIₜ / (1 + r)^t]` where `RIₜ = Earningsₜ - r × BVₜ₋₁`

### 1.4 Economic Value Added (EVA)
- **Description**: Measures value creation above the total cost of capital (debt + equity).
- **Applies to**: Stocks
- **Formula**: `EVA = NOPAT - (WACC × Total Capital)`

### 1.5 Price-to-Earnings Ratio (P/E)
- **Description**: Compares share price to earnings per share. Used for relative valuation.
- **Applies to**: Stocks
- **Formula**: `P/E = Price / EPS`
- **Variants**: Trailing P/E, Forward P/E, Shiller CAPE (cyclically adjusted)

### 1.6 Price-to-Book Ratio (P/B)
- **Description**: Compares market price to book value per share.
- **Applies to**: Stocks
- **Formula**: `P/B = Price / (Total Equity / Shares Outstanding)`

### 1.7 EV/EBITDA
- **Description**: Enterprise value relative to EBITDA; capital-structure-neutral valuation metric.
- **Applies to**: Stocks
- **Formula**: `EV/EBITDA = (Market Cap + Debt - Cash) / EBITDA`

### 1.8 Price-to-Sales (P/S)
- **Description**: Values a company relative to its revenue; useful for unprofitable companies.
- **Applies to**: Stocks
- **Formula**: `P/S = Price / Revenue per Share`

### 1.9 Price-to-Cash-Flow (P/CF)
- **Description**: Compares price to operating cash flow per share.
- **Applies to**: Stocks
- **Formula**: `P/CF = Price / (Operating Cash Flow / Shares)`

### 1.10 PEG Ratio
- **Description**: P/E ratio adjusted for earnings growth rate; identifies growth at a reasonable price.
- **Applies to**: Stocks
- **Formula**: `PEG = (P/E) / Annual EPS Growth Rate`

### 1.11 Free Cash Flow Yield
- **Description**: Inverse of price-to-FCF; measures cash return relative to market cap.
- **Applies to**: Stocks
- **Formula**: `FCF Yield = FCF per Share / Price`

### 1.12 Sum-of-the-Parts (SOTP) Valuation
- **Description**: Values each business segment separately and sums them; used for conglomerates.
- **Applies to**: Stocks
- **Formula**: Total value = Σ (individual segment values)

### 1.13 Asset-Based Valuation (NAV)
- **Description**: Values a company based on the fair market value of its net assets.
- **Applies to**: Stocks (especially REITs, holding companies)
- **Formula**: `NAV = Fair Value of Assets - Liabilities`

### 1.14 Comparable Company Analysis (Comps)
- **Description**: Values a company by comparing multiples (P/E, EV/EBITDA, etc.) to similar public companies.
- **Applies to**: Stocks

### 1.15 Precedent Transaction Analysis
- **Description**: Values a company based on multiples paid in prior M&A transactions of similar companies.
- **Applies to**: Stocks

### 1.16 Metcalfe's Law Valuation (Crypto)
- **Description**: Values a network as proportional to the square of the number of users/addresses.
- **Applies to**: Crypto
- **Formula**: `V ∝ n²` where n = number of active users/addresses

### 1.17 Token Velocity Model
- **Description**: Values a crypto token based on the equation of exchange from monetary economics.
- **Applies to**: Crypto
- **Formula**: `MV = PQ` → `M = PQ / V` (M = token value, V = velocity, P = price of resources, Q = quantity)

### 1.18 Cost of Production Model
- **Description**: Values crypto (especially Bitcoin) based on the marginal cost of mining (electricity, hardware).
- **Applies to**: Crypto (PoW)

---

## 2. TECHNICAL ANALYSIS METHODS

### 2A. Trend Indicators

#### 2.1 Moving Averages (SMA, EMA, WMA, DEMA, TEMA)
- **Description**: Smooths price data over a period. SMA = simple average; EMA = exponentially weighted; DEMA/TEMA = double/triple exponential for reduced lag.
- **Applies to**: Both
- **Formula (SMA)**: `SMA = Σ Priceₜ / n`
- **Formula (EMA)**: `EMAₜ = Priceₜ × k + EMAₜ₋₁ × (1-k)` where `k = 2/(n+1)`

#### 2.2 Moving Average Convergence Divergence (MACD)
- **Description**: Difference between 12-period and 26-period EMA; signal line is 9-period EMA of MACD.
- **Applies to**: Both
- **Formula**: `MACD = EMA(12) - EMA(26)`, `Signal = EMA(9) of MACD`, `Histogram = MACD - Signal`

#### 2.3 Average Directional Index (ADX)
- **Description**: Measures trend strength (not direction) on a 0-100 scale.
- **Applies to**: Both
- **Formula**: Based on smoothed +DI and -DI directional indicators.

#### 2.4 Parabolic SAR
- **Description**: Provides potential reversal points; dots above/below price indicate trend direction.
- **Applies to**: Both
- **Formula**: `SARₜ₊₁ = SARₜ + AF × (EP - SARₜ)` where AF = acceleration factor, EP = extreme point.

#### 2.5 Ichimoku Cloud (Ichimoku Kinko Hyo)
- **Description**: Five-line system showing support/resistance, trend direction, and momentum. Components: Tenkan-sen, Kijun-sen, Senkou Span A/B, Chikou Span.
- **Applies to**: Both

#### 2.6 Supertrend
- **Description**: Trend-following overlay based on ATR; flips above/below price to signal trend changes.
- **Applies to**: Both
- **Formula**: `Upper Band = (High + Low)/2 + Multiplier × ATR`, `Lower Band = (High + Low)/2 - Multiplier × ATR`

#### 2.7 VWAP (Volume-Weighted Average Price)
- **Description**: Average price weighted by volume; institutional benchmark for intraday trading.
- **Applies to**: Both
- **Formula**: `VWAP = Σ(Price × Volume) / Σ(Volume)`

### 2B. Momentum / Oscillator Indicators

#### 2.8 Relative Strength Index (RSI)
- **Description**: Momentum oscillator measuring speed and magnitude of price changes (0-100). Overbought >70, oversold <30.
- **Applies to**: Both
- **Formula**: `RSI = 100 - [100 / (1 + RS)]` where `RS = Avg Gain / Avg Loss` over n periods.

#### 2.9 Stochastic Oscillator (%K, %D)
- **Description**: Compares closing price to price range over a period.
- **Applies to**: Both
- **Formula**: `%K = (Close - Lowest Low) / (Highest High - Lowest Low) × 100`, `%D = SMA(%K, 3)`

#### 2.10 Commodity Channel Index (CCI)
- **Description**: Measures price deviation from statistical mean; identifies cyclical trends.
- **Applies to**: Both
- **Formula**: `CCI = (Typical Price - SMA) / (0.015 × Mean Deviation)`

#### 2.11 Williams %R
- **Description**: Momentum indicator similar to stochastic; ranges -100 to 0.
- **Applies to**: Both
- **Formula**: `%R = (Highest High - Close) / (Highest High - Lowest Low) × -100`

#### 2.12 Rate of Change (ROC) / Momentum
- **Description**: Measures percentage change in price over n periods.
- **Applies to**: Both
- **Formula**: `ROC = [(Closeₜ - Closeₜ₋ₙ) / Closeₜ₋ₙ] × 100`

#### 2.13 Money Flow Index (MFI)
- **Description**: Volume-weighted RSI; combines price and volume to measure buying/selling pressure.
- **Applies to**: Both
- **Formula**: `MFI = 100 - [100 / (1 + Money Flow Ratio)]`

#### 2.14 Ultimate Oscillator
- **Description**: Multi-timeframe momentum oscillator using weighted average of three periods (7, 14, 28).
- **Applies to**: Both

#### 2.15 Awesome Oscillator (AO)
- **Description**: Difference between 5-period and 34-period SMA of midpoint prices.
- **Applies to**: Both

#### 2.16 Detrended Price Oscillator (DPO)
- **Description**: Removes trend to identify cycles; shows overbought/oversold within cycles.
- **Applies to**: Both

#### 2.17 Know Sure Thing (KST)
- **Description**: Momentum oscillator based on smoothed rate of change across four timeframes.
- **Applies to**: Both

#### 2.18 True Strength Index (TSI)
- **Description**: Double-smoothed momentum oscillator showing trend direction and overbought/oversold.
- **Applies to**: Both

### 2C. Volatility Indicators

#### 2.19 Bollinger Bands
- **Description**: Middle band (SMA) with upper/lower bands at ±2 standard deviations; measures volatility.
- **Applies to**: Both
- **Formula**: `Upper = SMA(20) + 2σ`, `Lower = SMA(20) - 2σ`

#### 2.20 Average True Range (ATR)
- **Description**: Measures market volatility using the greatest of: current high-low, |high-previous close|, |low-previous close|.
- **Applies to**: Both
- **Formula**: `ATR = SMA of True Range over n periods`

#### 2.21 Keltner Channels
- **Description**: Volatility-based envelope around EMA using ATR (instead of standard deviation like Bollinger).
- **Applies to**: Both
- **Formula**: `Upper = EMA(20) + 2 × ATR(10)`, `Lower = EMA(20) - 2 × ATR(10)`

#### 2.22 Donchian Channels
- **Description**: Highest high and lowest low over n periods; used in Turtle Trading system.
- **Applies to**: Both

#### 2.23 Standard Deviation
- **Description**: Statistical measure of price dispersion around the mean.
- **Applies to**: Both

#### 2.24 Historical Volatility (HV) / Realized Volatility
- **Description**: Annualized standard deviation of log returns over a lookback period.
- **Applies to**: Both
- **Formula**: `HV = σ(log returns) × √252`

#### 2.25 Implied Volatility (IV)
- **Description**: Market's expectation of future volatility, derived from option prices via Black-Scholes inversion.
- **Applies to**: Stocks (primarily), Crypto (emerging)

#### 2.26 VIX (CBOE Volatility Index)
- **Description**: Measures 30-day expected volatility of S&P 500 from option prices; "fear gauge."
- **Applies to**: Stocks

### 2D. Volume Indicators

#### 2.27 On-Balance Volume (OBV)
- **Description**: Running total of volume; adds volume on up days, subtracts on down days.
- **Applies to**: Both
- **Formula**: `OBV = OBVₜ₋₁ ± Volumeₜ` (+ if close > prior close, - if close < prior close)

#### 2.28 Accumulation/Distribution Line (A/D)
- **Description**: Measures cumulative flow of money into and out of a security using close position within range.
- **Applies to**: Both
- **Formula**: `A/D = Prev A/D + [(Close - Low) - (High - Close)] / (High - Low) × Volume`

#### 2.29 Chaikin Money Flow (CMF)
- **Description**: Volume-weighted average of A/D over a period (typically 20).
- **Applies to**: Both

#### 2.30 Volume Rate of Change
- **Description**: Percentage change in volume over a specified period.
- **Applies to**: Both

#### 2.31 Klinger Oscillator
- **Description**: Volume-based oscillator comparing volume flowing in and out of a security.
- **Applies to**: Both

#### 2.32 Ease of Movement (EMV)
- **Description**: Relates price change to volume; shows how easily prices move.
- **Applies to**: Both

### 2E. Support/Resistance & Pivot Methods

#### 2.33 Fibonacci Retracement
- **Description**: Horizontal lines at key Fibonacci levels (23.6%, 38.2%, 50%, 61.8%, 78.6%) between swing high and low.
- **Applies to**: Both

#### 2.34 Fibonacci Extensions
- **Description**: Projects price targets beyond the original move using Fibonacci ratios (127.2%, 161.8%, 261.8%).
- **Applies to**: Both

#### 2.35 Pivot Points (Standard, Fibonacci, Camarilla, Woodie, DeMark)
- **Description**: Calculated support/resistance levels based on prior period's high, low, close.
- **Applies to**: Both
- **Formula (Standard)**: `Pivot = (H + L + C) / 3`, `R1 = 2P - L`, `S1 = 2P - H`

#### 2.36 Gann Fan / Gann Lines
- **Description**: Geometric angles drawn from price pivot points based on price-time relationships (1x1, 1x2, 2x1, etc.).
- **Applies to**: Both

#### 2.37 Andrew's Pitchfork
- **Description**: Three parallel lines based on three user-selected price points forming a median-line channel.
- **Applies to**: Both

### 2F. Chart Patterns

#### Reversal Patterns
- **2.38 Head and Shoulders / Inverse Head and Shoulders**: Three-peak pattern signaling trend reversal.
- **2.39 Double Top / Double Bottom**: Two tests of same resistance/support level.
- **2.40 Triple Top / Triple Bottom**: Three tests of the same level.
- **2.41 Rounding Bottom (Saucer)**: Gradual U-shaped reversal.
- **2.42 V-Bottom / V-Top**: Sharp reversal.
- **2.43 Bump and Run Reversal**: Lead-in trend, bump (steep acceleration), and reversal.

#### Continuation Patterns
- **2.44 Flags and Pennants**: Brief consolidation after sharp move; small rectangle (flag) or triangle (pennant).
- **2.45 Wedges (Rising/Falling)**: Converging trendlines sloping in same direction.
- **2.46 Rectangles**: Horizontal consolidation between parallel support/resistance.
- **2.47 Cup and Handle**: U-shaped cup followed by small pullback (handle).

#### Bilateral / Complex Patterns
- **2.48 Ascending / Descending / Symmetrical Triangles**: Converging trendlines.
- **2.49 Broadening Formations (Megaphone)**: Expanding trendlines showing increasing volatility.
- **2.50 Diamond Top / Bottom**: Head and shoulders variant with broadening then narrowing.

#### Candlestick Patterns
- **2.51 Doji** (indecision), **Hammer/Hanging Man** (reversal), **Engulfing** (bullish/bearish reversal), **Morning/Evening Star** (three-candle reversal), **Three White Soldiers / Three Black Crows** (strong trend), **Spinning Top** (indecision), **Marubozu** (strong conviction), **Harami** (inside bar), **Tweezer Tops/Bottoms**, **Dark Cloud Cover / Piercing Line**, **Shooting Star / Inverted Hammer**, **Abandoned Baby**, **Three Inside Up/Down**.
- **Applies to**: Both

### 2G. Other Technical Methods

#### 2.52 Elliott Wave Theory
- **Description**: Prices move in predictable 5-wave impulse + 3-wave corrective patterns driven by mass psychology.
- **Applies to**: Both

#### 2.53 Dow Theory
- **Description**: Market has three trends (primary, secondary, minor); confirmed by averages and volume.
- **Applies to**: Stocks (originally), Both (in practice)

#### 2.54 Wyckoff Method
- **Description**: Framework identifying accumulation/distribution phases through price, volume, and effort vs. result analysis.
- **Applies to**: Both

#### 2.55 Market Profile / Volume Profile
- **Description**: Organizes price and volume data by price level (TPO or volume at price) to identify value areas, POC (point of control), and high/low volume nodes.
- **Applies to**: Both

#### 2.56 Order Flow / Tape Reading / Footprint Charts
- **Description**: Analyzes bid/ask volume at each price level in real time to gauge buying/selling pressure.
- **Applies to**: Both

#### 2.57 Heikin Ashi
- **Description**: Modified candlestick using averaged values to smooth price action and filter noise.
- **Applies to**: Both

#### 2.58 Renko Charts
- **Description**: Bricks of fixed price movement; ignores time, focuses purely on price change.
- **Applies to**: Both

#### 2.59 Point and Figure Charts
- **Description**: Columns of X's (rising) and O's (falling) with no time axis; focuses on significant price moves.
- **Applies to**: Both

#### 2.60 Harmonic Patterns (Gartley, Bat, Butterfly, Crab, Shark, Cypher)
- **Description**: Geometric patterns using Fibonacci ratios to identify reversal zones (PRZ - Potential Reversal Zone).
- **Applies to**: Both

---

## 3. QUANTITATIVE / STATISTICAL METHODS

### 3.1 Capital Asset Pricing Model (CAPM)
- **Description**: Single-factor model relating expected return to systematic (market) risk.
- **Applies to**: Stocks
- **Formula**: `E(Rᵢ) = Rᶠ + βᵢ(E(Rₘ) - Rᶠ)`

### 3.2 Fama-French Three-Factor Model
- **Description**: Extends CAPM with size (SMB) and value (HML) factors.
- **Applies to**: Stocks
- **Formula**: `Rᵢ - Rᶠ = αᵢ + β₁(Rₘ - Rᶠ) + β₂(SMB) + β₃(HML) + εᵢ`

### 3.3 Fama-French Five-Factor Model
- **Description**: Adds profitability (RMW) and investment (CMA) factors to the three-factor model.
- **Applies to**: Stocks
- **Formula**: `Rᵢ - Rᶠ = αᵢ + β₁(Rₘ - Rᶠ) + β₂(SMB) + β₃(HML) + β₄(RMW) + β₅(CMA) + εᵢ`

### 3.4 Carhart Four-Factor Model
- **Description**: Three-factor model plus momentum factor (WML - Winners Minus Losers).
- **Applies to**: Stocks

### 3.5 Arbitrage Pricing Theory (APT)
- **Description**: Multi-factor model where expected return is a linear function of multiple macroeconomic factors; number and identity of factors not pre-specified.
- **Applies to**: Stocks, Both
- **Formula**: `E(Rᵢ) = Rᶠ + β₁λ₁ + β₂λ₂ + ... + βₖλₖ`

### 3.6 ARIMA (Autoregressive Integrated Moving Average)
- **Description**: Time series model combining autoregression, differencing, and moving average. Parameters (p,d,q).
- **Applies to**: Both
- **Formula**: `(1-Σφᵢ Lⁱ)(1-L)^d Xₜ = (1+Σθⱼ Lʲ)εₜ`

### 3.7 ARMA (Autoregressive Moving Average)
- **Description**: Stationary time series model combining AR and MA components.
- **Applies to**: Both

### 3.8 SARIMA (Seasonal ARIMA)
- **Description**: ARIMA extended with seasonal components (P,D,Q,s).
- **Applies to**: Both

### 3.9 ARIMAX / SARIMAX
- **Description**: ARIMA with exogenous variables (external regressors).
- **Applies to**: Both

### 3.10 VAR (Vector Autoregression)
- **Description**: Multivariate time series model where each variable is a linear function of past values of itself and other variables.
- **Applies to**: Both

### 3.11 VECM (Vector Error Correction Model)
- **Description**: VAR model with cointegration constraints for non-stationary but cointegrated series.
- **Applies to**: Both

### 3.12 GARCH (Generalized Autoregressive Conditional Heteroskedasticity)
- **Description**: Models time-varying volatility (volatility clustering). Variants: EGARCH, GJR-GARCH, TGARCH.
- **Applies to**: Both
- **Formula**: `σₜ² = ω + α₁εₜ₋₁² + β₁σₜ₋₁²`

### 3.13 Stochastic Volatility Models
- **Description**: Models volatility as a latent stochastic process (vs. deterministic in GARCH).
- **Applies to**: Both

### 3.14 Kalman Filter
- **Description**: Recursive algorithm estimating hidden state variables from noisy observations; used for dynamic factor models and trend extraction.
- **Applies to**: Both

### 3.15 Hidden Markov Models (HMM)
- **Description**: Models market as switching between hidden states (e.g., bull/bear/sideways) with state-dependent return distributions.
- **Applies to**: Both

### 3.16 Regime-Switching Models (Markov-Switching)
- **Description**: Allows model parameters to change across different market regimes with Markov transition probabilities.
- **Applies to**: Both

### 3.17 Cointegration-Based Pairs Trading
- **Description**: Identifies pairs of assets with long-run equilibrium relationship; trades mean-reversion of spread.
- **Applies to**: Both
- **Tests**: Engle-Granger, Johansen

### 3.18 Statistical Arbitrage (StatArb)
- **Description**: Portfolio of long/short positions exploiting statistical mispricings; beta-neutral, factor-neutral.
- **Applies to**: Both
- **Approaches**: Distance method, cointegration, copulas, PCA-based, Ornstein-Uhlenbeck mean-reversion.

### 3.19 Principal Component Analysis (PCA)
- **Description**: Dimensionality reduction extracting dominant factors from return covariance matrix.
- **Applies to**: Both

### 3.20 Monte Carlo Simulation
- **Description**: Generates thousands of random price paths using assumed distributions to estimate probabilities.
- **Applies to**: Both
- **Common process**: Geometric Brownian Motion (GBM): `dS = μSdt + σSdW`

### 3.21 Copula Models
- **Description**: Models dependency structure between assets separately from marginal distributions.
- **Applies to**: Both

### 3.22 Extreme Value Theory (EVT)
- **Description**: Models tail risk and rare events beyond normal distribution assumptions.
- **Applies to**: Both

### 3.23 Bayesian Methods
- **Description**: Updates probability estimates of parameters or models as new data arrives; includes Bayesian VAR, Bayesian structural time series.
- **Applies to**: Both

### 3.24 Ornstein-Uhlenbeck Process
- **Description**: Mean-reverting stochastic process; commonly used in pairs trading to model spread dynamics.
- **Applies to**: Both
- **Formula**: `dXₜ = θ(μ - Xₜ)dt + σdWₜ`

### 3.25 Hurst Exponent
- **Description**: Measures long-term memory / tendency of a time series (H>0.5: trending, H<0.5: mean-reverting, H=0.5: random walk).
- **Applies to**: Both
- **Formula**: `E[R(n)/S(n)] = Cnᴴ` (R/S analysis)

### 3.26 Exponential Smoothing (SES, Holt, Holt-Winters)
- **Description**: Forecasting methods that apply exponentially decreasing weights to past observations. Holt-Winters adds trend and seasonal components.
- **Applies to**: Both

### 3.27 Prophet (Facebook/Meta)
- **Description**: Additive regression model decomposing time series into trend, seasonality, and holidays.
- **Applies to**: Both

---

## 4. MACHINE LEARNING / AI METHODS

### 4A. Supervised Learning — Classical

#### 4.1 Linear Regression / Ridge / Lasso / ElasticNet
- **Description**: Predicts continuous price or return from features; regularization variants prevent overfitting.
- **Applies to**: Both

#### 4.2 Logistic Regression
- **Description**: Binary classification (up/down); outputs probability of price direction.
- **Applies to**: Both

#### 4.3 Support Vector Machines (SVM) / SVR
- **Description**: Finds optimal hyperplane for classification (SVM) or regression (SVR); effective in high-dimensional spaces.
- **Applies to**: Both

#### 4.4 Decision Trees
- **Description**: Recursive partitioning of feature space into regions with piecewise-constant predictions.
- **Applies to**: Both

#### 4.5 Random Forest
- **Description**: Ensemble of decorrelated decision trees; reduces variance via bagging + random feature selection.
- **Applies to**: Both

#### 4.6 Gradient Boosting (XGBoost, LightGBM, CatBoost)
- **Description**: Sequential ensemble where each tree corrects errors of prior trees; state-of-the-art for tabular data.
- **Applies to**: Both

#### 4.7 AdaBoost
- **Description**: Adaptive boosting; weights misclassified samples more heavily in each iteration.
- **Applies to**: Both

#### 4.8 K-Nearest Neighbors (KNN)
- **Description**: Predicts based on majority vote / average of k closest training examples.
- **Applies to**: Both

#### 4.9 Naive Bayes
- **Description**: Probabilistic classifier based on Bayes' theorem with independence assumptions; used for text-based signals.
- **Applies to**: Both

### 4B. Supervised Learning — Deep Learning

#### 4.10 Feedforward Neural Networks (MLP)
- **Description**: Multi-layer perceptron; universal function approximator for non-linear relationships.
- **Applies to**: Both

#### 4.11 Recurrent Neural Networks (RNN)
- **Description**: Neural networks with loops allowing information persistence; natural fit for sequential data.
- **Applies to**: Both

#### 4.12 Long Short-Term Memory (LSTM)
- **Description**: RNN variant with gating mechanisms (forget, input, output gates) solving vanishing gradient; captures long-term dependencies in time series.
- **Applies to**: Both

#### 4.13 Bidirectional LSTM (BiLSTM)
- **Description**: Processes sequence forward and backward; captures both past and future context.
- **Applies to**: Both

#### 4.14 Gated Recurrent Unit (GRU)
- **Description**: Simplified LSTM with fewer parameters (reset and update gates only).
- **Applies to**: Both

#### 4.15 Convolutional Neural Networks (CNN / 1D-CNN)
- **Description**: Applies convolutional filters to extract local patterns from time series or images (chart patterns).
- **Applies to**: Both

#### 4.16 CNN-LSTM Hybrid
- **Description**: CNN extracts spatial features, LSTM captures temporal dependencies; widely used architecture.
- **Applies to**: Both

#### 4.17 Transformer Models
- **Description**: Self-attention mechanism capturing long-range dependencies without recurrence; state-of-the-art for many sequence tasks.
- **Applies to**: Both
- **Variants**: Informer (long-sequence), Autoformer, PatchTST, iTransformer, Temporal Fusion Transformer (TFT)

#### 4.18 Attention Mechanisms
- **Description**: Learned weighting of input elements allowing models to focus on relevant time steps / features.
- **Applies to**: Both

#### 4.19 Temporal Convolutional Networks (TCN)
- **Description**: Dilated causal convolutions for long-range temporal modeling; parallelizable unlike RNNs.
- **Applies to**: Both

#### 4.20 Encoder-Decoder / Seq2Seq Models
- **Description**: Encodes input sequence to latent representation, then decodes to output sequence (multi-step forecasting).
- **Applies to**: Both

#### 4.21 Graph Neural Networks (GNN / GCN / GAT)
- **Description**: Processes graph-structured data (stock correlation networks, supply chains, crypto transaction graphs).
- **Applies to**: Both
- **Variants**: Relational GCN (RGCN), Graph Attention Network (GAT), Hypergraph Attention

#### 4.22 Variational Autoencoders (VAE)
- **Description**: Generative model learning latent representation; used for anomaly detection and regime identification.
- **Applies to**: Both

#### 4.23 Generative Adversarial Networks (GAN)
- **Description**: Generator creates synthetic price paths, discriminator evaluates; used for data augmentation and scenario generation.
- **Applies to**: Both

#### 4.24 Neural Ordinary Differential Equations (Neural ODE)
- **Description**: Continuous-depth models replacing discrete layers with differential equations; natural fit for continuous-time financial data.
- **Applies to**: Both

#### 4.25 N-BEATS (Neural Basis Expansion Analysis)
- **Description**: Pure deep learning architecture for time series; stack of fully connected layers with basis expansion.
- **Applies to**: Both

#### 4.26 DeepAR
- **Description**: Autoregressive RNN producing probabilistic (quantile) forecasts.
- **Applies to**: Both

#### 4.27 WaveNet
- **Description**: Dilated causal convolution architecture originally for audio; adapted for financial time series.
- **Applies to**: Both

### 4C. Unsupervised Learning

#### 4.28 K-Means / Hierarchical Clustering
- **Description**: Groups assets or market states by similarity; used for regime detection and portfolio construction.
- **Applies to**: Both

#### 4.29 DBSCAN
- **Description**: Density-based clustering identifying arbitrarily shaped clusters; useful for outlier/anomaly detection.
- **Applies to**: Both

#### 4.30 Autoencoders
- **Description**: Learns compressed representation of input; used for feature extraction, denoising, anomaly detection.
- **Applies to**: Both

#### 4.31 Self-Organizing Maps (SOM / Kohonen Maps)
- **Description**: Topology-preserving neural network mapping high-dimensional data to 2D; identifies market regimes and clusters.
- **Applies to**: Both

#### 4.32 Gaussian Mixture Models (GMM)
- **Description**: Soft clustering assuming data is generated from mixture of Gaussians; models regime probabilities.
- **Applies to**: Both

#### 4.33 t-SNE / UMAP
- **Description**: Dimensionality reduction for visualization; reveals structure in high-dimensional financial data.
- **Applies to**: Both

### 4D. Reinforcement Learning

#### 4.34 Q-Learning / Deep Q-Networks (DQN)
- **Description**: Agent learns optimal trading policy (buy/sell/hold) by maximizing cumulative reward.
- **Applies to**: Both

#### 4.35 Policy Gradient Methods (REINFORCE, A2C, A3C, PPO)
- **Description**: Directly optimizes the trading policy; PPO is stable and widely used.
- **Applies to**: Both

#### 4.36 Deep Deterministic Policy Gradient (DDPG) / TD3 / SAC
- **Description**: Actor-critic methods for continuous action spaces (e.g., position sizing).
- **Applies to**: Both

#### 4.37 Multi-Agent Reinforcement Learning (MARL)
- **Description**: Multiple agents simulate market participants; models emergent market dynamics.
- **Applies to**: Both

### 4E. Large Language Models (LLMs) & Foundation Models

#### 4.38 FinBERT / Financial BERT
- **Description**: BERT fine-tuned on financial text for sentiment classification and event extraction.
- **Applies to**: Both

#### 4.39 GPT-based Financial Models
- **Description**: Large language models analyzing news, filings, social media for price-relevant signals; few-shot learning for financial tasks.
- **Applies to**: Both

#### 4.40 LLM-Enhanced Feature Engineering
- **Description**: Uses LLMs to generate features from unstructured text (earnings call transcripts, SEC filings, tweets) as inputs to quantitative models.
- **Applies to**: Both

#### 4.41 Time Series Foundation Models (TimeGPT, Lag-Llama, Chronos)
- **Description**: Pre-trained on massive time series corpora; zero-shot or fine-tuned for financial forecasting.
- **Applies to**: Both

### 4F. Ensemble & Hybrid Methods

#### 4.42 Stacking
- **Description**: Meta-learner trained on outputs of multiple base models.
- **Applies to**: Both

#### 4.43 Blending
- **Description**: Simpler variant of stacking using holdout set instead of cross-validation.
- **Applies to**: Both

#### 4.44 Voting (Hard/Soft)
- **Description**: Aggregates predictions from multiple models via majority vote or weighted average.
- **Applies to**: Both

#### 4.45 Decomposition-Prediction-Reconstruction
- **Description**: Decomposes time series (EMD, VMD, wavelet), predicts each component separately, then reconstructs. Examples: EMD-LSTM, VMD-GRU, CEEMDAN-Transformer.
- **Applies to**: Both

---

## 5. SENTIMENT ANALYSIS METHODS

### 5.1 Lexicon-Based Sentiment Analysis
- **Description**: Uses predefined dictionaries (Loughran-McDonald financial dictionary, Harvard GI) to score text sentiment.
- **Applies to**: Both

### 5.2 Social Media Sentiment (Twitter/X, Reddit, StockTwits)
- **Description**: Aggregates sentiment from posts mentioning tickers; tracks bullish/bearish ratios, engagement volume.
- **Applies to**: Both

### 5.3 News Sentiment Analysis (NLP)
- **Description**: Applies NLP models to news headlines and articles to extract sentiment, classify events, and predict impact.
- **Applies to**: Both

### 5.4 Earnings Call Transcript Analysis
- **Description**: NLP analysis of tone, word choice, and linguistic patterns in management commentary during earnings calls.
- **Applies to**: Stocks

### 5.5 SEC Filing Analysis (10-K, 10-Q, 8-K)
- **Description**: NLP extraction of sentiment, risk factors, and changes from regulatory filings.
- **Applies to**: Stocks

### 5.6 Fear and Greed Index
- **Description**: Composite index combining momentum, volume, put/call ratio, junk bond demand, volatility, etc.
- **Applies to**: Stocks (CNN), Crypto (Alternative.me)

### 5.7 Put/Call Ratio Sentiment
- **Description**: Ratio of put to call option volume as measure of market sentiment; high ratio = bearish.
- **Applies to**: Stocks

### 5.8 AAII Sentiment Survey / Investors Intelligence
- **Description**: Survey-based sentiment of individual/professional investors; contrarian signals at extremes.
- **Applies to**: Stocks

### 5.9 Google Trends / Search Volume Index (SVI)
- **Description**: Tracks search interest for financial terms/tickers; spikes may predict volatility or directional moves.
- **Applies to**: Both

### 5.10 Crypto-Specific Sentiment (Telegram, Discord, Crypto Twitter)
- **Description**: Monitors crypto-native communities for hype, FUD, and project-specific sentiment.
- **Applies to**: Crypto

---

## 6. ON-CHAIN ANALYSIS (Crypto-Specific)

### 6.1 NVT Ratio (Network Value to Transactions)
- **Description**: Crypto P/E ratio; compares market cap to on-chain transaction volume.
- **Applies to**: Crypto
- **Formula**: `NVT = Market Cap / Daily Transaction Volume (USD)`
- **Interpretation**: High NVT = overvalued/speculative; Low NVT = undervalued/high utility.

### 6.2 NVT Signal
- **Description**: Smoother variant of NVT using 90-day MA of transaction volume instead of daily.
- **Applies to**: Crypto

### 6.3 MVRV Ratio (Market Value to Realized Value)
- **Description**: Compares market cap to realized cap (each UTXO valued at last moved price).
- **Applies to**: Crypto
- **Formula**: `MVRV = Market Cap / Realized Cap`
- **Interpretation**: >3.5 signals top, <1.0 signals bottom.

### 6.4 MVRV Z-Score
- **Description**: Standardized deviation of market cap from realized cap; more precise top/bottom detection.
- **Applies to**: Crypto
- **Formula**: `Z = (Market Cap - Realized Cap) / Std(Market Cap)`

### 6.5 SOPR (Spent Output Profit Ratio)
- **Description**: Ratio of realized value to creation value of spent outputs; shows aggregate profit/loss.
- **Applies to**: Crypto
- **Formula**: `SOPR = Σ(value at spend) / Σ(value at creation)` for all spent outputs
- **Variants**: STH-SOPR, LTH-SOPR, aSOPR (adjusted)

### 6.6 NUPL (Net Unrealized Profit/Loss)
- **Description**: Total profit/loss if all coins were sold at current price.
- **Applies to**: Crypto
- **Formula**: `NUPL = (Market Cap - Realized Cap) / Market Cap`

### 6.7 Stock-to-Flow Model (S2F)
- **Description**: Values Bitcoin based on scarcity (ratio of existing supply to annual production).
- **Applies to**: Crypto (Bitcoin, PoW)
- **Formula**: `S2F = Stock / Flow`, then `Price = e^a × S2F^b`

### 6.8 Stock-to-Flow Cross-Asset Model (S2FX)
- **Description**: Extension treating Bitcoin through different phase transitions alongside gold and silver.
- **Applies to**: Crypto

### 6.9 Thermocap Multiple
- **Description**: Market cap divided by cumulative miner revenue; measures aggregate return to security spend.
- **Applies to**: Crypto

### 6.10 Puell Multiple
- **Description**: Daily coin issuance (USD) divided by 365-day MA of issuance; identifies miner revenue extremes.
- **Applies to**: Crypto
- **Formula**: `Puell = Daily Issuance USD / MA365(Daily Issuance USD)`

### 6.11 Hash Rate & Mining Difficulty Analysis
- **Description**: Tracks network security and miner economics; hash rate drops may signal miner capitulation.
- **Applies to**: Crypto (PoW)

### 6.12 Hash Ribbons
- **Description**: Compares 30-day and 60-day MA of hash rate to identify miner capitulation and recovery signals.
- **Applies to**: Crypto

### 6.13 Active Addresses / New Addresses
- **Description**: Counts unique addresses transacting; proxy for network adoption and demand.
- **Applies to**: Crypto

### 6.14 Exchange Flows (Inflow / Outflow)
- **Description**: Tracks deposits (sell pressure) and withdrawals (accumulation) from exchanges.
- **Applies to**: Crypto

### 6.15 Exchange Reserve
- **Description**: Total coins held on exchanges; declining reserves = accumulation (bullish).
- **Applies to**: Crypto

### 6.16 Coin Days Destroyed (CDD)
- **Description**: Measures economic activity by weighting transactions by coin age; high CDD = old coins moving.
- **Applies to**: Crypto
- **Formula**: `CDD = Coins × Days since last moved`

### 6.17 HODL Waves / Realized Cap HODL Waves
- **Description**: Age distribution of UTXO set; shows proportion of supply by age band.
- **Applies to**: Crypto

### 6.18 Supply in Profit / Loss
- **Description**: Percentage of total supply currently above/below its acquisition price.
- **Applies to**: Crypto

### 6.19 Realized Price
- **Description**: Average price at which each coin last moved (realized cap / supply).
- **Applies to**: Crypto

### 6.20 Mayer Multiple
- **Description**: Current price divided by 200-day MA; identifies overbought/oversold relative to long-term trend.
- **Applies to**: Crypto
- **Formula**: `Mayer Multiple = Price / MA200`

### 6.21 Pi Cycle Top Indicator
- **Description**: Uses crossing of 111-day MA and 2x of 350-day MA to identify market cycle tops.
- **Applies to**: Crypto

### 6.22 Reserve Risk
- **Description**: Confidence (accumulated opportunity cost of holding) relative to price; low = high conviction holders.
- **Applies to**: Crypto

### 6.23 Stablecoin Supply Ratio (SSR)
- **Description**: Bitcoin market cap divided by total stablecoin market cap; low SSR = high purchasing power available.
- **Applies to**: Crypto

### 6.24 Whale Alert / Large Transaction Monitoring
- **Description**: Tracking large on-chain transactions by wallets holding significant amounts; predicts large sell/buy pressure.
- **Applies to**: Crypto

### 6.25 DeFi TVL (Total Value Locked) Analysis
- **Description**: Tracks capital locked in DeFi protocols as measure of ecosystem health and token demand.
- **Applies to**: Crypto

### 6.26 Gas Fees / Network Congestion
- **Description**: High gas fees indicate high network demand; proxy for network utility.
- **Applies to**: Crypto (especially Ethereum)

---

## 7. OPTIONS-BASED / DERIVATIVES PRICING MODELS

### 7.1 Black-Scholes-Merton (BSM) Model
- **Description**: Closed-form option pricing assuming log-normal prices, constant volatility, no dividends.
- **Applies to**: Stocks (primarily)
- **Formula**: `C = S₀N(d₁) - Ke^(-rT)N(d₂)` where `d₁ = [ln(S/K) + (r + σ²/2)T] / (σ√T)`, `d₂ = d₁ - σ√T`

### 7.2 Black Model (Black-76)
- **Description**: Variant for pricing options on futures, bonds, interest rate products.
- **Applies to**: Stocks / Futures
- **Formula**: Like BSM but uses forward price F instead of spot S.

### 7.3 Binomial Options Pricing Model (Cox-Ross-Rubinstein)
- **Description**: Discrete-time lattice model; allows American-style early exercise, dividends, changing volatility.
- **Applies to**: Stocks, Crypto
- **Parameters**: `u = e^(σ√Δt)`, `d = 1/u`, `p = (e^(rΔt) - d) / (u - d)`

### 7.4 Trinomial Tree Model
- **Description**: Three-branch lattice (up, down, middle); more accurate than binomial for same number of steps.
- **Applies to**: Stocks

### 7.5 Heston Stochastic Volatility Model
- **Description**: Models volatility as a mean-reverting stochastic process correlated with price.
- **Applies to**: Stocks, Crypto
- **SDEs**: `dS = μSdt + √v S dW₁`, `dv = κ(θ-v)dt + ξ√v dW₂`, `Corr(dW₁,dW₂) = ρ`

### 7.6 SABR Model
- **Description**: Stochastic Alpha Beta Rho; models volatility smile dynamics for interest rate and equity options.
- **Applies to**: Stocks
- **SDEs**: `dF = σFᵝdW₁`, `dσ = ασdW₂`

### 7.7 Bates Model (Jump-Diffusion + Stochastic Vol)
- **Description**: Combines Heston stochastic volatility with Merton jump-diffusion.
- **Applies to**: Stocks

### 7.8 Merton Jump-Diffusion Model
- **Description**: Adds Poisson-distributed jumps to geometric Brownian motion; captures sudden price moves.
- **Applies to**: Stocks, Crypto
- **SDE**: `dS/S = (μ-λk)dt + σdW + JdN`

### 7.9 Local Volatility Model (Dupire)
- **Description**: Volatility is a deterministic function of price and time; perfectly fits observed volatility surface.
- **Applies to**: Stocks

### 7.10 Bachelier Model
- **Description**: Assumes arithmetic (normal) price process instead of geometric; allows negative prices.
- **Applies to**: Stocks / Futures

### 7.11 Monte Carlo Option Pricing
- **Description**: Simulates thousands of price paths to price complex/exotic options.
- **Applies to**: Both

### 7.12 Implied Volatility Surface Analysis
- **Description**: Maps implied volatility across strikes and expirations; shape encodes market expectations about future price distribution.
- **Applies to**: Stocks, Crypto (emerging)

### 7.13 Options Greeks for Price Prediction
- **Description**: Delta, gamma, vanna, charm used to infer expected moves and hedging flows (GEX - Gamma Exposure analysis).
- **Applies to**: Stocks, Crypto
- **GEX concept**: Net dealer gamma exposure at each strike implies expected support/resistance via hedging flows.

### 7.14 Max Pain Theory
- **Description**: Price tends to gravitate toward strike where most options expire worthless (maximum loss for option buyers).
- **Applies to**: Stocks, Crypto

### 7.15 Put-Call Parity
- **Description**: Arbitrage relationship linking call, put, underlying, and risk-free bond prices.
- **Applies to**: Stocks
- **Formula**: `C - P = S - Ke^(-rT)`

### 7.16 Variance Swaps / Volatility Derivatives
- **Description**: Trade realized vs. implied variance; provides forward-looking volatility expectations.
- **Applies to**: Stocks

---

## 8. BEHAVIORAL FINANCE APPROACHES

### 8.1 Prospect Theory (Kahneman & Tversky)
- **Description**: Models how investors evaluate gains/losses asymmetrically (loss aversion, reference dependence, diminishing sensitivity). Implies predictable mispricing.
- **Applies to**: Both

### 8.2 Overreaction / Underreaction Models
- **Description**: Markets systematically overreact to dramatic news and underreact to gradual information; enables contrarian and momentum strategies.
- **Applies to**: Both

### 8.3 Disposition Effect
- **Description**: Investors sell winners too early and hold losers too long; creates predictable price patterns around reference points.
- **Applies to**: Both

### 8.4 Herding Models
- **Description**: Models information cascades where investors follow others; creates momentum and bubbles.
- **Applies to**: Both

### 8.5 Anchoring Bias Models
- **Description**: Prices anchor to salient reference points (52-week high, round numbers, IPO price); predicts resistance/support.
- **Applies to**: Both

### 8.6 Noise Trader Risk (DeLong-Shleifer-Summers-Waldmann / DSSW)
- **Description**: Models how irrational noise traders affect prices and create risk for arbitrageurs.
- **Applies to**: Both

### 8.7 Limits to Arbitrage
- **Description**: Explains why mispricings can persist: fundamental risk, noise trader risk, implementation costs, model risk.
- **Applies to**: Both

### 8.8 Mental Accounting
- **Description**: Investors categorize money into separate accounts affecting investment decisions; creates predictable patterns (e.g., January effect, dividend preference).
- **Applies to**: Both

### 8.9 Attention-Based Trading Models
- **Description**: Stocks that attract attention (unusual volume, news, extreme returns) experience predictable buying pressure from retail investors.
- **Applies to**: Both

### 8.10 Sentiment Cycle Models (Investor Psychology Cycle)
- **Description**: Maps market phases to psychological states (optimism, excitement, euphoria, anxiety, denial, panic, capitulation, hope).
- **Applies to**: Both

---

## 9. EVENT-DRIVEN METHODS

### 9.1 Earnings Surprise / Post-Earnings Announcement Drift (PEAD)
- **Description**: Stocks drift in the direction of earnings surprise for 60+ days after announcement.
- **Applies to**: Stocks

### 9.2 Merger Arbitrage
- **Description**: Long target, short acquirer in announced deals; profits from spread closing.
- **Applies to**: Stocks

### 9.3 Spin-Off / Restructuring Arbitrage
- **Description**: Exploits temporary mispricing during corporate restructurings.
- **Applies to**: Stocks

### 9.4 Index Rebalancing Prediction
- **Description**: Predicts price impact when stocks are added/removed from indices (forced buying/selling by index funds).
- **Applies to**: Stocks

### 9.5 Insider Trading Signal Analysis
- **Description**: Tracks insider buying/selling (SEC Form 4) as predictive signal.
- **Applies to**: Stocks

### 9.6 Central Bank / FOMC Event Trading
- **Description**: Models price response to interest rate decisions, forward guidance, and dot plots.
- **Applies to**: Both

### 9.7 Macro Data Release Trading
- **Description**: Trades on NFP, CPI, GDP, PMI releases and deviation from consensus.
- **Applies to**: Both

### 9.8 Halving Event Models (Crypto)
- **Description**: Models Bitcoin price cycle around supply halving events (~4-year cycle).
- **Applies to**: Crypto

### 9.9 Token Unlock / Vesting Schedule Analysis
- **Description**: Predicts sell pressure when locked tokens are released to investors/team.
- **Applies to**: Crypto

### 9.10 Hard Fork / Protocol Upgrade Event Trading
- **Description**: Trades around scheduled protocol changes (e.g., Ethereum Merge).
- **Applies to**: Crypto

### 9.11 Regulatory Event Analysis
- **Description**: Predicts impact of SEC actions, legislation, and regulatory decisions on prices.
- **Applies to**: Both

### 9.12 Share Buyback Announcement Effect
- **Description**: Models positive price impact of announced buyback programs.
- **Applies to**: Stocks

### 9.13 Dividend Announcement / Ex-Dividend Trading
- **Description**: Exploits predictable price adjustment around dividend events.
- **Applies to**: Stocks

### 9.14 IPO / ICO / Token Launch Analysis
- **Description**: Models first-day returns, lockup expiration effects, and long-run underperformance.
- **Applies to**: Stocks (IPO), Crypto (ICO/IDO)

---

## 10. ALTERNATIVE DATA METHODS

### 10.1 Satellite Imagery Analysis
- **Description**: Parking lot counts (retail traffic), oil storage levels, crop health, construction activity.
- **Applies to**: Stocks

### 10.2 Credit Card / Transaction Data
- **Description**: Real-time consumer spending data to estimate revenue ahead of earnings.
- **Applies to**: Stocks

### 10.3 Web Scraping (Product Prices, Job Postings, Reviews)
- **Description**: Tracks product prices, hiring trends, app reviews as leading indicators of company performance.
- **Applies to**: Stocks

### 10.4 App Download / Usage Data (App Annie / Sensor Tower)
- **Description**: Mobile app engagement metrics predict user growth and revenue.
- **Applies to**: Stocks, Crypto

### 10.5 Patent Filings Analysis
- **Description**: Tracks patent activity as indicator of R&D pipeline and future competitive advantage.
- **Applies to**: Stocks

### 10.6 Supply Chain Data / Shipping / AIS Data
- **Description**: Vessel tracking (AIS), port activity, and supply chain disruption signals.
- **Applies to**: Stocks

### 10.7 Weather Data Models
- **Description**: Weather patterns affecting agriculture, energy demand, retail foot traffic.
- **Applies to**: Stocks

### 10.8 Geolocation / Foot Traffic Data
- **Description**: Anonymized mobile location data estimating store visits and consumer behavior.
- **Applies to**: Stocks

### 10.9 Email Receipt Data
- **Description**: Aggregated e-commerce receipt data from email panels to estimate online sales.
- **Applies to**: Stocks

### 10.10 Government / Lobbying Data
- **Description**: Tracks lobbying expenditure, government contracts, and political donations as signals.
- **Applies to**: Stocks

### 10.11 GitHub Activity (Crypto Projects)
- **Description**: Monitors commit frequency, developer count, code quality for crypto project health.
- **Applies to**: Crypto

### 10.12 Social Graph / Influencer Tracking
- **Description**: Monitors key influencer sentiment and reach; tracks viral potential of crypto projects.
- **Applies to**: Both

---

## 11. NETWORK / GRAPH ANALYSIS

### 11.1 Correlation Network Analysis
- **Description**: Builds graph where nodes = assets, edges = correlations; identifies clusters, central nodes, and systemic risk.
- **Applies to**: Both

### 11.2 Minimum Spanning Tree (MST)
- **Description**: Extracts most important correlation links; reveals market structure and hierarchical clustering.
- **Applies to**: Both

### 11.3 Planar Maximally Filtered Graph (PMFG)
- **Description**: More edges than MST while maintaining planarity; richer network structure.
- **Applies to**: Both

### 11.4 Granger Causality Networks
- **Description**: Builds directed graph where edges represent statistically significant lead-lag relationships between assets.
- **Applies to**: Both

### 11.5 Transfer Entropy Networks
- **Description**: Information-theoretic measure of directional information flow between time series; captures non-linear relationships.
- **Applies to**: Both

### 11.6 Mutual Information Networks
- **Description**: Measures total (linear + non-linear) dependence between asset returns; builds dependency structure.
- **Applies to**: Both

### 11.7 Supply Chain Network Analysis
- **Description**: Maps customer-supplier relationships; predicts cross-firm return predictability.
- **Applies to**: Stocks

### 11.8 Blockchain Transaction Graph Analysis
- **Description**: Analyzes wallet-to-wallet flows, identifies whale activity patterns, exchange flows, and wash trading.
- **Applies to**: Crypto

### 11.9 Social Network Influence Propagation
- **Description**: Models how information and sentiment spread through investor networks.
- **Applies to**: Both

### 11.10 Knowledge Graphs for Financial Reasoning
- **Description**: Structured representation of entities (companies, people, events) and relationships for multi-hop reasoning about price impact.
- **Applies to**: Both

---

## 12. MACRO / ECONOMIC MODELS

### 12.1 Fed Model
- **Description**: Compares stock earnings yield (E/P) to 10-year Treasury yield.
- **Applies to**: Stocks
- **Signal**: Stocks attractive when E/P > Treasury yield.

### 12.2 Gordon Growth Model (Macro Version)
- **Description**: Expected stock market return = dividend yield + expected earnings growth.
- **Applies to**: Stocks
- **Formula**: `E(R) = D/P + g`

### 12.3 Buffett Indicator (Market Cap / GDP)
- **Description**: Total stock market capitalization relative to GDP; measures aggregate market valuation.
- **Applies to**: Stocks
- **Formula**: `Buffett Indicator = Total Market Cap / GDP`

### 12.4 Tobin's Q
- **Description**: Market value of assets divided by replacement cost; Q>1 implies overvaluation.
- **Applies to**: Stocks
- **Formula**: `Q = Market Value of Assets / Replacement Cost`

### 12.5 Yield Curve Analysis
- **Description**: Shape of Treasury yield curve (normal, inverted, flat) predicts economic cycles and equity returns.
- **Applies to**: Stocks, Both

### 12.6 Taylor Rule
- **Description**: Prescribes interest rate based on inflation and output gap; deviations signal policy surprise.
- **Applies to**: Stocks
- **Formula**: `r = r* + 0.5(π - π*) + 0.5(y - y*)`

### 12.7 Purchasing Managers' Index (PMI) Signal
- **Description**: Leading indicator of economic expansion/contraction; predicts equity market direction.
- **Applies to**: Stocks

### 12.8 Money Supply (M2) Growth Models
- **Description**: Rapid M2 growth historically correlates with asset price inflation (stocks and crypto).
- **Applies to**: Both

### 12.9 Real Interest Rate Models
- **Description**: Negative real rates historically support risk assets; Fisher equation relates nominal, real rates and inflation.
- **Applies to**: Both

### 12.10 Dollar Strength (DXY) Correlation Models
- **Description**: USD strength inversely correlates with risk assets, commodities, and crypto.
- **Applies to**: Both

### 12.11 Kondratiev / Long Wave Economic Cycle
- **Description**: 40-60 year economic super-cycles driven by technological innovation.
- **Applies to**: Stocks

### 12.12 Business Cycle / NBER Recession Indicators
- **Description**: Maps market performance to expansion/contraction phases.
- **Applies to**: Stocks

### 12.13 Global Liquidity Cycle Models
- **Description**: Tracks aggregate central bank balance sheets and credit creation as driver of all risk assets.
- **Applies to**: Both

---

## 13. GAME THEORY APPROACHES

### 13.1 Nash Equilibrium in Market Microstructure
- **Description**: Models optimal strategies of informed traders, market makers, and noise traders.
- **Applies to**: Both

### 13.2 Kyle's Lambda Model
- **Description**: Models how informed trading affects price impact; relates order flow to information asymmetry.
- **Applies to**: Stocks
- **Formula**: `ΔP = λ × Order Flow` where λ = Kyle's lambda (price impact coefficient)

### 13.3 Glosten-Milgrom Model
- **Description**: Sequential trade model where bid-ask spread reflects adverse selection risk from informed traders.
- **Applies to**: Stocks

### 13.4 Auction Theory (IPO, NFT, Token Sales)
- **Description**: Models optimal bidding strategies and price discovery in various auction formats.
- **Applies to**: Both

### 13.5 Mechanism Design for Token Economics
- **Description**: Designs incentive-compatible token distribution and governance mechanisms that affect token value.
- **Applies to**: Crypto

### 13.6 Zero-Sum Game Models (Options / Futures)
- **Description**: Models derivatives trading as zero-sum game between longs and shorts.
- **Applies to**: Both

### 13.7 Evolutionary Game Theory in Markets
- **Description**: Models strategy populations (momentum, value, noise) evolving over time; explains factor crowding and regime shifts.
- **Applies to**: Both

### 13.8 Minority Game / El Farol Bar Problem
- **Description**: Models where agents benefit from being in the minority; captures contrarian dynamics in markets.
- **Applies to**: Both

### 13.9 Signaling Games (Corporate Finance)
- **Description**: Dividends, buybacks, and capital structure choices as signals of quality; affects pricing.
- **Applies to**: Stocks

### 13.10 Maximin / Game-Theoretic Portfolio Optimization
- **Description**: Constructs portfolios robust to worst-case scenarios using minimax optimization.
- **Applies to**: Both

---

## 14. OTHER / EMERGING / LESSER-KNOWN METHODS

### 14.1 Topological Data Analysis (TDA) / Persistent Homology
- **Description**: Detects topological features (holes, loops) in point cloud data that persist across scales; identifies market regime changes and crash precursors.
- **Applies to**: Both

### 14.2 Fractal / Multifractal Analysis
- **Description**: Models self-similar patterns at different time scales; Multifractal Detrended Fluctuation Analysis (MF-DFA) characterizes market complexity.
- **Applies to**: Both

### 14.3 Entropy-Based Methods (Shannon, Sample, Approximate, Permutation Entropy)
- **Description**: Measures information content and complexity of price series; changes in entropy signal regime transitions.
- **Applies to**: Both

### 14.4 Wavelet Analysis
- **Description**: Decomposes time series into frequency components at different scales; identifies dominant cycles and multi-scale patterns.
- **Applies to**: Both

### 14.5 Empirical Mode Decomposition (EMD / EEMD / CEEMDAN)
- **Description**: Adaptive decomposition of non-linear, non-stationary signals into intrinsic mode functions (IMFs).
- **Applies to**: Both

### 14.6 Variational Mode Decomposition (VMD)
- **Description**: Non-recursive signal decomposition into band-limited modes; more robust than EMD.
- **Applies to**: Both

### 14.7 Econophysics / Statistical Mechanics Models
- **Description**: Applies physics concepts (Ising models, percolation, power laws, phase transitions) to financial markets.
- **Applies to**: Both

### 14.8 Agent-Based Models (ABM)
- **Description**: Simulates heterogeneous interacting agents (fundamentalists, chartists, noise traders) to generate emergent market dynamics.
- **Applies to**: Both

### 14.9 Genetic Algorithms / Evolutionary Computation
- **Description**: Evolves trading rules or model parameters through selection, crossover, and mutation.
- **Applies to**: Both

### 14.10 Genetic Programming
- **Description**: Evolves mathematical expressions (trading strategies / indicators) from primitives.
- **Applies to**: Both

### 14.11 Fuzzy Logic Systems
- **Description**: Handles imprecise inputs with linguistic rules (e.g., "if RSI is HIGH and volume is LOW then SELL"); models expert reasoning.
- **Applies to**: Both

### 14.12 Chaos Theory / Lyapunov Exponent
- **Description**: Tests for deterministic chaos in price series; positive Lyapunov exponent implies sensitive dependence on initial conditions.
- **Applies to**: Both

### 14.13 Random Matrix Theory (RMT)
- **Description**: Separates true correlations from noise in return correlation matrices; improves portfolio optimization.
- **Applies to**: Both

### 14.14 Quantum Computing Methods
- **Description**: Quantum annealing for portfolio optimization, quantum ML for pattern recognition, variational quantum eigensolvers. Emerging and experimental.
- **Applies to**: Both

### 14.15 Symbolic Regression
- **Description**: Discovers interpretable mathematical formulas from data without assuming functional form.
- **Applies to**: Both

### 14.16 Reservoir Computing / Echo State Networks
- **Description**: Recurrent network where only output layer is trained; efficient for chaotic time series.
- **Applies to**: Both

### 14.17 Causal Inference Methods (DoWhy, Instrumental Variables)
- **Description**: Goes beyond correlation to estimate causal impact of events/factors on prices.
- **Applies to**: Both

### 14.18 Conformal Prediction
- **Description**: Provides prediction intervals with guaranteed coverage probability; quantifies uncertainty.
- **Applies to**: Both

### 14.19 Optimal Transport / Wasserstein Distance
- **Description**: Measures distance between probability distributions; used for distributional forecasting and detecting distribution shifts.
- **Applies to**: Both

### 14.20 Power Law / Zipf's Law Analysis
- **Description**: Models fat-tailed return distributions and scaling behavior in markets.
- **Applies to**: Both

### 14.21 Information-Theoretic Approaches (Mutual Information, Directed Information)
- **Description**: Measures non-linear dependencies and directional information flow between assets/features.
- **Applies to**: Both

### 14.22 Benford's Law Analysis
- **Description**: Detects manipulation or anomalies by checking if leading digits of financial data follow expected distribution.
- **Applies to**: Both

### 14.23 Cross-Asset Momentum / Carry / Value
- **Description**: Applies factor premia across asset classes (equities, bonds, FX, commodities, crypto).
- **Applies to**: Both

### 14.24 Seasonality / Calendar Effects
- **Description**: Models recurring patterns: January effect, sell in May, turn of month, day of week, holiday effects, options expiration (OpEx).
- **Applies to**: Both

### 14.25 Dark Pool / Hidden Liquidity Analysis
- **Description**: Monitors dark pool prints and block trade data for institutional activity signals.
- **Applies to**: Stocks

### 14.26 Short Interest / Borrow Rate Analysis
- **Description**: High short interest or rising borrow rates indicate crowded shorts; potential squeeze signal.
- **Applies to**: Stocks

### 14.27 Funding Rate Analysis (Crypto Perpetuals)
- **Description**: Positive funding rate = longs pay shorts (bullish crowding); negative = bearish crowding. Extreme funding predicts reversals.
- **Applies to**: Crypto

### 14.28 Open Interest Analysis
- **Description**: Changes in open interest combined with price moves reveal whether new money is entering/exiting; confirms trends.
- **Applies to**: Both

### 14.29 Liquidation Cascade / Liquidation Heatmap Models
- **Description**: Maps leveraged positions to identify price levels where cascading liquidations will trigger; predicts sudden moves.
- **Applies to**: Crypto (primarily)

### 14.30 Market Microstructure (Order Book Imbalance)
- **Description**: Bid-ask imbalance, order book depth analysis, and queue position predict very short-term price moves.
- **Applies to**: Both

### 14.31 Flow Toxicity (VPIN - Volume-Synchronized Probability of Informed Trading)
- **Description**: Real-time estimate of information asymmetry in order flow; predicts adverse selection risk.
- **Applies to**: Stocks

### 14.32 Nowcasting
- **Description**: Real-time estimation of current economic conditions using high-frequency data before official releases.
- **Applies to**: Stocks

### 14.33 Survival Analysis
- **Description**: Models time-to-event (time until price target hit, stop loss triggered, or regime change).
- **Applies to**: Both

### 14.34 State Space Models
- **Description**: General framework (includes Kalman filter, HMM) where observed prices are generated by hidden state dynamics.
- **Applies to**: Both

### 14.35 Rough Volatility Models
- **Description**: Models volatility with fractional Brownian motion (Hurst parameter ~0.1); captures empirical volatility dynamics better than classical models.
- **Applies to**: Stocks

### 14.36 Physics-Inspired Neural Networks (PINNs)
- **Description**: Neural networks constrained by differential equations (e.g., Black-Scholes PDE); combines data-driven and model-driven approaches.
- **Applies to**: Both

---

## SUMMARY TABLE

| Category | Count | Applies To |
|----------|-------|------------|
| 1. Fundamental Analysis | 18 | Stocks primarily; 2 crypto-specific |
| 2. Technical Analysis | 60+ | Both stocks and crypto |
| 3. Quantitative/Statistical | 27 | Both |
| 4. Machine Learning / AI | 45 | Both |
| 5. Sentiment Analysis | 10 | Both (some stock-specific) |
| 6. On-Chain Analysis | 26 | Crypto only |
| 7. Options/Derivatives Models | 16 | Stocks primarily; some crypto |
| 8. Behavioral Finance | 10 | Both |
| 9. Event-Driven | 14 | Both (some stock/crypto-specific) |
| 10. Alternative Data | 12 | Stocks primarily; some crypto |
| 11. Network/Graph Analysis | 10 | Both |
| 12. Macro/Economic Models | 13 | Both |
| 13. Game Theory | 10 | Both |
| 14. Other/Emerging | 36 | Both |
| **TOTAL** | **~300+** | |
