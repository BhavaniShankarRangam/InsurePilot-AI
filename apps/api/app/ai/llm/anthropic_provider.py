"""Anthropic Claude provider (official SDK)."""

import json
from collections.abc import AsyncIterator

import anthropic

from app.ai.llm.base import LLMError, LLMRequest, LLMResult

# Models with server-side refusal fallbacks (Claude API only).
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, enable_fallbacks: bool = True) -> None:
        self.client = anthropic.AsyncAnthropic(api_key=api_key or None, timeout=120.0)
        self.enable_fallbacks = enable_fallbacks

    def _params(self, req: LLMRequest, model: str) -> dict:
        params: dict = {
            "model": model,
            "max_tokens": req.max_tokens,
            "system": [{"type": "text", "text": req.system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
        }
        if model.startswith("claude-opus-5-5"):
            params["output_config"] = {"effort": "medium"}
        if req.json_schema:
            params.setdefault("output_config", {})["format"] = {"type": "json_schema", "schema": req.json_schema}
        return params

    def _use_fallbacks(self, model: str) -> bool:
        return self.enable_fallbacks and model in _FALLBACK_MODELS

    async def complete(self, req: LLMRequest, model: str) -> LLMResult:
        params = self._params(req, model)
        try:
            if self._use_fallbacks(model):
                async with self.client.beta.messages.stream(
                    **params, betas=[_FALLBACK_BETA], fallbacks="default"
                ) as stream:
                    msg = await stream.get_final_message()
            else:
                async with self.client.messages.stream(**params) as stream:
                    msg = await stream.get_final_message()
        except anthropic.RateLimitError as exc:
            raise LLMError("Claude rate limit reached") from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Claude API error {exc.status_code}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("Could not reach Claude API") from exc

        refused = msg.stop_reason == "refusal"
        text = "".join(b.text for b in msg.content if b.type == "text")
        if req.json_schema and text:
            json.loads(text)  # validate structured output
        return LLMResult(text=text, model=msg.model, provider=self.name, input_tokens=msg.usage.input_tokens,
                         output_tokens=msg.usage.output_tokens, refused=refused)

    async def stream(self, req: LLMRequest, model: str) -> AsyncIterator[str]:
        params = self._params(req, model)
        try:
            if self._use_fallbacks(model):
                ctx = self.client.beta.messages.stream(**params, betas=[_FALLBACK_BETA], fallbacks="default")
            else:
                ctx = self.client.messages.stream(**params)
            async with ctx as stream:
                async for text in stream.text_stream:
                    yield text
                final = await stream.get_final_message()
                if final.stop_reason == "refusal":
                    raise LLMError("refusal")
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Claude API error {exc.status_code}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("Could not reach Claude API") from exc
