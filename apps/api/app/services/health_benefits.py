"""Health insurance navigation: cost estimates, network checks, bill reconciliation, prior auth."""

from difflib import SequenceMatcher

from app.db.models import EOB, Authorization, Bill, Provider
from app.services.health_score import expected_coinsurance
from app.services.portfolio import Portfolio

PROCEDURES: dict[str, tuple[str, str]] = {
    "mri lumbar": ("72148", "MRI, lumbar spine without contrast"),
    "mri back": ("72148", "MRI, lumbar spine without contrast"),
    "mri spine": ("72148", "MRI, lumbar spine without contrast"),
    "mri knee": ("73721", "MRI, knee joint without contrast"),
    "mri brain": ("70553", "MRI, brain with and without contrast"),
    "mri": ("72148", "MRI (assumed lumbar spine — most common for your open authorization)"),
    "ct": ("74177", "CT abdomen and pelvis with contrast"),
    "arthroscopy": ("29881", "Knee arthroscopy with meniscectomy"),
}

TERMS = {
    "deductible": "The amount you pay each year before your plan starts sharing costs. Copay visits usually don't count toward waiting for it.",
    "copay": "A flat fee for a visit — like $30 for a regular doctor visit — regardless of the total bill.",
    "coinsurance": "Your percentage share of the bill after you've met your deductible. With 20% coinsurance, a $1,000 allowed charge costs you $200.",
    "allowed_amount": "The maximum your plan has agreed to pay for a service. In-network providers can't bill you above it.",
    "out_of_pocket_max": "The most you'll pay in a year for covered in-network care. After that, the plan pays 100%.",
    "eob": "An Explanation of Benefits is a summary from your insurer of what they paid and what you may owe. It is not a bill.",
    "prior_authorization": "Approval your plan must give before certain services (like an MRI) so they're covered.",
}


def _match_provider(p: Portfolio, query: str) -> Provider | None:
    if not query:
        return None
    best = max(p.providers.values(), key=lambda pr: SequenceMatcher(None, query.lower(), pr.name.lower()).ratio(), default=None)
    if best and (SequenceMatcher(None, query.lower(), best.name.lower()).ratio() > 0.35 or query.lower() in best.name.lower()):
        return best
    return None


def identify_procedure(text: str) -> tuple[str, str, str]:
    lower = text.lower()
    for key in sorted(PROCEDURES, key=len, reverse=True):
        if all(w in lower for w in key.split()):
            cpt, name = PROCEDURES[key]
            certainty = "possible" if key in ("mri", "ct") else "confirmed"
            return cpt, name, certainty
    return "", text, "needs_verification"


