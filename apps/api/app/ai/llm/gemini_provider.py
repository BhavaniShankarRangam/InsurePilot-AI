"""Google Gemini provider (Generative Language REST API)."""

import json
from collections.abc import AsyncIterator

import httpx

from app.ai.llm.base import LLMError, LLMRequest, LLMResult

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str) -> None:
        self.headers = {"x-goog-api-key": api_key}

    def _body(self, req: LLMRequest) -> dict:
        body: dict = {
            "systemInstruction": {"parts": [{"text": req.system}]},
            "contents": [
                {"role": "model" if m.role == "assistant" else "user", "parts": [{"text": m.content}]}
                for m in req.messages
            ],
            "generationConfig": {"maxOutputTokens": req.max_tokens},
        }
        if req.json_schema:
            body["generationConfig"]["responseMimeType"] = "application/json"
        return body

    async def complete(self, req: LLMRequest, model: str) -> LLMResult:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{_BASE}/{model}:generateContent", headers=self.headers, json=self._body(req))
        if resp.status_code >= 400:
            raise LLMError(f"Gemini API error {resp.status_code}")
        data = resp.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        usage = data.get("usageMetadata", {})
        return LLMResult(text="".join(p.get("text", "") for p in parts), model=model, provider=self.name,
                         input_tokens=usage.get("promptTokenCount", 0), output_tokens=usage.get("candidatesTokenCount", 0))

    async def stream(self, req: LLMRequest, model: str) -> AsyncIterator[str]:
        url = f"{_BASE}/{model}:streamGenerateContent?alt=sse"
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, headers=self.headers, json=self._body(req)) as resp:
                if resp.status_code >= 400:
                    raise LLMError(f"Gemini API error {resp.status_code}")
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    for part in json.loads(line[6:]).get("candidates", [{}])[0].get("content", {}).get("parts", []):
                        if part.get("text"):
                            yield part["text"]
