"""AI endpoints: streaming chat (SSE), human-in-the-loop actions, tools, agents, activity, explain, drafts, evals."""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.ai.agents import describe_agents
from app.ai.llm.router import get_router
from app.ai.orchestrator import run_chat, serialize_action
from app.api.deps import DB, CurrentUser, PortfolioDep, require
from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.core.security import Permission
from app.core.logging import get_logger
from app.db.models import AIAction, AIConversation, AIMessage, AIToolExecution, EvaluationRun, User
from app.db.session import SessionLocal
from app.mcp.registry import ToolContext, registry
from app.rag.evaluation import run_evaluation
from app.schemas.api import ActionEditIn, ChatIn, DraftIn, ExplainIn, SendDraftIn
from app.services.audit import audit
from app.services.communication import draft
from app.services.explain import explain

router = APIRouter(prefix="/ai", tags=["ai"])
log = get_logger(__name__)


@router.post("/chat", dependencies=[Depends(rate_limit("ai", get_settings().ai_rate_limit_per_minute))])
async def chat(body: ChatIn, user: CurrentUser, _=Depends(require(Permission.AI_CHAT))) -> StreamingResponse:
    user_id = user.id

    async def events():
        # The stream outlives request-scoped dependencies, so it owns its session.
        db = SessionLocal()
        try:
            async for ev in run_chat(db, db.get(User, user_id), body.message, body.conversation_id, body.page):
                yield f"data: {json.dumps(ev, default=str)}\n\n"
        except Exception:
            log.exception("chat stream failed")
            yield f"data: {json.dumps({'type': 'error', 'message': 'The assistant hit a problem. Please try again.'})}\n\n"
        finally:
            db.close()

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/status")
def ai_status() -> dict:
    r = get_router()
    return {"provider": r.provider.name, "live": r.is_live, "models": {k.value: v for k, v in r.models.items()},
            "mode": "live" if r.is_live else "demo (grounded deterministic answers)"}


@router.get("/conversations")
def conversations(user: CurrentUser, db: DB) -> list[dict]:
    rows = db.scalars(select(AIConversation).where(AIConversation.user_id == user.id)
                      .order_by(AIConversation.updated_at.desc()).limit(30))
    return [{"id": c.id, "title": c.title, "updated_at": c.updated_at.isoformat()} for c in rows]


