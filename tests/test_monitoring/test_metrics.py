"""Tests for src.monitoring.metrics metric definitions."""

import re

from src.monitoring.metrics import (
    BOT_REQUEST_COUNT,
    DATA_FRESHNESS_HOURS,
    ENGINE_DURATION,
    FETCH_FAILURE,
    FETCH_SUCCESS,
    LLM_CALL_COUNT,
    LLM_CALL_DURATION,
    PIPELINE_DURATION,
    PIPELINE_LAST_SUCCESS,
    PIPELINE_STAGE_STATUS,
)


ALL_METRICS = [
    PIPELINE_DURATION,
    PIPELINE_STAGE_STATUS,
    FETCH_SUCCESS,
    FETCH_FAILURE,
    LLM_CALL_COUNT,
    LLM_CALL_DURATION,
    ENGINE_DURATION,
    DATA_FRESHNESS_HOURS,
    PIPELINE_LAST_SUCCESS,
    BOT_REQUEST_COUNT,
]


def test_all_metrics_importable() -> None:
    """All metric objects are importable without error."""
    for metric in ALL_METRICS:
        assert metric is not None


def test_metric_names_follow_conventions() -> None:
    """Metric names must be snake_case (no dashes, no uppercase)."""
    pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    for metric in ALL_METRICS:
        name = metric._name
        assert pattern.match(name), f"Metric name '{name}' violates Prometheus naming"


def test_pipeline_duration_labels() -> None:
    """PIPELINE_DURATION has expected labels."""
    assert PIPELINE_DURATION._labelnames == ("stage",)


def test_llm_call_count_labels() -> None:
    """LLM_CALL_COUNT has expected labels."""
    assert LLM_CALL_COUNT._labelnames == ("model", "is_fallback")


def test_engine_duration_labels() -> None:
    """ENGINE_DURATION has expected labels."""
    assert ENGINE_DURATION._labelnames == ("engine_name",)


def test_counter_increment_works() -> None:
    """Incrementing a counter works without error."""
    PIPELINE_STAGE_STATUS.labels(stage="fetch", status="completed").inc()
    # No assertion needed -- just verifying no exception is raised.
