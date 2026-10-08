"""Dashboard, wallet, policies, renewals, insights, analytics, search and the Digital Twin graph."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DB, CurrentUser, PortfolioDep
from app.schemas.api import FindingDecisionIn, SimulateIn
from app.services import serializers as ser
from app.services.analytics import insights
from app.services.digital_twin import graph_view
from app.services.health_score import daily_summary, detect_risks, health_score, home_layout, potential_savings
from app.services.policy_intel import (
    compare,
    coverage_map,
    explain_policy,
    premium_change,
    renewal_autopilot,
    simulate,
)
from app.services.search import global_search

router = APIRouter(tags=["portfolio"])


def _visible_findings(user, findings) -> list[dict]:
    prefs = user.preferences or {}
    hidden = set(prefs.get("ignored_findings", []))
    snoozed = {k: v for k, v in prefs.get("snoozed_findings", {}).items() if datetime.fromisoformat(v) > datetime.now(UTC)}
    return [f.to_dict() for f in findings if f.id not in hidden and f.id not in snoozed]


@router.get("/dashboard")
def dashboard(p: PortfolioDep) -> dict:
    risks = detect_risks(p)
    visible = _visible_findings(p.user, risks)
    savings = potential_savings(p)
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    return {
        "greeting": greeting,
        "name": p.user.preferred_name or p.user.full_name.split()[0],
        "daily_summary": daily_summary(p),
        "health_score": health_score(p),
        "stats": {
            "actions_needed": sum(1 for r in visible if r["severity"] == "attention"),
            "renewals_upcoming": sum(1 for pol in p.active_policies if 0 <= (pol.expiration_date - datetime.now().date()).days <= 45),
            "potential_savings": savings["total"],
            "active_claims": len(p.open_claims),
        },
        "savings": savings,
        "layout": home_layout(p),
        "actions": visible,
        "policies": [ser.policy_card(p, pol) for pol in p.policies],
        "claims": [ser.claim_card(c) for c in p.claims],
        "authorizations": [{"id": a.id, "procedure": a.procedure_name, "status": a.status,
                            "decision_due": a.decision_due.isoformat() if a.decision_due else None,
                            "missing": [r["item"] for r in a.requirements if r.get("status") == "missing"]}
                           for a in p.authorizations],
        "empty_categories": [c for c in ("renters", "commercial") if not p.policy(c)],
    }


@router.get("/wallet")
def wallet(p: PortfolioDep) -> list[dict]:
    return [ser.policy_card(p, pol) for pol in p.policies]


@router.get("/policies")
def list_policies(p: PortfolioDep, category: str | None = None, status: str | None = None) -> list[dict]:
    return [ser.policy_card(p, pol) for pol in p.policies
            if (category is None or pol.category == category) and (status is None or pol.status == status)]


@router.get("/policies/coverage-map")
def get_coverage_map(p: PortfolioDep) -> list[dict]:
    return coverage_map(p)


@router.get("/policies/{policy_id}")
def get_policy(policy_id: str, p: PortfolioDep) -> dict:
    pol = p.policy_by_id(policy_id)
    if pol is None:
        raise HTTPException(404, "Policy not found")
    return {**ser.policy_detail(p, pol), "explainer": explain_policy(pol)}


@router.get("/policies/{policy_id}/premium-change")
def get_premium_change(policy_id: str, p: PortfolioDep) -> dict:
    pol = p.policy_by_id(policy_id)
    if pol is None:
        raise HTTPException(404, "Policy not found")
    return premium_change(pol)


@router.get("/renewals")
def renewals(p: PortfolioDep) -> list[dict]:
    out = []
    for pol in sorted(p.active_policies, key=lambda x: x.expiration_date):
        if (pol.expiration_date - datetime.now().date()).days <= 120:
            out.append(renewal_autopilot(p, pol) | {"category": pol.category, "carrier": pol.carrier.name})
    return out


@router.get("/quotes/compare")
def compare_quotes(p: PortfolioDep, category: str = "auto") -> dict:
    return compare(p, category)


@router.get("/insights/actions")
def action_center(p: PortfolioDep) -> list[dict]:
    return _visible_findings(p.user, detect_risks(p))


@router.post("/insights/actions/{finding_id}")
def decide_finding(finding_id: str, body: FindingDecisionIn, user: CurrentUser, db: DB) -> dict:
    prefs = dict(user.preferences or {})
    if body.decision == "ignore":
        prefs["ignored_findings"] = sorted(set(prefs.get("ignored_findings", [])) | {finding_id})
    else:
        snoozed = dict(prefs.get("snoozed_findings", {}))
        snoozed[finding_id] = (datetime.now(UTC) + timedelta(days=body.days)).isoformat()
        prefs["snoozed_findings"] = snoozed
    user.preferences = prefs
    db.commit()
    return {"ok": True}


@router.get("/insights/health-score")
def get_health_score(p: PortfolioDep) -> dict:
    return health_score(p)


@router.get("/analytics")
def analytics(p: PortfolioDep) -> dict:
    return insights(p)


@router.post("/simulate")
def run_simulation(body: SimulateIn, p: PortfolioDep) -> dict:
    return simulate(p, body.scenario, body.params)


@router.get("/search")
def search(user: CurrentUser, db: DB, q: str = Query(min_length=1, max_length=200)) -> list[dict]:
    return global_search(db, user.id, q)


@router.get("/graph")
def digital_twin(user: CurrentUser, db: DB) -> dict:
    return graph_view(db, user.id)