def procedure_check(p: Portfolio, procedure: str, provider_query: str) -> dict:
    hp = p.health_plan
    if hp is None:
        return {"available": False, "message": "No health plan found. Upload your benefits summary to check coverage."}
    provider = _match_provider(p, provider_query) or _match_provider(p, procedure)
    cpt, proc_name, cpt_certainty = identify_procedure(procedure)
    steps: list[dict] = []
    steps.append({"step": "Identify insurance plan", "status": "done", "detail": f"Bluepeak {hp.plan_type} · {hp.network_name} network",
                  "certainty": "confirmed"})
    if provider is None:
        steps.append({"step": "Find provider", "status": "blocked", "detail": "We couldn't match that provider. Try the full name.",
                      "certainty": "needs_verification"})
        return {"available": True, "steps": steps, "procedure": proc_name, "cpt": cpt, "estimate": None,
                "summary": "I need the provider's name to check network status and cost."}
    steps.append({"step": "Find provider", "status": "done", "detail": f"{provider.name} · {provider.city}", "certainty": "confirmed"})
    in_network = hp.network_name in (provider.networks or [])
    steps.append({"step": "Check network", "status": "done" if in_network else "warning",
                  "detail": "In-network" if in_network else "Not listed in your plan's directory — you may pay more or be balance-billed",
                  "certainty": "confirmed", "source": "Health Plan Benefits · Section 5 — Provider Network · Page 14"})
    steps.append({"step": "Identify procedure code", "status": "done" if cpt else "warning",
                  "detail": f"CPT {cpt} — {proc_name}" if cpt else "Procedure code unknown — ask your doctor's office",
                  "certainty": cpt_certainty})

    remaining_ded = max(0.0, float(hp.deductible_individual) - float(hp.deductible_met))
    remaining_oop = max(0.0, float(hp.oop_max_individual) - float(hp.oop_met))
    rate = hp.coinsurance_in_network if in_network else hp.coinsurance_out_network
    steps.append({"step": "Check deductible", "status": "done", "certainty": "confirmed",
                  "detail": f"${float(hp.deductible_met):,.0f} of ${float(hp.deductible_individual):,.0f} met · ${remaining_ded:,.0f} left"})
    steps.append({"step": "Check coinsurance", "status": "done", "certainty": "confirmed",
                  "detail": f"You pay {rate}% after the deductible", "source": "Summary of Benefits and Coverage · Page 1"})
    rule = next((r for r in hp.prior_auth_rules if cpt and cpt in r.get("cpt", [])), None)
    existing = next((a for a in p.authorizations if a.cpt_code == cpt), None) if cpt else None
    steps.append({"step": "Check authorization", "status": "warning" if rule else "done", "certainty": "confirmed",
                  "detail": ("Prior authorization required" + (f" — your request is {existing.status}" if existing else ""))
                  if rule else "No prior authorization rule found for this code",
                  "source": rule["source"] if rule else None})

    price = (provider.price_estimates or {}).get(cpt)
    estimate = None
    if price:
        ded_part = min(remaining_ded, price)
        coins_part = (price - ded_part) * rate / 100
        you_pay = min(remaining_oop, ded_part + coins_part)
        estimate = {"negotiated_price": price, "deductible_portion": round(ded_part, 2), "coinsurance_portion": round(coins_part, 2),
                    "you_pay": round(you_pay, 2), "plan_pays": round(price - you_pay, 2), "certainty": "possible",
                    "basis": "Typical negotiated rate for this provider (mock price transparency data). Actual cost depends on the final bill."}
    steps.append({"step": "Check payer policy", "status": "done", "certainty": "confirmed",
                  "detail": "Advanced imaging covered at 20% after deductible in-network; 40% out-of-network",
                  "source": "Summary of Benefits and Coverage · Page 1"})
    alternatives = [
        {"name": pr.name, "price": pr.price_estimates.get(cpt), "in_network": hp.network_name in (pr.networks or [])}
        for pr in p.providers.values() if cpt in (pr.price_estimates or {}) and pr.id != provider.id
    ]
    summary = (
        f"{proc_name} at {provider.name} is {'in-network' if in_network else 'NOT listed as in-network'}. "
        + (f"Estimated cost to you: about ${estimate['you_pay']:,.0f}. " if estimate else "We don't have a price estimate. ")
        + ("Prior authorization is required. " if rule else "")
    )
    return {"available": True, "procedure": proc_name, "cpt": cpt, "provider": provider.name, "in_network": in_network,
            "steps": steps, "estimate": estimate, "alternatives": alternatives, "summary": summary.strip(),
            "uncertainty": ["Prices are estimates, not quotes.", "Network status can change — confirm before your visit.",
                            "Individual physicians (e.g. radiologists) may bill separately."]}


