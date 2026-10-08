"""MCP server exposing the InsurePilot tool catalog to any MCP client (Claude Desktop, IDEs, other agents).

Run:  python -m app.mcp.server            (stdio)
      python -m app.mcp.server --http     (streamable HTTP)

Tools act on behalf of INSUREPILOT_USER_EMAIL (defaults to the demo profile). External tools
(submit_claim, send_email, ...) are never executed here — they create pending approvals that the
user must confirm in the InsurePilot app.
"""

import inspect
import json
import os
import sys
from typing import Any

from mcp.server.mcpserver import MCPServer
from sqlalchemy import select

import app.mcp.tools  # noqa: F401  (register tools)
from app.db.models import User
from app.db.session import SessionLocal, init_db
from app.mcp.registry import ToolContext, ToolSpec, registry


def _resolve_user_id() -> str:
    from app.demo.seed import DEMO_EMAIL, seed_demo

    email = os.getenv("INSUREPILOT_USER_EMAIL", DEMO_EMAIL)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None and email == DEMO_EMAIL:
            user = seed_demo(db)
        if user is None:
            raise SystemExit(f"No InsurePilot user with email {email}")
        return user.id


def _wrap(spec: ToolSpec, user_id: str):
    params = [p for name, p in inspect.signature(spec.handler).parameters.items() if name != "ctx"]

    def tool(**kwargs: Any) -> str:
        with SessionLocal() as db:
            result = registry.call(ToolContext(db, user_id, None, "MCP client"), spec.name, **kwargs)
            db.commit()
        payload = {"ok": result.ok, "summary": result.summary, "data": result.data}
        if result.pending_action_id:
            payload["note"] = "This action requires the user's approval in the InsurePilot app before it runs."
        return json.dumps(payload, default=str)

    tool.__name__ = spec.name
    tool.__doc__ = spec.description
    tool.__signature__ = inspect.Signature(params, return_annotation=str)  # type: ignore[attr-defined]
    return tool


def build_server() -> MCPServer:
    init_db()
    user_id = _resolve_user_id()
    server = MCPServer(
        name="insurepilot",
        title="InsurePilot AI",
        instructions="Insurance tools for one user's policies, claims, health benefits and documents. "
                     "Never present uncertain results as facts. External actions require user approval.",
    )
    for spec in registry.all():
        server.add_tool(_wrap(spec, user_id), name=spec.name, description=spec.description)
    return server


if __name__ == "__main__":
    build_server().run("streamable-http" if "--http" in sys.argv else "stdio")
