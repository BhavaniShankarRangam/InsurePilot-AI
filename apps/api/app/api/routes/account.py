"""User profile, onboarding, notifications, privacy center and observability metrics."""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select

from app.api.deps import DB, CurrentUser, PortfolioDep, require
from app.api.routes.auth import user_out
from app.core.config import get_settings
from app.core.security import Permission
from app.db.models import (
    AIAction,
    AIToolExecution,
    AuditLog,
    Consent,
    Integration,
    LLMUsage,
    Notification,
)
from app.schemas.api import ConsentIn, PreferencesIn, UserOut
from app.services import serializers as ser
from app.services.audit import audit

router = APIRouter(tags=["account"])


@router.patch("/users/me", response_model=UserOut)
def update_me(body: PreferencesIn, user: CurrentUser, db: DB) -> UserOut:
    prefs = dict(user.preferences or {})
    for k in ("theme", "reduced_motion", "low_power_3d"):
        v = getattr(body, k)
        if v is not None:
            prefs[k] = v
    user.preferences = prefs
    if body.preferred_name:
        user.preferred_name = body.preferred_name
    db.commit()
    return user_out(user)


@router.post("/users/me/onboarding", response_model=UserOut)
def complete_onboarding(user: CurrentUser, db: DB) -> UserOut:
    user.onboarding_complete = True
    audit(db, user.id, "onboarding.completed")
    db.commit()
    return user_out(user)


# ---- Notifications -----------------------------------------------------------
@router.get("/notifications")
def notifications(p: PortfolioDep) -> list[dict]:
    now = datetime.now(UTC)
    return [ser.notification_out(n) for n in p.notifications
            if not n.snoozed_until or n.snoozed_until.replace(tzinfo=n.snoozed_until.tzinfo or UTC) < now]


@router.post("/notifications/{nid}/read")
def mark_read(nid: str, user: CurrentUser, db: DB) -> dict:
    n = db.get(Notification, nid)
    if n is None or n.user_id != user.id:
        raise HTTPException(404, "Not found")
    n.read = True
    db.commit()
    return {"ok": True}


@router.post("/notifications/read-all")
def read_all(user: CurrentUser, db: DB) -> dict:
    for n in db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.read.is_(False))):
        n.read = True
    db.commit()
    return {"ok": True}


# ---- Privacy center -----------------------------------------------------------
@router.get("/privacy")
def privacy(p: PortfolioDep, db: DB) -> dict:
    uid = p.user.id
    tool_calls = db.scalar(select(func.count()).select_from(AIToolExecution).where(AIToolExecution.user_id == uid)) or 0
    approvals = db.scalar(select(func.count()).select_from(AIAction).where(AIAction.user_id == uid)) or 0
    return {
        "data_inventory": [
            {"kind": "Policies", "count": len(p.policies), "purpose": "Explain coverage, detect gaps and renewals"},
            {"kind": "Claims", "count": len(p.claims), "purpose": "Track claims and deadlines"},
            {"kind": "Documents", "count": len(p.documents), "purpose": "Answer questions with citations"},
            {"kind": "Health data (EOBs, bills, authorizations)", "count": len(p.eobs) + len(p.bills) + len(p.authorizations),
             "purpose": "Find billing discrepancies and navigate benefits", "sensitive": True},
            {"kind": "Assets (vehicles, property, pets)", "count": len(p.assets), "purpose": "Link policies to what they protect"},
        ],
        "consents": [{"id": c.id, "scope": c.scope, "purpose": c.purpose, "granted": c.granted,
                      "granted_at": c.granted_at.isoformat() if c.granted else None}
                     for c in db.scalars(select(Consent).where(Consent.user_id == uid))],
        "integrations": [{"id": i.id, "provider": i.provider, "kind": i.kind, "status": i.status, "data_shared": i.data_shared,
                          "connected_on": i.connected_on.isoformat() if i.connected_on else None}
                         for i in db.scalars(select(Integration).where(Integration.user_id == uid))],
        "ai_activity": {"tool_calls": tool_calls, "actions_requested": approvals},
        "shared_data": [{"recipient": a.recipient, "items": a.data_shared, "date": (a.decided_at or a.created_at).isoformat()}
                        for a in db.scalars(select(AIAction).where(AIAction.user_id == uid, AIAction.status == "executed"))],
        "retention": "Documents are kept until you delete them. AI conversation history is kept for 12 months.",
    }


