"""User-facing insights — only the few that matter."""

from datetime import date

from app.services.health_score import detect_risks
from app.services.portfolio import Portfolio


def insights(p: Portfolio) -> dict:
    active = p.active_policies
    total = sum(float(x.premium_annual) for x in active)
    prior = sum(float(x.prior_premium_annual or x.premium_annual) for x in active)
    by_cat = sorted(({"category": x.category, "premium": float(x.premium_annual)} for x in active), key=lambda r: -r["premium"])
    renewals = sorted(
        ({"policy_id": x.id, "category": x.category, "carrier": x.carrier.short_name, "date": x.expiration_date.isoformat(),
          "days": (x.expiration_date - date.today()).days} for x in active if (x.expiration_date - date.today()).days <= 120),
        key=lambda r: r["days"],
    )
    deductibles = [{"category": x.category, "deductible": float(x.deductible)} for x in active if x.deductible]
    year = date.today().year
    # Premium history: prior term vs current term (only data we actually have).
    history = [{"year": year - 1, "total": round(prior)}, {"year": year, "total": round(total)}]
    claims = [{"claim_number": c.claim_number, "category": c.category, "status": c.status, "date": c.incident_date.isoformat(),
               "amount": float(c.amount_claimed or 0)} for c in p.claims]
    return {
        "annual_premium": round(total),
        "monthly_equivalent": round(total / 12),
        "premium_change_percent": round((total - prior) / prior * 100, 1) if prior else 0,
        "by_category": by_cat,
        "renewals": renewals,
        "deductible_exposure": {"items": deductibles, "worst_case_total": sum(d["deductible"] for d in deductibles)},
        "claims_history": claims,
        "premium_history": history,
        "duplicate_coverage": [f.title for f in detect_risks(p) if f.kind == "duplicate_coverage"],
    }
