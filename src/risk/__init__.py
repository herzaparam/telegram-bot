"""Portfolio risk computation module.

Pure computation functions (numpy/pandas only) -- no DB or pipeline imports.
Consumed by both the /portfolio bot handler and daily report pipeline hook.
"""

from src.risk.concentration import ConcentrationResult, compute_concentration
from src.risk.correlation import (
    CorrelationResult,
    compute_correlation_matrix,
    format_correlation_heatmap,
)
from src.risk.metrics import RiskMetricsResult, compute_risk_metrics
from src.risk.stress import STRESS_SCENARIOS, StressResult, run_stress_test
from src.risk.var import VaRResult, compute_historical_var

__all__ = [
    "ConcentrationResult",
    "CorrelationResult",
    "RiskMetricsResult",
    "STRESS_SCENARIOS",
    "StressResult",
    "VaRResult",
    "compute_concentration",
    "compute_correlation_matrix",
    "compute_historical_var",
    "compute_risk_metrics",
    "format_correlation_heatmap",
    "run_stress_test",
]