def reconcile(p: Portfolio, bill: Bill, eob: EOB) -> dict:
    hp = p.health_plan
    rate = hp.coinsurance_in_network if hp else 20
    rows = [
        {"key": "hospital_charge", "label": "Hospital charge", "amount": float(eob.billed_amount),
         "explain": "The provider's full list price before any insurance discounts."},
        {"key": "allowed", "label": "Negotiated amount", "amount": float(eob.allowed_amount),
         "explain": "What your plan agreed to pay this provider in total. The rest is written off."},
        {"key": "plan_paid", "label": "Insurance payment", "amount": float(eob.plan_paid), "explain": "What Bluepeak paid."},
        {"key": "deductible", "label": "Deductible", "amount": float(eob.deductible), "explain": "Your share before the plan pays."},
        {"key": "coinsurance", "label": "Coinsurance", "amount": float(eob.coinsurance), "explain": f"Your {rate}% share after the deductible."},
        {"key": "copay", "label": "Copay", "amount": float(eob.copay), "explain": "Flat fee, if any."},
        {"key": "patient_responsibility", "label": "Patient responsibility", "amount": float(eob.patient_responsibility),
         "explain": "What you may owe according to the insurer."},
    ]
    issues: list[dict] = []
    parts = float(eob.plan_paid) + float(eob.deductible) + float(eob.coinsurance) + float(eob.copay)
    if abs(parts - float(eob.allowed_amount)) > 1:
        issues.append({"title": "EOB amounts don't add up", "certainty": "confirmed",
                       "detail": f"Plan paid + your share = ${parts:,.2f}, but the allowed amount is ${float(eob.allowed_amount):,.2f}."})
    exp = expected_coinsurance(float(eob.allowed_amount), float(eob.deductible), float(eob.copay), rate)
    if abs(float(eob.coinsurance) - exp) >= 25:
        issues.append({"title": "Coinsurance higher than expected", "certainty": "possible", "amount": round(float(eob.coinsurance) - exp, 2),
                       "detail": f"At {rate}% of ${float(eob.allowed_amount) - float(eob.deductible):,.0f}, expected coinsurance is "
                                 f"about ${exp:,.0f}, but the EOB shows ${float(eob.coinsurance):,.0f}. Part of the claim may have "
                                 "been processed at the out-of-network rate."})
    if abs(float(bill.amount_due) - float(eob.patient_responsibility)) > 1:
        issues.append({"title": "Bill doesn't match EOB", "certainty": "confirmed",
                       "amount": round(float(bill.amount_due) - float(eob.patient_responsibility), 2),
                       "detail": f"The hospital is asking for ${float(bill.amount_due):,.2f}; your EOB says you owe "
                                 f"${float(eob.patient_responsibility):,.2f}."})
    for item in bill.line_items:
        if item.get("network_note"):
            issues.append({"title": f"{item['provider']} may be out-of-network", "certainty": "possible",
                           "detail": f"{item['network_note']}. Because your facility was in-network, federal surprise-billing "
                                     "protections may limit what you owe — ask Bluepeak to review."})
    return {
        "rows": rows,
        "issues": issues,
        "status": "discrepancy_possible" if issues else "matches",
        "summary": ("Your bill matches the EOB, but there may be an issue worth asking about." if issues and all(
            i["title"] != "Bill doesn't match EOB" for i in issues) else
                    "We found differences between your bill and your insurer's EOB." if issues else
                    "Your bill matches your insurer's EOB."),
        "suggested_questions": [
            "Was any part of this claim processed as out-of-network? If so, which line?",
            f"Can you confirm the coinsurance calculation ({rate}% of the amount after deductible)?",
            "Does the No Surprises Act apply to the anesthesia charges?",
        ] if issues else [],
    }


def prior_auth_assistant(p: Portfolio, auth: Authorization) -> dict:
    hp = p.health_plan
    rule = next((r for r in (hp.prior_auth_rules if hp else []) if auth.cpt_code in r.get("cpt", [])), None)
    missing = [r["item"] for r in auth.requirements if r.get("status") != "complete"]
    risk = "elevated" if missing else "low"
    provider = p.providers.get(auth.provider_id) if auth.provider_id else None
    return {
        "procedure": auth.procedure_name,
        "cpt": auth.cpt_code,
        "status": auth.status,
        "decision_due": auth.decision_due.isoformat() if auth.decision_due else None,
        "provider": provider.name if provider else None,
        "steps": [
            {"step": "Procedure requested", "status": "done"},
            {"step": "Identify payer rules", "status": "done", "detail": rule["source"] if rule else "No rule found"},
            {"step": "Check clinical documentation", "status": "warning" if missing else "done",
             "detail": f"{len(auth.requirements) - len(missing)} of {len(auth.requirements)} items on file"},
            {"step": "Find missing requirements", "status": "warning" if missing else "done", "detail": ", ".join(missing) or "None"},
            {"step": "Administrative denial risk", "status": "warning" if missing else "done",
             "detail": "Elevated — missing documentation is a common administrative denial reason" if missing else "Low"},
            {"step": "Prepare authorization packet", "status": "ready"},
        ],
        "requirements": auth.requirements,
        "missing": missing,
        "administrative_risk": risk,
        "packet": ["Physician order", "Clinical notes", "Conservative therapy records (PT notes, medications tried)",
                   "Member ID and plan information"],
        "disclaimer": "InsurePilot checks paperwork completeness only. Medical necessity is decided by licensed clinicians "
                      "and your health plan.",
    }