@router.get("/conversations/{conv_id}")
def conversation(conv_id: str, user: CurrentUser, db: DB) -> dict:
    conv = db.get(AIConversation, conv_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    msgs = db.scalars(select(AIMessage).where(AIMessage.conversation_id == conv.id).order_by(AIMessage.created_at))
    return {"id": conv.id, "title": conv.title,
            "messages": [{"id": m.id, "role": m.role, "content": m.content, **(m.payload if m.role == "assistant" else {})}
                         for m in msgs]}


# ---- Human-in-the-loop actions ---------------------------------------------
def _action(db, user_id: str, action_id: str) -> AIAction:
    a = db.get(AIAction, action_id)
    if a is None or a.user_id != user_id:
        raise HTTPException(404, "Action not found")
    return a


@router.get("/actions")
def list_actions(user: CurrentUser, db: DB, status: str | None = None) -> list[dict]:
    stmt = select(AIAction).where(AIAction.user_id == user.id).order_by(AIAction.created_at.desc()).limit(50)
    if status:
        stmt = stmt.where(AIAction.status == status)
    return [serialize_action(a) | {"result": a.result} for a in db.scalars(stmt)]


@router.post("/actions/send-draft", status_code=201)
def propose_send(body: SendDraftIn, user: CurrentUser, db: DB) -> dict:
    """Turns an edited draft into a pending 'send email' action that still requires approval."""
    res = registry.call(ToolContext(db, user.id, None, "Communication Agent"), "send_email",
                        to=body.to, subject=body.subject, body=body.body)
    db.commit()
    return serialize_action(db.get(AIAction, res.pending_action_id))


@router.patch("/actions/{action_id}")
def edit_action(action_id: str, body: ActionEditIn, user: CurrentUser, db: DB) -> dict:
    a = _action(db, user.id, action_id)
    if a.status != "pending":
        raise HTTPException(409, "Only pending actions can be edited")
    args = {**a.payload.get("args", {}), **{k: v for k, v in body.payload_args.items() if k in a.payload.get("args", {})}}
    a.payload = {**a.payload, "args": args, "preview": args.get("body", a.payload.get("preview"))}
    db.commit()
    return serialize_action(a)


@router.post("/actions/{action_id}/approve")
def approve(action_id: str, user: CurrentUser, db: DB, _=Depends(require(Permission.AI_APPROVE))) -> dict:
    a = _action(db, user.id, action_id)
    if a.status != "pending":
        raise HTTPException(409, f"Action is already {a.status}")
    a.status, a.decided_at = "approved", datetime.now(UTC)
    audit(db, user.id, "ai_action.approved", actor="user", resource_type="ai_action", resource_id=a.id,
          details={"kind": a.kind, "recipient": a.recipient})
    try:
        a.result = registry.execute_approved(ToolContext(db, user.id, a.conversation_id, "Supervisor"), a)
        a.status = "executed"
    except Exception as exc:
        a.status, a.result = "failed", {"error": type(exc).__name__}
    audit(db, user.id, f"ai_action.{a.status}", actor="ai", resource_type="ai_action", resource_id=a.id)
    db.commit()
    return serialize_action(a) | {"result": a.result}


@router.post("/actions/{action_id}/cancel")
def cancel(action_id: str, user: CurrentUser, db: DB) -> dict:
    a = _action(db, user.id, action_id)
    if a.status != "pending":
        raise HTTPException(409, f"Action is already {a.status}")
    a.status, a.decided_at = "cancelled", datetime.now(UTC)
    audit(db, user.id, "ai_action.cancelled", resource_type="ai_action", resource_id=a.id)
    db.commit()
    return serialize_action(a)


# ---- Transparency ------------------------------------------------------------
@router.get("/tools")
def tools() -> list[dict]:
    return registry.describe()


@router.get("/agents")
def agents() -> list[dict]:
    return describe_agents()


@router.get("/activity")
def activity(user: CurrentUser, db: DB, limit: int = 60) -> list[dict]:
    execs = db.scalars(select(AIToolExecution).where(AIToolExecution.user_id == user.id)
                       .order_by(AIToolExecution.created_at.desc()).limit(min(limit, 200)))
    items = [{"id": e.id, "kind": "tool", "agent": e.agent, "tool": e.tool, "summary": e.summary, "ok": e.ok,
              "latency_ms": e.latency_ms, "at": e.created_at.isoformat()} for e in execs]
    for a in db.scalars(select(AIAction).where(AIAction.user_id == user.id).order_by(AIAction.created_at.desc()).limit(30)):
        label = {"pending": "Waiting for your approval", "executed": "Completed after your approval",
                 "cancelled": "Cancelled by you", "approved": "Approved", "failed": "Failed"}[a.status]
        items.append({"id": a.id, "kind": "action", "agent": "Supervisor", "tool": a.kind, "summary": f"{a.title} — {label}",
                      "ok": a.status != "failed", "status": a.status, "at": (a.decided_at or a.created_at).isoformat()})
    return sorted(items, key=lambda i: i["at"], reverse=True)


@router.post("/explain")
def explain_this(body: ExplainIn, p: PortfolioDep) -> dict:
    return explain(p, body.kind, body.ref)


@router.post("/drafts")
def make_draft(body: DraftIn, p: PortfolioDep) -> dict:
    claim = p.claim_by_ref(body.claim_id) if body.claim_id else None
    policy = p.policy_by_id(body.policy_id) if body.policy_id else None
    return draft(p, body.kind, claim=claim, policy=policy)


# ---- Evaluation (internal) ---------------------------------------------------
@router.get("/evaluations")
def evaluations(db: DB, _=Depends(require(Permission.EVAL_READ))) -> list[dict]:
    rows = db.scalars(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(20))
    return [{"id": r.id, "suite": r.suite, "metrics": r.metrics, "cases": r.cases, "notes": r.notes,
             "created_at": r.created_at.isoformat()} for r in rows]


@router.post("/evaluations/run")
def run_eval(user: CurrentUser, db: DB, _=Depends(require(Permission.EVAL_READ))) -> dict:
    r = run_evaluation(db, user.id)
    return {"id": r.id, "suite": r.suite, "metrics": r.metrics, "cases": r.cases, "created_at": r.created_at.isoformat()}
