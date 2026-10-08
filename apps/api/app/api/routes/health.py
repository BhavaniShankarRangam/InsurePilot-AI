"""Health insurance AI: plan summary, procedure checker, reconciliation, prior authorization, providers."""

from fastapi import APIRouter, HTTPException

from app.api.deps import DB, PortfolioDep
from app.integrations.adapters import MockFHIRPayerAdapter, MockProviderDirectory
from app.schemas.api import ProcedureIn
from app.services import health_benefits as hb

router = APIRouter(tags=["health"])


def _plan(p):
    if p.health_plan is None:
        raise HTTPException(404, "No health plan on file")
    return p.health_plan


@router.get("/health/summary")
def summary(p: PortfolioDep) -> dict:
    hp = _plan(p)
    pol = p.policy_by_id(hp.policy_id)
    return {
        "plan": {"name": f"{pol.carrier.name} {pol.product_name}", "type": hp.plan_type, "network": hp.network_name,
                 "plan_year_end": hp.plan_year_end.isoformat(), "copays": hp.copays, "benefits": hp.benefits,
                 "coinsurance_in": hp.coinsurance_in_network, "coinsurance_out": hp.coinsurance_out_network},
        "accumulators": {"deductible": float(hp.deductible_individual), "deductible_met": float(hp.deductible_met),
                         "oop_max": float(hp.oop_max_individual), "oop_met": float(hp.oop_met)},
        "authorizations": [hb.prior_auth_assistant(p, a) | {"id": a.id} for a in p.authorizations],
        "bills": [{"id": b.id, "service": b.service_description, "date": b.service_date.isoformat(),
                   "total": float(b.total_charge), "amount_due": float(b.amount_due),
                   "due_date": b.due_date.isoformat() if b.due_date else None, "line_items": b.line_items} for b in p.bills],
        "eobs": [{"id": e.id, "date": e.service_date.isoformat(), "billed": float(e.billed_amount),
                  "allowed": float(e.allowed_amount), "plan_paid": float(e.plan_paid),
                  "you_owe": float(e.patient_responsibility)} for e in p.eobs],
        "fhir_coverage": MockFHIRPayerAdapter().coverage(hp),
        "terms": hb.TERMS,
    }


@router.post("/health/procedure-check")
def procedure_check(body: ProcedureIn, p: PortfolioDep) -> dict:
    _plan(p)
    return hb.procedure_check(p, body.procedure, body.provider)


@router.get("/health/reconciliation")
def reconciliation(p: PortfolioDep) -> dict:
    if not p.bills or not p.eobs:
        return {"available": False}
    return {"available": True, **hb.reconcile(p, p.bills[0], p.eobs[0])}


@router.get("/health/authorizations/{auth_id}")
def authorization(auth_id: str, p: PortfolioDep) -> dict:
    a = next((x for x in p.authorizations if x.id == auth_id), None)
    if a is None:
        raise HTTPException(404, "Authorization not found")
    return hb.prior_auth_assistant(p, a)


@router.get("/providers")
def providers(p: PortfolioDep, db: DB, q: str = "", in_network_only: bool = False) -> list[dict]:
    network = p.health_plan.network_name if p.health_plan else None
    out = []
    for pr in MockProviderDirectory(db).search(q or "provider"):
        in_net = bool(network and network in (pr.networks or []))
        if in_network_only and not in_net:
            continue
        out.append({"id": pr.id, "name": pr.name, "kind": pr.kind, "specialty": pr.specialty, "city": pr.city,
                    "in_network": in_net, "rating": float(pr.rating or 0), "accepting": pr.accepting_patients})
    return sorted(out, key=lambda r: (not r["in_network"], -r["rating"]))
