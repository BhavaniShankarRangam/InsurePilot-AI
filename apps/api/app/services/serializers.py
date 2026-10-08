"""Converts ORM objects into API payloads. Sensitive identifiers are masked."""

from datetime import date

from app.core.masking import mask_identifier
from app.db.models import Claim, Document, Notification, Policy
from app.services.health_score import policy_alerts
from app.services.portfolio import Portfolio


def f(v) -> float | None:
    return None if v is None else float(v)


def policy_card(p: Portfolio, pol: Policy) -> dict:
    days = (pol.expiration_date - date.today()).days
    alerts = policy_alerts(p, pol)
    health = "inactive" if pol.status == "lapsed" else (
        "attention" if any(a["severity"] == "attention" for a in alerts) else "review" if alerts else "healthy")
    extra: dict = {}
    if pol.category == "health" and p.health_plan:
        hp = p.health_plan
        extra = {"deductible_remaining": f(hp.deductible_individual) - f(hp.deductible_met),
                 "oop_remaining": f(hp.oop_max_individual) - f(hp.oop_met),
                 "deductible_progress": round(f(hp.deductible_met) / f(hp.deductible_individual), 3),
                 "oop_progress": round(f(hp.oop_met) / f(hp.oop_max_individual), 3)}
    if pol.category == "life":
        extra = {"coverage_amount": next((f(c.limit_amount) for c in pol.coverages if c.code == "DB"), None),
                 "beneficiary_status": "Primary only — no backup" if not any(
                     b.designation == "contingent" for b in pol.beneficiaries) else "Complete"}
    open_claims = [c for c in p.claims if c.policy_id == pol.id and c.status not in ("closed", "paid")]
    return {
        "id": pol.id,
        "category": pol.category,
        "product_name": pol.product_name,
        "carrier": {"name": pol.carrier.name, "short_name": pol.carrier.short_name, "color": pol.carrier.brand_color,
                    "phone": pol.carrier.phone, "rating": pol.carrier.rating},
        "policy_number": mask_identifier(pol.policy_number),
        "status": pol.status,
        "premium_annual": f(pol.premium_annual),
        "premium_monthly": round(f(pol.premium_annual) / 12, 2),
        "prior_premium_annual": f(pol.prior_premium_annual),
        "deductible": f(pol.deductible),
        "effective_date": pol.effective_date.isoformat(),
        "expiration_date": pol.expiration_date.isoformat(),
        "days_until_renewal": days,
        "summary": pol.summary,
        "coverage_health": health,
        "alerts": alerts,
        "claim_status": open_claims[0].status if open_claims else None,
        "open_claims": len(open_claims),
        **extra,
    }


def policy_detail(p: Portfolio, pol: Policy) -> dict:
    return {
        **policy_card(p, pol),
        "details": pol.details,
        "coverages": [{"id": c.id, "code": c.code, "name": c.name, "plain_language": c.plain_language, "limit": c.limit_text,
                       "limit_amount": f(c.limit_amount), "deductible": f(c.deductible), "status": c.status,
                       "source": {"section": c.source_section, "page": c.source_page}} for c in pol.coverages],
        "exclusions": [{"id": e.id, "name": e.name, "plain_language": e.plain_language,
                        "source": {"section": e.source_section, "page": e.source_page}} for e in pol.exclusions],
        "endorsements": [{"id": e.id, "code": e.code, "name": e.name, "plain_language": e.plain_language,
                          "limit_amount": f(e.limit_amount), "premium_annual": f(e.premium_annual),
                          "source": {"section": e.source_section, "page": e.source_page}} for e in pol.endorsements],
        "beneficiaries": [{"name": b.full_name, "relationship": b.relationship_type, "designation": b.designation,
                           "share": b.share_percent} for b in pol.beneficiaries],
        "documents": [document_out(d) for d in p.documents if d.policy_id == pol.id],
        "claims": [claim_card(c) for c in p.claims if c.policy_id == pol.id],
        "renewal_changes": pol.renewal_changes,
    }


def claim_card(c: Claim) -> dict:
    current = next((e for e in c.events if e.status == "current"), None)
    done = sum(1 for e in c.events if e.status == "done")
    return {
        "id": c.id, "claim_number": c.claim_number, "category": c.category, "title": c.title, "status": c.status,
        "stage": current.title if current else c.stage, "incident_date": c.incident_date.isoformat(),
        "amount_claimed": f(c.amount_claimed), "amount_paid": f(c.amount_paid), "missing_documents": c.missing_documents,
        "progress": round(done / max(1, len(c.events)), 2), "policy_id": c.policy_id,
    }


def claim_detail(c: Claim, docs: list[Document]) -> dict:
    return {
        **claim_card(c), "description": c.description, "deductible_applied": f(c.deductible_applied),
        "adjuster": {"name": c.adjuster_name, "email": c.adjuster_email} if c.adjuster_name else None,
        "denial_reason": c.denial_reason, "deadlines": c.deadlines, "details": c.details,
        "events": [{"id": e.id, "kind": e.kind, "title": e.title, "description": e.description, "status": e.status,
                    "occurred_at": e.occurred_at.isoformat()} for e in c.events],
        "documents": [document_out(d) for d in docs],
    }


def document_out(d: Document) -> dict:
    return {"id": d.id, "title": d.title, "filename": d.filename, "mime_type": d.mime_type, "size_bytes": d.size_bytes,
            "doc_type": d.doc_type, "status": d.status, "page_count": d.page_count, "summary": d.summary,
            "extracted": d.extracted, "classification_confidence": d.classification_confidence, "policy_id": d.policy_id,
            "claim_id": d.claim_id, "created_at": d.created_at.isoformat() if d.created_at else None}


def notification_out(n: Notification) -> dict:
    return {"id": n.id, "title": n.title, "body": n.body, "category": n.category, "priority": n.priority, "link": n.link,
            "read": n.read, "created_at": n.created_at.isoformat() if n.created_at else None}
