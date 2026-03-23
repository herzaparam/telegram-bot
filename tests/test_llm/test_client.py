"""Tests for the LLM wrapper client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.client import LLM_UNAVAILABLE, LLMResult, llm_completion


class TestLLMResult:
    """Tests for LLMResult dataclass."""

    def test_llm_result_fields(self) -> None:
        result = LLMResult(content="hello", model_used="gpt-4o-mini")
        assert result.content == "hello"
        assert result.model_used == "gpt-4o-mini"
        assert result.is_fallback is False

    def test_llm_result_is_frozen(self) -> None:
        result = LLMResult(content="hello", model_used="gpt-4o-mini")
        with pytest.raises(AttributeError):
            result.content = "changed"  # type: ignore[misc]


class TestLLMUnavailable:
    """Tests for the LLM_UNAVAILABLE sentinel."""

    def test_sentinel_content_empty(self) -> None:
        assert LLM_UNAVAILABLE.content == ""

    def test_sentinel_model_none(self) -> None:
        assert LLM_UNAVAILABLE.model_used == "none"

    def test_sentinel_is_fallback(self) -> None:
        assert LLM_UNAVAILABLE.is_fallback is True


class TestLLMCompletion:
    """Tests for the llm_completion async function."""

    def _mock_response(self, content: str = "test response", model: str = "gpt-4o-mini") -> MagicMock:
        """Create a mock litellm response."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = content
        response.model = model
        return response

    @patch("src.llm.client.litellm")
    async def test_successful_completion(self, mock_litellm: MagicMock) -> None:
        mock_litellm.acompletion = AsyncMock(return_value=self._mock_response("hello world", "gpt-4o-mini"))

        result = await llm_completion(messages=[{"role": "user", "content": "hi"}])

        assert isinstance(result, LLMResult)
        assert result.content == "hello world"
        assert result.model_used == "gpt-4o-mini"

    @patch("src.llm.client.litellm")
    async def test_successful_completion_is_not_fallback(self, mock_litellm: MagicMock) -> None:
        mock_litellm.acompletion = AsyncMock(return_value=self._mock_response())

        result = await llm_completion(messages=[{"role": "user", "content": "hi"}])

        assert result.is_fallback is False

    @patch("src.llm.client.litellm")
    async def test_all_models_fail_returns_unavailable(self, mock_litellm: MagicMock) -> None:
        mock_litellm.acompletion = AsyncMock(side_effect=Exception("API error"))

        result = await llm_completion(messages=[{"role": "user", "content": "hi"}])

        assert result is LLM_UNAVAILABLE
        assert result.content == ""
        assert result.model_used == "none"
        assert result.is_fallback is True

    @patch("src.llm.client.litellm")
    async def test_never_raises_exception(self, mock_litellm: MagicMock) -> None:
        mock_litellm.acompletion = AsyncMock(side_effect=RuntimeError("catastrophic failure"))

        # Must not raise -- returns LLM_UNAVAILABLE instead
        result = await llm_completion(messages=[{"role": "user", "content": "hi"}])
        assert result is LLM_UNAVAILABLE

    @patch("src.llm.client.litellm")
    async def test_passes_timeout_to_litellm(self, mock_litellm: MagicMock) -> None:
        mock_litellm.acompletion = AsyncMock(return_value=self._mock_response())

        await llm_completion(messages=[{"role": "user", "content": "hi"}], timeout=60)

        call_kwargs = mock_litellm.acompletion.call_args[1]
        assert call_kwargs["timeout"] == 60

    @patch("src.llm.client.litellm")
    async def test_passes_num_retries_to_litellm(self, mock_litellm: MagicMock) -> None:
        mock_litellm.acompletion = AsyncMock(return_value=self._mock_response())

        await llm_completion(messages=[{"role": "user", "content": "hi"}], num_retries=5)

        call_kwargs = mock_litellm.acompletion.call_args[1]
        assert call_kwargs["num_retries"] == 5

    @patch("src.llm.client.litellm")
    async def test_uses_settings_defaults(self, mock_litellm: MagicMock) -> None:
        mock_litellm.acompletion = AsyncMock(return_value=self._mock_response())

        await llm_completion(messages=[{"role": "user", "content": "hi"}])

        call_kwargs = mock_litellm.acompletion.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["num_retries"] == 3
        assert call_kwargs["timeout"] == 30
        assert call_kwargs["fallbacks"] == ["gemini/gemini-2.0-flash"]

    @patch("src.llm.client.litellm")
    async def test_custom_model_override(self, mock_litellm: MagicMock) -> None:
        mock_litellm.acompletion = AsyncMock(return_value=self._mock_response(model="deepseek/deepseek-chat"))

        result = await llm_completion(
            messages=[{"role": "user", "content": "hi"}],
            model="deepseek/deepseek-chat",
        )

        call_kwargs = mock_litellm.acompletion.call_args[1]
        assert call_kwargs["model"] == "deepseek/deepseek-chat"
        assert result.model_used == "deepseek/deepseek-chat"

    @patch("src.llm.client.litellm")
    async def test_handles_none_content(self, mock_litellm: MagicMock) -> None:
        """When LLM returns None content, should return empty string."""
        response = self._mock_response()
        response.choices[0].message.content = None
        mock_litellm.acompletion = AsyncMock(return_value=response)

        result = await llm_completion(messages=[{"role": "user", "content": "hi"}])

        assert result.content == ""
