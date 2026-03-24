"""Tests for llm_completion response_format extension."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.client import LLMResult, llm_completion


class TestResponseFormat:
    """Tests for response_format parameter on llm_completion."""

    def _mock_response(self, content: str = "test", model: str = "gpt-4o-mini") -> MagicMock:
        """Create a mock litellm response."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = content
        response.model = model
        return response

    @patch("src.llm.client.litellm")
    async def test_llm_completion_passes_response_format(self, mock_litellm: MagicMock) -> None:
        """response_format kwarg is passed through to litellm.acompletion."""
        mock_litellm.acompletion = AsyncMock(return_value=self._mock_response())

        await llm_completion(
            messages=[{"role": "user", "content": "hi"}],
            response_format={"type": "json_object"},
        )

        call_kwargs = mock_litellm.acompletion.call_args[1]
        assert call_kwargs["response_format"] == {"type": "json_object"}

    @patch("src.llm.client.litellm")
    async def test_llm_completion_no_response_format(self, mock_litellm: MagicMock) -> None:
        """Without response_format, kwarg is not passed to litellm.acompletion."""
        mock_litellm.acompletion = AsyncMock(return_value=self._mock_response())

        await llm_completion(
            messages=[{"role": "user", "content": "hi"}],
        )

        call_kwargs = mock_litellm.acompletion.call_args[1]
        assert "response_format" not in call_kwargs
