"""Policy intelligence: explainer, premium change, renewal autopilot, comparison, coverage map, simulation."""

from datetime import date

from app.db.models import Policy
from app.services.portfolio import Portfolio


def money(v: float | None) -> str:
    return "—" if v is None else f"${float(v):,.0f}"


def explain_policy(pol: Policy) -> dict:
    return {
        "policy_id": pol.id,
        "title": f"{pol.carrier.name} · {pol.product_name}",
        "summary": pol.summary,
        "covered": [{"name": c.name, "detail": c.plain_language, "limit": c.limit_text or money(c.limit_amount),
                     "source": f"{c.source_section} · Page {c.source_page}" if c.source_section else None}
                    for c in pol.coverages if c.status in ("covered", "partial", "review")],
        "not_covered": [{"name": e.name, "detail": e.plain_language,
                         "source": f"{e.source_section} · Page {e.source_page}" if e.source_section else None}
                        for e in pol.exclusions]
                       + [{"name": c.name, "detail": c.plain_language, "source": f"{c.source_section} · Page {c.source_page}"}
                          for c in pol.coverages if c.status == "not_covered"],
        "deductible": money(pol.deductible),
        "limits": [{"name": c.name, "limit": c.limit_text or money(c.limit_amount)} for c in pol.coverages if c.limit_amount or c.limit_text],
        "endorsements": [{"name": e.name, "detail": e.plain_language, "limit": money(e.limit_amount),
                          "source": f"{e.source_section} · Page {e.source_page}"} for e in pol.endorsements],
        "potential_gaps": [{"name": c.name, "detail": c.plain_language} for c in pol.coverages if c.status == "review"],
        "renewal_date": pol.expiration_date.isoformat(),
        "premium": float(pol.premium_annual),
    }


def coverage_map(p: Portfolio) -> list[dict]:
    """Flattened covered/partial/not-covered/review items across the portfolio for the Coverage Map."""
    items: list[dict] = []
    for pol in p.active_policies:
        for c in pol.coverages:
            items.append({"category": pol.category, "policy_id": pol.id, "name": c.name, "status": c.status,
                          "detail": c.plain_language, "limit": c.limit_text or money(c.limit_amount)})
        for e in pol.exclusions:
            items.append({"category": pol.category, "policy_id": pol.id, "name": e.name, "status": "not_covered",
                          "detail": e.plain_language, "limit": None})
        for e in pol.endorsements:
            items.append({"category": pol.category, "policy_id": pol.id, "name": e.name, "status": "partial",
                          "detail": e.plain_language, "limit": money(e.limit_amount)})
    return items


def premium_change(pol: Policy) -> dict:
    prior = float(pol.prior_premium_annual or pol.premium_annual)
    current = float(pol.premium_annual)
    pct = round((current - prior) / prior * 100) if prior else 0
    rc = pol.renewal_changes or {}
    factors = rc.get("factors", [])
    explained = sum(f["impact"] for f in factors if f.get("impact"))
    return {
        "policy_id": pol.id,
        "prior_premium": prior,
        "current_premium": current,
        "change": current - prior,
        "change_percent": pct,
        "confirmed": [f for f in factors if f["status"] == "confirmed"],
        "possible": [f for f in factors if f["status"] != "confirmed"],
        "unexplained_amount": round(current - prior - explained, 2),
        "coverage_changes": rc.get("coverage_changes", []),
        "discount_opportunities": rc.get("discount_opportunities", []),
        "note": "Confirmed reasons come from your carrier's renewal notice. Possible reasons are general rating practices "
                "the carrier didn't state for your policy.",
    }


