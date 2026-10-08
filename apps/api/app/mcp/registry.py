"""MCP-style tool registry with permission tiers and human-in-the-loop gating.

Sensitivity tiers:
- read:      read-only data access; executes immediately
- draft:     creates internal drafts (claim drafts, packets); executes, nothing leaves the system
- external:  affects the outside world (submit, send, purchase, share); NEVER executes directly —
             it creates a pending AIAction that the user must approve.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AIAction, AIToolExecution


@dataclass
class ToolContext:
    db: Session
    user_id: str
    conversation_id: str | None = None
    agent: str = "system"


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    sensitivity: str  # read | draft | external
    handler: Callable[..., Any]
    summarize: Callable[[dict, Any], str] = field(default=lambda args, result: "")
    approval: Callable[[ToolContext, dict], dict] | None = None  # builds the approval card for external tools


@dataclass
class ToolResult:
    tool: str
    ok: bool
    data: Any
    summary: str
    pending_action_id: str | None = None


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def all(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def describe(self) -> list[dict]:
        return [{"name": t.name, "description": t.description, "input_schema": t.input_schema,
                 "sensitivity": t.sensitivity, "requires_approval": t.sensitivity == "external"} for t in self._tools.values()]

    def call(self, ctx: ToolContext, name: str, **args: Any) -> ToolResult:
        spec = self._tools.get(name)
        if spec is None:
            return ToolResult(name, False, None, f"Unknown tool {name}")
        start = time.perf_counter()

        if spec.sensitivity == "external":
            card = spec.approval(ctx, args) if spec.approval else {}
            action = AIAction(
                user_id=ctx.user_id, conversation_id=ctx.conversation_id, kind=name,
                title=card.get("title", name.replace("_", " ").title()), what=card.get("what", ""), why=card.get("why", ""),
                data_shared=card.get("data_shared", []), recipient=card.get("recipient"),
                payload={"tool": name, "args": args, **card.get("payload", {})}, risk_level=card.get("risk", "high"),
            )
            ctx.db.add(action)
            ctx.db.flush()
            summary = f"Prepared “{action.title}” — waiting for your approval"
            self._log(ctx, name, summary, True, start)
            return ToolResult(name, True, {"action_id": action.id, "status": "pending_approval"}, summary, action.id)

        try:
            data = spec.handler(ctx, **args)
            summary = spec.summarize(args, data) or f"Ran {name}"
            self._log(ctx, name, summary, True, start)
            return ToolResult(name, True, data, summary)
        except Exception as exc:  # tool failures are reported, not raised, so agents can fall back
            self._log(ctx, name, f"{name} failed", False, start)
            return ToolResult(name, False, None, f"{name} failed: {type(exc).__name__}")

    def execute_approved(self, ctx: ToolContext, action: AIAction) -> Any:
        """Run an external tool after the user explicitly approved its AIAction."""
        spec = self._tools[action.payload["tool"]]
        start = time.perf_counter()
        data = spec.handler(ctx, **action.payload.get("args", {}))
        self._log(ctx, spec.name, f"Executed approved action: {action.title}", True, start)
        return data

    @staticmethod
    def _log(ctx: ToolContext, tool: str, summary: str, ok: bool, start: float) -> None:
        ctx.db.add(AIToolExecution(user_id=ctx.user_id, conversation_id=ctx.conversation_id, agent=ctx.agent, tool=tool,
                                   summary=summary[:240], ok=ok, latency_ms=int((time.perf_counter() - start) * 1000)))


registry = ToolRegistry()
