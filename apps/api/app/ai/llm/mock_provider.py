"""Offline provider for demo mode and tests.

Agents always build a grounded, deterministic draft from tool results and retrieved
evidence. The mock provider returns that draft as-is (streamed word by word), so the
product is fully functional without API keys and never fabricates content.
"""

import asyncio
import re
from collections.abc import AsyncIterator

from app.ai.llm.base import LLMRequest, LLMResult


class MockProvider:
    name = "mock"

    async def complete(self, req: LLMRequest, model: str) -> LLMResult:
        text = req.fallback_text or "I don't have enough verified information to answer this confidently."
        return LLMResult(text=text, model=model, provider=self.name, input_tokens=len(req.system) // 4,
                         output_tokens=len(text) // 4)

    async def stream(self, req: LLMRequest, model: str) -> AsyncIterator[str]:
        text = req.fallback_text or "I don't have enough verified information to answer this confidently."
        for piece in re.findall(r"\S+\s*|\n", text):
            yield piece
            await asyncio.sleep(0.012)
