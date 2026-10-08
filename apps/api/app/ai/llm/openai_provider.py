"""OpenAI provider (Chat Completions over REST)."""

import json
from collections.abc import AsyncIterator

import httpx

from app.ai.llm.base import LLMError, LLMRequest, LLMResult

_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str) -> None:
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def _body(self, req: LLMRequest, model: str, stream: bool) -> dict:
        body: dict = {
            "model": model,
            "max_completion_tokens": req.max_tokens,
            "messages": [{"role": "system", "content": req.system}]
            + [{"role": m.role, "content": m.content} for m in req.messages],
            "stream": stream,
        }
        if req.json_schema:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "output", "schema": req.json_schema}}
        return body

    async def complete(self, req: LLMRequest, model: str) -> LLMResult:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(_URL, headers=self.headers, json=self._body(req, model, False))
        if resp.status_code >= 400:
            raise LLMError(f"OpenAI API error {resp.status_code}")
        data = resp.json()
        usage = data.get("usage", {})
        return LLMResult(text=data["choices"][0]["message"]["content"] or "", model=model, provider=self.name,
                         input_tokens=usage.get("prompt_tokens", 0), output_tokens=usage.get("completion_tokens", 0))

    async def stream(self, req: LLMRequest, model: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", _URL, headers=self.headers, json=self._body(req, model, True)) as resp:
                if resp.status_code >= 400:
                    raise LLMError(f"OpenAI API error {resp.status_code}")
                async for line in resp.aiter_lines():
                    if not line.startswith("data: ") or line.endswith("[DONE]"):
                        continue
                    delta = json.loads(line[6:])["choices"][0]["delta"].get("content")
                    if delta:
                        yield delta