def renewal_autopilot(p: Portfolio, pol: Policy) -> dict:
    pc = premium_change(pol)
    quotes = [q for q in p.quotes if q.category == pol.category]
    days = (pol.expiration_date - date.today()).days
    return {
        "policy_id": pol.id,
        "days_until_renewal": days,
        "renewal_date": pol.expiration_date.isoformat(),
        "steps": [
            {"step": "Renewal detected", "status": "done", "detail": f"Renews in {days} days"},
            {"step": "Analyze premium change", "status": "done",
             "detail": f"{money(pc['prior_premium'])} → {money(pc['current_premium'])} ({pc['change_percent']:+d}%)"},
            {"step": "Compare previous policy", "status": "done",
             "detail": "No coverage changes found" if not pc["coverage_changes"] else f"{len(pc['coverage_changes'])} changes"},
            {"step": "Identify changed coverages", "status": "done", "detail": "Limits and deductibles unchanged"},
            {"step": "Identify discounts", "status": "done", "detail": ", ".join(pc["discount_opportunities"]) or "None found"},
            {"step": "Compare alternatives", "status": "done" if quotes else "skipped", "detail": f"{len(quotes)} comparable quotes"},
            {"step": "Your decision", "status": "waiting", "detail": "Nothing changes without your approval"},
        ],
        "premium_change": pc,
        "alternatives": len(quotes),
    }


COMPARE_ROWS = [
    ("premium", "Annual premium"), ("liability", "Liability"), ("collision_deductible", "Collision deductible"),
    ("comprehensive_deductible", "Comprehensive deductible"), ("rental", "Rental car"), ("roadside", "Roadside"),
    ("medical_payments", "Medical payments"), ("exclusions", "Notable exclusions"), ("add_ons", "Add-ons"),
]


def _current_profile(pol: Policy) -> dict:
    cov = {c.code: c for c in pol.coverages}
    return {
        "premium": float(pol.premium_annual),
        "liability": "$100k/$300k/$100k" if "BI" in cov else "—",
        "collision_deductible": float(cov["COLL"].deductible) if "COLL" in cov else None,
        "comprehensive_deductible": float(cov["COMP"].deductible) if "COMP" in cov else None,
        "rental": cov["RENT"].limit_text if "RENT" in cov else "Not included",
        "roadside": "Included" if "ROAD" in cov else "Not included",
        "medical_payments": float(cov["MED"].limit_amount) if "MED" in cov else None,
        "exclusions": [e.name for e in pol.exclusions][:3],
        "add_ons": [],
    }


def compare(p: Portfolio, category: str) -> dict:
    pol = p.policy(category)
    if pol is None:
        return {"available": False, "message": f"No {category} policy to compare."}
    columns = [{"id": pol.id, "name": f"{pol.carrier.short_name} (current)", "current": True, **_current_profile(pol)}]
    for q in p.quotes:
        if q.category == category:
            columns.append({"id": q.id, "name": q.carrier_name, "current": False, "premium": float(q.premium_annual),
                            **q.coverages, "exclusions": q.exclusions, "add_ons": q.add_ons})
    base = columns[0]
    tradeoffs: list[dict] = []
    for col in columns[1:]:
        notes = []
        diff = col["premium"] - base["premium"]
        notes.append(f"{'Saves' if diff < 0 else 'Costs'} {money(abs(diff))}/yr vs. your current policy")
        if col.get("rental") != base["rental"]:
            notes.append(f"Rental: {col.get('rental')} (you have {base['rental']})")
        if col.get("roadside") != base["roadside"]:
            notes.append(f"Roadside: {col.get('roadside')}")
        if col.get("comprehensive_deductible") != base["comprehensive_deductible"]:
            notes.append(f"Comprehensive deductible {money(col.get('comprehensive_deductible'))} (yours: {money(base['comprehensive_deductible'])})")
        if col.get("collision_deductible") != base["collision_deductible"]:
            notes.append(f"Collision deductible {money(col.get('collision_deductible'))} (yours: {money(base['collision_deductible'])})")
        if col.get("liability") != base["liability"]:
            notes.append(f"Higher liability limits: {col.get('liability')}")
        if col.get("medical_payments") != base["medical_payments"]:
            notes.append(f"Medical payments {money(col.get('medical_payments'))} (yours: {money(base['medical_payments'])})")
        tradeoffs.append({"name": col["name"], "notes": notes})
    return {
        "available": True,
        "category": category,
        "rows": [{"key": k, "label": label} for k, label in COMPARE_ROWS],
        "columns": columns,
        "tradeoffs": tradeoffs,
        "note": "Differences are shown objectively. InsurePilot doesn't rank carriers as “best” — the right choice depends on what matters to you.",
    }


