"""Tests for pipeline runner Prometheus metrics instrumentation."""

from unittest.mock import MagicMock, patch

import pytest
from prometheus_client import REGISTRY

from src.monitoring.metrics import PIPELINE_DURATION, PIPELINE_STAGE_STATUS


def test_pipeline_duration_labels():
    """Verify PIPELINE_DURATION histogram has the expected stage label."""
    before = REGISTRY.get_sample_value(
        "pipeline_run_duration_seconds_count",
        {"stage": "metric_test_stage"},
    ) or 0.0

    PIPELINE_DURATION.labels(stage="metric_test_stage").observe(1.5)

    after = REGISTRY.get_sample_value(
        "pipeline_run_duration_seconds_count",
        {"stage": "metric_test_stage"},
    ) or 0.0

    assert after == before + 1, "PIPELINE_DURATION should accept stage label and observe"


def test_pipeline_stage_status_labels():
    """Verify PIPELINE_STAGE_STATUS counter has expected labels."""
    before = REGISTRY.get_sample_value(
        "pipeline_stage_status_total",
        {"stage": "metric_test_stage", "status": "completed"},
    ) or 0.0

    PIPELINE_STAGE_STATUS.labels(stage="metric_test_stage", status="completed").inc()

    after = REGISTRY.get_sample_value(
        "pipeline_stage_status_total",
        {"stage": "metric_test_stage", "status": "completed"},
    ) or 0.0

    assert after == before + 1, "PIPELINE_STAGE_STATUS should accept stage+status labels"


def test_runner_imports_metrics():
    """Verify runner module imports the metric objects."""
    import src.pipeline.runner as runner_mod

    # The module should have imported these from metrics
    assert hasattr(runner_mod, "PIPELINE_DURATION")
    assert hasattr(runner_mod, "PIPELINE_STAGE_STATUS")


def test_runner_run_stage_contains_metric_calls():
    """Verify run_stage source code contains metric emission calls."""
    import inspect

    from src.pipeline.runner import PipelineRunner

    source = inspect.getsource(PipelineRunner.run_stage)
    assert "PIPELINE_DURATION.labels(stage=stage).observe(elapsed)" in source
    assert "PIPELINE_STAGE_STATUS.labels(stage=stage, status=result.status).inc()" in source
