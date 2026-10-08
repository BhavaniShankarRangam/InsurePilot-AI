"""Agent contract: tools, permissions, structured output, confidence, reasoning summary, fallback, escalation."""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.llm.base import ChatMessage, Task
from app.mcp.registry import ToolContext, ToolResult, registry
from app.services.portfolio import Portfolio


class Confidence(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    NEEDS_VERIFICATION = "needs_verification"
    HUMAN_REVIEW = "human_review"


class Card(BaseModel):
    type: str
    data: dict | list


class AgentOutput(BaseModel):
    """Structured output every agent returns. `answer` is a grounded draft the composer may rephrase."""

    agent: str
    answer: str
    task: Task = Task.SUMMARY
    confidence: Confidence = Confidence.MODERATE
    reasoning_summary: str = ""
    cards: list[Card] = Field(default_factory=list)
    citations: list[dict] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    data_used: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    policy_specific: bool = False
    escalate: bool = False


@dataclass
class Entities:
    category: str | None = None
    categories: list[str] = field(default_factory=list)
    claim_ref: str | None = None
    amount: float | None = None
    provider: str | None = None
    procedure: str | None = None


@dataclass
class AgentContext:
    db: Session
    user_id: str
    conversation_id: str | None
    message: str
    history: list[ChatMessage]
    page: dict
    portfolio: Portfolio
    entities: Entities
    memory: dict
    emit: Callable[[dict], None] = lambda e: None

    @property
    def lower(self) -> str:
        return self.message.lower()


class BaseAgent:
    name: str = "Agent"
    description: str = ""
    tools: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ("data:read_own",)
    escalation_rules: tuple[str, ...] = ()

    def __init__(self) -> None:
        self._used: list[str] = []
        self._citations: list[dict] = []

    # --- helpers ---------------------------------------------------------
    def call(self, ctx: AgentContext, tool: str, **args: Any) -> ToolResult:
        if tool not in self.tools:
            raise PermissionError(f"{self.name} is not permitted to use {tool}")
        tctx = ToolContext(ctx.db, ctx.user_id, ctx.conversation_id, self.name)
        result = registry.call(tctx, tool, **args)
        self._used.append(tool)
        ctx.emit({"type": "tool", "tool": tool, "label": result.summary, "ok": result.ok})
        return result

    def status(self, ctx: AgentContext, state: str, label: str) -> None:
        ctx.emit({"type": "status", "state": state, "label": label})

    def search(self, ctx: AgentContext, query: str, category: str | None = None, claim_id: str | None = None,
               top_k: int = 3, min_score: float = 0.35) -> list[dict]:
        self.status(ctx, "retrieving", "Searching your policy documents")
        res = self.call(ctx, "search_policy_documents", query=query, category=category, claim_id=claim_id, top_k=top_k)
        hits = [h for h in (res.data or []) if h["score"] >= min_score]
        for h in hits:
            if all(c["chunk_id"] != h["citation"]["chunk_id"] for c in self._citations):
                self._citations.append(h["citation"])
        return hits

    def cite(self, hit: dict) -> str:
        idx = next(i for i, c in enumerate(self._citations) if c["chunk_id"] == hit["citation"]["chunk_id"])
        return f"[{idx + 1}]"

    def evidence_from_citations(self) -> list[str]:
        return [f"[{i + 1}] {c['label']}: {c['snippet']}" for i, c in enumerate(self._citations)]

    def output(self, **kwargs: Any) -> AgentOutput:
        kwargs.setdefault("tools_used", list(dict.fromkeys(self._used)))
        kwargs.setdefault("citations", self._citations)
        ev = kwargs.pop("evidence", [])
        kwargs["evidence"] = ev + self.evidence_from_citations()
        return AgentOutput(agent=self.name, **kwargs)

    def fallback(self, ctx: AgentContext, reason: str = "") -> AgentOutput:
        return self.output(
            answer="I don't have enough verified information to answer this confidently."
                   + (f" {reason}" if reason else ""),
            confidence=Confidence.NEEDS_VERIFICATION,
            reasoning_summary="No structured data or document passage supported an answer.",
            suggestions=["Upload the relevant document", "Tell me more details", "Talk to a licensed professional"],
            limitations=["No verified source found"],
        )

    def run(self, ctx: AgentContext) -> AgentOutput:  # pragma: no cover - interface
        raise NotImplementedError

    def safe_run(self, ctx: AgentContext) -> AgentOutput:
        self._used, self._citations = [], []
        try:
            return self.run(ctx)
        except LookupError:
            return self.fallback(ctx, "I couldn't find the policy or claim you mentioned.")