def coverage_profile(pol: Policy) -> dict:
    return {"category": pol.category, **{k: v for k, v in _current_profile(pol).items() if k != "premium"},
            "vehicle": (pol.details or {}).get("vehicle")}


def simulate(p: Portfolio, scenario: str, params: dict) -> dict:
    """Clearly-labeled simulations using simple, disclosed assumptions — not carrier quotes."""
    base = {"label": "Simulated outcome", "disclaimer": "Simulation based on general rating patterns and your data — not a quote. "
                                                        "Actual carrier pricing will differ."}
    if scenario == "deductible":
        pol = p.policy(params.get("category", "auto"))
        if not pol:
            return {**base, "available": False}
        old = float(params.get("from", pol.deductible or 500))
        new = float(params.get("to", 1000))
        factor = {250: 1.08, 500: 1.0, 1000: 0.9, 2000: 0.82, 2500: 0.8}
        f_old = factor.get(int(old), 1.0)
        f_new = factor.get(int(new), 0.9)
        collision_share = 0.42  # assumed share of premium from physical-damage coverage
        current = float(pol.premium_annual)
        new_premium = current * (1 - collision_share) + current * collision_share * (f_new / f_old)
        saving = current - new_premium
        return {**base, "available": True, "scenario": "deductible", "title": f"Raise deductible {money(old)} → {money(new)}",
                "metrics": [
                    {"label": "Estimated premium", "before": current, "after": round(new_premium), "certainty": "possible"},
                    {"label": "Out-of-pocket per claim", "before": old, "after": new, "certainty": "confirmed"},
                ],
                "insights": [f"You'd save about {money(saving)}/yr but pay {money(new - old)} more if you file a claim.",
                             f"Break-even: about one claim every {max(1, round((new - old) / max(saving, 1)))} years."],
                "assumptions": ["~42% of premium is collision/comprehensive", "Typical deductible rating factors"]}
    if scenario == "teen_driver":
        pol = p.policy("auto")
        if not pol:
            return {**base, "available": False}
        current = float(pol.premium_annual)
        low, high = current * 1.5, current * 2.1
        return {**base, "available": True, "scenario": "teen_driver", "title": "Add a teen driver (Riley, 16)",
                "metrics": [{"label": "Estimated premium", "before": current, "after": round((low + high) / 2),
                             "range": [round(low), round(high)], "certainty": "possible"}],
                "insights": ["Adding a newly licensed teen typically raises premiums 50–110%.",
                             "Good-student and driver-training discounts can reduce the increase.",
                             "Your liability limits ($100k/$300k) become more important with an inexperienced driver."],
                "assumptions": ["Industry-typical teen surcharge range", "No change to vehicles or coverages"]}
    if scenario == "switch_health_plan":
        hp = p.health_plan
        if not hp:
            return {**base, "available": False}
        alt = {"name": "Bluepeak HDHP 4000 + HSA", "premium": 4260, "deductible": 4000, "oop": 7500, "coinsurance": 20}
        current = {"name": "Choice PPO 2500", "premium": 5880, "deductible": 2500, "oop": 6500, "coinsurance": 20}
        usage = float(params.get("expected_medical_spend", 6000))

        def annual_cost(plan: dict) -> float:
            ded = min(usage, plan["deductible"])
            coins = max(0.0, usage - plan["deductible"]) * plan["coinsurance"] / 100
            return plan["premium"] + min(plan["oop"], ded + coins)

        return {**base, "available": True, "scenario": "switch_health_plan", "title": f"Switch to {alt['name']}",
                "metrics": [{"label": f"Total yearly cost at ${usage:,.0f} of care", "before": round(annual_cost(current)),
                             "after": round(annual_cost(alt)), "certainty": "possible"},
                            {"label": "Deductible", "before": current["deductible"], "after": alt["deductible"], "certainty": "confirmed"}],
                "insights": ["Lower premiums but a higher deductible — better if you expect few medical costs.",
                             "An HSA lets you save pre-tax money for medical expenses.",
                             "Your pending MRI would be paid more out of pocket under the HDHP."],
                "assumptions": [f"${usage:,.0f} of allowed medical spending", "Illustrative alternative plan (mock)"]}
    return {**base, "available": False, "message": "Unknown scenario"}
