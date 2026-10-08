"""Claim Guardian services: decision support, denial analysis, packets, drafts, photo observations."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import Claim, ClaimEvent, Policy
from app.services.portfolio import Portfolio


def claim_decision(p: Portfolio, category: str, repair_estimate: float) -> dict:
    """Transparent file-vs-pay comparison. Never makes the decision for the user."""
    policy = p.policy(category)
    if policy is None:
        return {"available": False, "message": f"No active {category} policy was found."}
    coverage_code = "COLL" if category == "auto" else None
    cov = next((c for c in policy.coverages if c.code == coverage_code), None)
    deductible = float(cov.deductible) if cov and cov.deductible else float(policy.deductible or 0)
    payout = max(0.0, repair_estimate - deductible)
    recent_claims = [c for c in p.claims if c.category == category and (date.today() - c.incident_date).days <= 365 * 3]
    surcharge_factor = next((f for f in (policy.renewal_changes or {}).get("factors", []) if "claim" in f["label"].lower()), None)

    considerations = [
        {"label": "Insurer would pay about", "value": f"${payout:,.0f}", "certainty": "confirmed",
         "note": "Estimate minus your deductible. The adjuster's final figure may differ."},
        {"label": "Claims on this policy in the last 3 years", "value": str(len(recent_claims)), "certainty": "confirmed"},
    ]
    if surcharge_factor:
        considerations.append({"label": "Past premium impact", "value": f"+${surcharge_factor.get('impact') or 0:,.0f}/yr",
                               "certainty": "confirmed", "note": f"From a prior at-fault claim ({surcharge_factor['source']})."})
    considerations.append({"label": "Future premium impact", "value": "Possible", "certainty": "possible",
                           "note": "Your policy says an at-fault collision claim may affect your premium at renewal. "
                                   "The exact amount isn't known in advance."})
    return {
        "available": True,
        "repair_estimate": repair_estimate,
        "deductible": deductible,
        "estimated_insurer_payment": payout,
        "prior_claims": len(recent_claims),
        "options": [
            {"title": "File a claim", "pros": [f"Insurer may pay about ${payout:,.0f}", "Adjuster documents the damage",
                                               "Rental reimbursement may apply"],
             "cons": ["May affect future premium if you were at fault", "Takes time to process"]},
            {"title": "Pay out of pocket", "pros": ["No claim on your record", "Faster repair"],
             "cons": [f"You pay the full ${repair_estimate:,.0f}"]},
        ],
        "considerations": considerations,
        "source": f"{category.title()} Policy · Section 4 — Collision Coverage · Page 18" if category == "auto" else None,
        "note": "This is information to help you decide — not a recommendation. If someone else caused the damage, "
                "their insurer may be responsible instead.",
    }


def denial_analysis(p: Portfolio, claim: Claim) -> dict:
    policy = p.policy_by_id(claim.policy_id)
    reason = claim.denial_reason or ""
    exclusions = [e for e in (policy.exclusions if policy else []) if any(
        w in e.name.lower() for w in ("water", "flood")) and "water" in reason.lower()]
    endorsements = [e for e in (policy.endorsements if policy else []) if "water" in reason.lower() and "water" in e.name.lower()]
    findings = []
    for e in exclusions:
        findings.append({"kind": "exclusion", "title": e.name, "detail": e.plain_language,
                         "source": f"{e.source_section} · Page {e.source_page}", "certainty": "confirmed"})
    for e in endorsements:
        findings.append({"kind": "endorsement", "title": f"{e.name} ({e.code})",
                         "detail": f"{e.plain_language} Limit ${float(e.limit_amount or 0):,.0f}.",
                         "source": f"{e.source_section} · Page {e.source_page}", "certainty": "confirmed"})
    explanation = (
        f"The denial cites: “{reason}” "
        + (f"Your policy also contains the {endorsements[0].name} endorsement, which adds back up to "
           f"${float(endorsements[0].limit_amount or 0):,.0f} for water that backs up through drains or a sump. "
           "Whether it applies depends on the actual cause of loss — for example, a drain backup versus surface flooding."
           if endorsements else "We didn't find an endorsement that modifies this exclusion.")
    )
    return {
        "claim_number": claim.claim_number,
        "denial_reason": reason,
        "explanation": explanation,
        "findings": findings,
        "open_questions": [
            "Did the water enter through the floor drain (backup) or from surface water outside?",
            "Was the water-backup endorsement considered when the claim was reviewed?",
            "Can a plumber's report on the cause of loss be added to the file?",
        ],
        "deadline": claim.deadlines[0] if claim.deadlines else None,
        "certainty": "possible" if endorsements else "confirmed",
        "next_steps": ["generate_adjuster_questions", "prepare_evidence_package", "prepare_appeal_draft", "escalate_to_human"],
    }


def claim_packet(p: Portfolio, claim: Claim) -> dict:
    docs = [d for d in p.documents if d.claim_id == claim.id]
    policy = p.policy_by_id(claim.policy_id)
    return {
        "claim_number": claim.claim_number,
        "policy": f"{policy.carrier.name} {policy.product_name}" if policy else None,
        "incident_date": claim.incident_date.isoformat(),
        "summary": claim.description,
        "documents_included": [d.title for d in docs],
        "documents_missing": claim.missing_documents,
        "timeline": [{"title": e.title, "date": e.occurred_at.date().isoformat(), "status": e.status} for e in claim.events],
        "ready_to_submit": not claim.missing_documents,
    }


def create_claim_draft(db: Session, user_id: str, policy: Policy, title: str, description: str,
                       incident_date: date, amount: float | None) -> Claim:
    number = f"D-{datetime.now(UTC):%y%m%d%H%M}"
    claim = Claim(
        user_id=user_id, policy_id=policy.id, claim_number=number, category=policy.category, title=title,
        description=description, status="draft", stage="Draft prepared", incident_date=incident_date,
        amount_claimed=amount, missing_documents=["Photos of damage"] if policy.category in ("auto", "home") else [],
        deadlines=[{"label": "Report to insurer promptly", "due": (date.today() + timedelta(days=7)).isoformat(),
                    "source": "Policy conditions — prompt notice"}],
        details={"created_via": "InsurePilot AI"},
    )
    db.add(claim)
    db.flush()
    db.add(ClaimEvent(claim_id=claim.id, kind="incident", title="Incident occurred", occurred_at=datetime.combine(
        incident_date, datetime.min.time(), tzinfo=UTC)))
    db.add(ClaimEvent(claim_id=claim.id, kind="draft", title="Draft prepared with AI", status="current"))
    db.add(ClaimEvent(claim_id=claim.id, kind="submitted", title="Submit to insurer (needs your approval)", status="upcoming",
                      occurred_at=datetime.now(UTC) + timedelta(days=1)))
    return claim


DAMAGE_AREAS = {
    "bumper": "Bumper", "door": "Door panel", "hood": "Hood", "windshield": "Windshield / glass", "glass": "Windshield / glass",
    "light": "Lighting", "lamp": "Lighting", "fender": "Fender", "liftgate": "Liftgate / trunk", "trunk": "Liftgate / trunk",
    "roof": "Roof", "ceiling": "Ceiling", "drywall": "Drywall", "floor": "Flooring", "basement": "Basement", "wall": "Walls",
}


def photo_observations(filename: str, description: str, size_bytes: int, content_type: str) -> dict:
    """AI-assisted observations from photo context. Labeled as observations, never as a repair estimate."""
    text = f"{filename} {description}".lower()
    areas = sorted({label for key, label in DAMAGE_AREAS.items() if key in text})
    damage_type = (
        "water" if any(w in text for w in ("water", "leak", "flood", "wet")) else
        "collision" if any(w in text for w in ("hit", "collision", "dent", "bumper", "crash")) else
        "hail" if "hail" in text else "fire" if "fire" in text or "smoke" in text else "unclassified"
    )
    return {
        "label": "AI-assisted observations — not a repair estimate",
        "damage_type": damage_type,
        "visible_areas": areas or ["Not determined — add a short description"],
        "evidence_category": "damage_photo" if damage_type != "unclassified" else "supporting_photo",
        "metadata": {"filename": filename, "size_kb": round(size_bytes / 1024), "content_type": content_type},
        "confidence": "moderate" if areas else "needs_verification",
        "notes": "Only a licensed adjuster or repair shop can determine repair costs.",
    }
