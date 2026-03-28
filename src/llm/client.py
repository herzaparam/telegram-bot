"""LLM wrapper with retry, fallback, and deterministic failure handling.

All LLM calls go through llm_completion(). It never raises -- returns
LLM_UNAVAILABLE sentinel when all models fail.
"""

import time
from dataclasses import dataclass

import litellm
import structlog

from src.config import settings
from src.monitoring.metrics import LLM_CALL_COUNT, LLM_CALL_DURATION

log = structlog.get_logger()


@dataclass(frozen=True)
class LLMResult:
    """Result from an LLM completion call."""

    content: str
    model_used: str
    is_fallback: bool = False


LLM_UNAVAILABLE = LLMResult(
    content="",
    model_used="none",
    is_fallback=True,
)


async def llm_completion(
    messages: list[dict[str, str]],
    model: str | None = None,
    fallback_models: list[str] | None = None,
    num_retries: int | None = None,
    timeout: int | None = None,
    response_format: dict[str, str] | None = None,
) -> LLMResult:
    """Call LLM with retry + model fallback.

    Returns LLM_UNAVAILABLE on total failure -- never raises.
    """
    model = model or settings.llm_primary_model
    fallbacks = fallback_models or [settings.llm_fallback_model]
    retries = num_retries if num_retries is not None else settings.llm_max_retries
    tout = timeout or settings.llm_timeout

    kwargs: dict[str, object] = {
        "model": model,
        "messages": messages,
        "num_retries": retries,
        "timeout": tout,
        "fallbacks": fallbacks,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format

    start = time.monotonic()
    try:
        response = await litellm.acompletion(**kwargs)
        duration = time.monotonic() - start
        model_used = response.model or model
        LLM_CALL_COUNT.labels(model=model_used, is_fallback="false").inc()
        LLM_CALL_DURATION.labels(model=model_used).observe(duration)
        return LLMResult(
            content=response.choices[0].message.content or "",
            model_used=model_used,
        )
    except Exception as exc:
        duration = time.monotonic() - start
        LLM_CALL_COUNT.labels(model="none", is_fallback="true").inc()
        LLM_CALL_DURATION.labels(model=model).observe(duration)
        log.error(
            "llm_all_models_failed",
            model=model,
            fallbacks=fallbacks,
            error=str(exc),
        )
        return LLM_UNAVAILABLE