@router.patch("/privacy/consents/{cid}")
def set_consent(cid: str, body: ConsentIn, user: CurrentUser, db: DB) -> dict:
    c = db.get(Consent, cid)
    if c is None or c.user_id != user.id:
        raise HTTPException(404, "Consent not found")
    c.granted = body.granted
    now = datetime.now(UTC)
    if body.granted:
        c.granted_at, c.revoked_at = now, None
    else:
        c.revoked_at = now
    audit(db, user.id, "consent.granted" if body.granted else "consent.revoked", resource_type="consent", resource_id=c.id,
          details={"scope": c.scope})
    db.commit()
    return {"id": c.id, "granted": c.granted}


@router.delete("/privacy/integrations/{iid}", status_code=204)
def revoke_integration(iid: str, user: CurrentUser, db: DB) -> None:
    i = db.get(Integration, iid)
    if i is None or i.user_id != user.id:
        raise HTTPException(404, "Integration not found")
    i.status = "revoked"
    audit(db, user.id, "integration.revoked", resource_type="integration", resource_id=i.id, details={"provider": i.provider})
    db.commit()


@router.get("/privacy/export")
def export_data(p: PortfolioDep, db: DB) -> Response:
    data = {
        "user": {"name": p.user.full_name, "email": p.user.email},
        "policies": [ser.policy_detail(p, pol) for pol in p.policies],
        "claims": [ser.claim_detail(c, []) for c in p.claims],
        "documents": [ser.document_out(d) for d in p.documents],
        "exported_at": datetime.now(UTC).isoformat(),
    }
    audit(db, p.user.id, "privacy.export")
    db.commit()
    return Response(json.dumps(data, indent=2, default=str), media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=insurepilot-export.json"})


@router.delete("/privacy/account", status_code=204)
def delete_account(user: CurrentUser, db: DB, response: Response) -> Response:
    audit(db, user.id, "privacy.account_deleted", details={"is_demo": user.is_demo})
    db.delete(user)
    db.commit()
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    response.status_code = 204
    return response


@router.get("/audit")
def audit_log(user: CurrentUser, db: DB, limit: int = 50) -> list[dict]:
    rows = db.scalars(select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.created_at.desc()).limit(min(limit, 200)))
    return [{"action": r.action, "actor": r.actor, "resource_type": r.resource_type, "at": r.created_at.isoformat(),
             "details": r.details} for r in rows]


# ---- Observability -------------------------------------------------------------
@router.get("/admin/metrics", dependencies=[Depends(require(Permission.EVAL_READ))])
def metrics(db: DB) -> dict:
    usage = db.execute(select(LLMUsage.provider, LLMUsage.model, LLMUsage.task, func.count(), func.sum(LLMUsage.input_tokens),
                              func.sum(LLMUsage.output_tokens), func.sum(LLMUsage.cost_usd), func.avg(LLMUsage.latency_ms),
                              func.sum(func.cast(LLMUsage.error.is_not(None), type_=LLMUsage.latency_ms.type)))
                       .group_by(LLMUsage.provider, LLMUsage.model, LLMUsage.task)).all()
    tools = db.execute(select(AIToolExecution.tool, func.count(), func.avg(AIToolExecution.latency_ms),
                              func.sum(func.cast(AIToolExecution.ok.is_(False), type_=AIToolExecution.latency_ms.type)))
                       .group_by(AIToolExecution.tool)).all()
    return {
        "llm": [{"provider": r[0], "model": r[1], "task": r[2], "calls": r[3], "input_tokens": r[4] or 0,
                 "output_tokens": r[5] or 0, "cost_usd": round(r[6] or 0, 6), "avg_latency_ms": round(r[7] or 0),
                 "errors": r[8] or 0} for r in usage],
        "tools": [{"tool": r[0], "calls": r[1], "avg_latency_ms": round(r[2] or 0), "failures": r[3] or 0} for r in tools],
    }
