"""Cost-aware model routing: small models for classification/extraction, large models for reasoning."""

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy.orm import Session

from app.ai.llm.base import TASK_TIER, LLMError, LLMProvider, LLMRequest, LLMResult, Task, Tier
from app.ai.llm.mock_provider import MockProvider
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import LLMUsage

log = get_logger(__name__)

DEFAULT_MODELS: dict[str, dict[Tier, str]] = {
    "anthropic": {Tier.LARGE: "claude-opus-5-5", Tier.SMALL: "claude-haiku-4-5"},
    "openai": {Tier.LARGE: "gpt-5", Tier.SMALL: "gpt-5-mini"},
    "gemini": {Tier.LARGE: "gemini-2.5-pro", Tier.SMALL: "gemini-2.5-flash"},
    "mock": {Tier.LARGE: "mock-large", Tier.SMALL: "mock-small"},
}

# USD per 1M tokens (input, output). Override as pricing changes.
PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


@dataclass
class Route:
    provider: LLMProvider
    model: str
    tier: Tier


class ModelRouter:
    def __init__(self) -> None:
        s = get_settings()
        self.provider_name = s.llm_provider
        self.provider = self._build(s)
        defaults = DEFAULT_MODELS[self.provider.name]
        self.models = {
            Tier.LARGE: s.llm_model_large or defaults[Tier.LARGE],
            Tier.SMALL: s.llm_model_small or defaults[Tier.SMALL],
        }
        self.fallback = MockProvider()

    @staticmethod
    def _build(s) -> LLMProvider:
        if s.llm_provider == "anthropic" and s.anthropic_api_key:
            from app.ai.llm.anthropic_provider import AnthropicProvider

            return AnthropicProvider(s.anthropic_api_key, s.anthropic_enable_fallbacks)
        if s.llm_provider == "openai" and s.openai_api_key:
            from app.ai.llm.openai_provider import OpenAIProvider

            return OpenAIProvider(s.openai_api_key)
        if s.llm_provider == "gemini" and s.gemini_api_key:
            from app.ai.llm.gemini_provider import GeminiProvider

            return GeminiProvider(s.gemini_api_key)
        return MockProvider()

    @property
    def is_live(self) -> bool:
        return self.provider.name != "mock"

    def route(self, task: Task) -> Route:
        tier = TASK_TIER[task]
        return Route(self.provider, self.models[tier], tier)

    async def complete(self, task: Task, req: LLMRequest, db: Session | None = None, user_id: str | None = None) -> LLMResult:
        r = self.route(task)
        start = time.perf_counter()
        try:
            result = await r.provider.complete(req, r.model)
            if result.refused:
                raise LLMError("refusal")
        except LLMError as exc:
            log.warning("llm call failed; using grounded fallback", extra={"fields": {"task": task, "error": str(exc)}})
            self._record(db, user_id, r, task, 0, 0, start, str(exc))
            return await self.fallback.complete(req, "fallback")
        self._record(db, user_id, r, task, result.input_tokens, result.output_tokens, start, None)
        return result

    async def stream(self, task: Task, req: LLMRequest, db: Session | None = None, user_id: str | None = None) -> AsyncIterator[str]:
        r = self.route(task)
        start = time.perf_counter()
        emitted = 0
        try:
            async for piece in r.provider.stream(req, r.model):
                emitted += len(piece)
                yield piece
        except LLMError as exc:
            log.warning("llm stream failed", extra={"fields": {"task": task, "error": str(exc)}})
            self._record(db, user_id, r, task, 0, 0, start, str(exc))
            if emitted == 0:
                async for piece in self.fallback.stream(req, "fallback"):
                    yield piece
            return
        self._record(db, user_id, r, task, len(req.system + str(req.messages)) // 4, emitted // 4, start, None)

    def _record(self, db, user_id, r: Route, task: Task, tin: int, tout: int, start: float, error: str | None) -> None:
        if db is None:
            return
        price_in, price_out = PRICING.get(r.model, (0.0, 0.0))
        db.add(LLMUsage(user_id=user_id, provider=r.provider.name, model=r.model, task=str(task), input_tokens=tin,
                        output_tokens=tout, cost_usd=round((tin * price_in + tout * price_out) / 1_000_000, 6),
                        latency_ms=int((time.perf_counter() - start) * 1000), error=error))


@lru_cache
def get_router() -> ModelRouter:
    return ModelRouter()
