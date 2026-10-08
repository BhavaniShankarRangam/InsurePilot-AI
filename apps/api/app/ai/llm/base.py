from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class Tier(StrEnum):
    SMALL = "small"  # classification, extraction, intent, short summaries
    LARGE = "large"  # coverage reasoning, claims analysis, comparison, planning


class Task(StrEnum):
    INTENT = "intent"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    SUMMARY = "summary"
    COVERAGE_EXPLANATION = "coverage_explanation"
    CLAIMS_REASONING = "claims_reasoning"
    POLICY_COMPARISON = "policy_comparison"
    CROSS_DOCUMENT = "cross_document"
    PLANNING = "planning"
    DRAFTING = "drafting"


TASK_TIER: dict[Task, Tier] = {
    Task.INTENT: Tier.SMALL,
    Task.EXTRACTION: Tier.SMALL,
    Task.CLASSIFICATION: Tier.SMALL,
    Task.SUMMARY: Tier.SMALL,
    Task.COVERAGE_EXPLANATION: Tier.LARGE,
    Task.CLAIMS_REASONING: Tier.LARGE,
    Task.POLICY_COMPARISON: Tier.LARGE,
    Task.CROSS_DOCUMENT: Tier.LARGE,
    Task.PLANNING: Tier.LARGE,
    Task.DRAFTING: Tier.LARGE,
}


@dataclass
class ChatMessage:
    role: str  # user | assistant
    content: str


@dataclass
class LLMRequest:
    system: str
    messages: list[ChatMessage]
    max_tokens: int = 4096
    json_schema: dict | None = None  # request structured JSON output
    fallback_text: str = ""  # grounded deterministic draft (used by the mock provider)


@dataclass
class LLMResult:
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    refused: bool = False
    meta: dict = field(default_factory=dict)


class LLMProvider(Protocol):
    name: str

    async def complete(self, req: LLMRequest, model: str) -> LLMResult: ...

    def stream(self, req: LLMRequest, model: str) -> AsyncIterator[str]: ...


class LLMError(RuntimeError):
    pass
