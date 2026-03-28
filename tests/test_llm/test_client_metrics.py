"""Tests for LLM client Prometheus metrics instrumentation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prometheus_client import REGISTRY

from src.llm.client import llm_completion


@pytest.mark.asyncio
async def test_llm_completion_emits_metrics_on_success():
    """Verify llm_completion increments LLM_CALL_COUNT on success."""
    before = REGISTRY.get_sample_value(
        "llm_call_total",
        {"model": "test-model", "is_fallback": "false"},
    ) or 0.0

    mock_response = MagicMock()
    mock_response.model = "test-model"
    mock_response.choices = [MagicMock(message=MagicMock(content="test response"))]

    with patch("src.llm.client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)
        result = await llm_completion(
            messages=[{"role": "user", "content": "test"}],
            model="test-model",
        )

    after = REGISTRY.get_sample_value(
        "llm_call_total",
        {"model": "test-model", "is_fallback": "false"},
    ) or 0.0

    assert after > before, "LLM_CALL_COUNT should have been incremented"
    assert result.content == "test response"


@pytest.mark.asyncio
async def test_llm_completion_emits_duration_on_success():
    """Verify llm_completion observes LLM_CALL_DURATION on success."""
    before = REGISTRY.get_sample_value(
        "llm_call_duration_seconds_count",
        {"model": "duration-model"},
    ) or 0.0

    mock_response = MagicMock()
    mock_response.model = "duration-model"
    mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]

    with patch("src.llm.client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)
        await llm_completion(
            messages=[{"role": "user", "content": "test"}],
            model="duration-model",
        )

    after = REGISTRY.get_sample_value(
        "llm_call_duration_seconds_count",
        {"model": "duration-model"},
    ) or 0.0

    assert after > before, "LLM_CALL_DURATION should have been observed"


@pytest.mark.asyncio
async def test_llm_completion_emits_fallback_metric_on_failure():
    """Verify llm_completion increments fallback counter on failure."""
    before = REGISTRY.get_sample_value(
        "llm_call_total",
        {"model": "none", "is_fallback": "true"},
    ) or 0.0

    with patch("src.llm.client.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(side_effect=Exception("API down"))
        result = await llm_completion(
            messages=[{"role": "user", "content": "test"}],
            model="fail-model",
            fallback_models=["also-fail"],
        )

    after = REGISTRY.get_sample_value(
        "llm_call_total",
        {"model": "none", "is_fallback": "true"},
    ) or 0.0

    assert after > before, "LLM_CALL_COUNT fallback should have been incremented"
    assert result.content == ""  # LLM_UNAVAILABLE
