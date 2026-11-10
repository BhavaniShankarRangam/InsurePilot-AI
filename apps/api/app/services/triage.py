"""Claim triage: routes a first-notice-of-loss to one of five paths.

Deterministic rules on purpose: every decision is explainable, reproducible and costs nothing to run, so the
public demo can't run up an LLM bill. Order matters — coverage first, then fraud signals, then data quality,
then the auto-approve limit.

Paths
  not_covered      a policy exclusion or the policy period rules the loss out
  fraud_review     two or more fraud signals → special investigations (never an automatic denial)
  low_confidence   the intake is too thin to decide → a person gathers more information
  adjuster_review  covered and clean, but above the straight-through limit
  auto_approve     covered, clean, complete and under the limit → paid without a person touching it
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Terms of the synthetic Northstar Personal Auto policy used throughout the demo (see app/demo/seed.py).
POLICY_NAME = "Northstar Personal Auto"
DEDUCTIBLES = {"collision": 1000.0, "glass": 500.0, "theft": 500.0, "vandalism": 500.0, "weather": 500.0, "other": 1000.0}
COVERAGE_FOR = {"collision": "Collision", "glass": "Comprehensive", "theft": "Comprehensive",
                "vandalism": "Comprehensive", "weather": "Comprehensive", "other": "To be determined"}
AUTO_APPROVE_LIMIT = 5000.0
LOW_CONFIDENCE_BELOW = 0.6
EXCLUDED_USE = {
    "rideshare": ("Rideshare use", "Driving for Uber/Lyft isn't covered unless a rideshare endorsement is added."),
    "delivery": ("Rideshare use", "Paid delivery driving is treated like rideshare use and needs an endorsement."),
    "racing": ("Racing & speed contests", "Losses during racing or speed contests are excluded."),
}
WEAR_WORDS = ("wear and tear", "worn out", "rust", "engine failure", "transmission failed", "mechanical breakdown")
VAGUE_WORDS = ("not sure", "don't know", "dont know", "no idea", "somehow", "unknown", "can't remember", "cant remember")
SOURCE_EXCLUSIONS = f"{POLICY_NAME} · Exclusions · Page 27"

PATH_META = {
    "auto_approve": {"label": "Auto-approved", "tone": "ok",
                     "next_step": "Payment issued automatically. No adjuster needed."},
    "adjuster_review": {"label": "Adjuster review", "tone": "info",
                        "next_step": "Covered and clean, but above the straight-through limit. Assigned to an adjuster."},
    "fraud_review": {"label": "Fraud flag", "tone": "danger",
                     "next_step": "Referred to the Special Investigations Unit. Not denied: a person reviews the signals."},
    "not_covered": {"label": "Not covered", "tone": "warn",
                    "next_step": "Coverage letter drafted with the policy wording, for a person to check before sending."},
    "low_confidence": {"label": "Low confidence", "tone": "neutral",
                       "next_step": "Routed to a person to collect the missing details before any decision."},
}


@dataclass
class Intake:
    incident_type: str
    description: str
    incident_date: date
    reported_date: date
    policy_start_date: date
    policy_end_date: date
    amount_claimed: float | None
    vehicle_value: float
    photos: int = 0
    police_report: bool = False
    prior_claims_12mo: int = 0
    vehicle_use: str = "personal"


def _confidence(i: Intake) -> tuple[float, list[str]]:
    score, gaps = 1.0, []
    text = i.description.lower()
    if i.photos == 0 and i.incident_type in ("collision", "glass", "vandalism", "weather"):
        score -= 0.3
        gaps.append("No photos of the damage")
    if len(i.description.strip()) < 40:
        score -= 0.25
        gaps.append("Description is too short to confirm what happened")
    if not i.amount_claimed:
        score -= 0.25
        gaps.append("No repair estimate or claimed amount")
    if i.incident_type == "other":
        score -= 0.2
        gaps.append("Cause of loss isn't identified")
    if any(w in text for w in VAGUE_WORDS):
        score -= 0.15
        gaps.append("Claimant is unsure of key facts")
    return round(max(0.0, min(1.0, score)), 2), gaps


def _fraud_signals(i: Intake) -> list[str]:
    signals = []
    if 0 <= (i.incident_date - i.policy_start_date).days <= 30:
        signals.append(f"Loss {(i.incident_date - i.policy_start_date).days} days after the policy started")
    if (i.reported_date - i.incident_date).days > 30:
        signals.append(f"Reported {(i.reported_date - i.incident_date).days} days after the incident")
    if i.amount_claimed and i.amount_claimed > 0.9 * i.vehicle_value:
        signals.append(f"Claimed ${i.amount_claimed:,.0f} against a ${i.vehicle_value:,.0f} vehicle")
    if i.prior_claims_12mo >= 2:
        signals.append(f"{i.prior_claims_12mo} other claims in the last 12 months")
    if i.incident_type == "theft" and not i.police_report:
        signals.append("Theft with no police report")
    return signals


def triage(i: Intake) -> dict:
    confidence, gaps = _confidence(i)
    text = i.description.lower()
    reasons: list[dict] = []
    path: str

    # 1. Coverage
    excluded = EXCLUDED_USE.get(i.vehicle_use)
    if not (i.policy_start_date <= i.incident_date <= i.policy_end_date):
        path = "not_covered"
        reasons.append({"rule": "Policy period", "detail": "The incident date is outside the policy period.",
                        "source": f"{POLICY_NAME} · Declarations · Page 1"})
    elif excluded:
        path = "not_covered"
        reasons.append({"rule": excluded[0], "detail": excluded[1], "source": SOURCE_EXCLUSIONS})
    elif any(w in text for w in WEAR_WORDS):
        path = "not_covered"
        reasons.append({"rule": "Wear, tear & breakdown", "detail": "Mechanical breakdowns and normal wear aren't covered.",
                        "source": SOURCE_EXCLUSIONS})
    else:
        signals = _fraud_signals(i)
        # 2. Fraud signals (two or more → SIU)
        if len(signals) >= 2:
            path = "fraud_review"
            reasons += [{"rule": "Fraud signal", "detail": s} for s in signals]
        # 3. Data quality
        elif confidence < LOW_CONFIDENCE_BELOW:
            path = "low_confidence"
            reasons += [{"rule": "Missing information", "detail": g} for g in gaps]
        # 4. Straight-through limit
        elif (i.amount_claimed or 0) > AUTO_APPROVE_LIMIT:
            path = "adjuster_review"
            reasons.append({"rule": "Straight-through limit",
                            "detail": f"${i.amount_claimed:,.0f} is above the ${AUTO_APPROVE_LIMIT:,.0f} auto-approve limit."})
        else:
            path = "auto_approve"
            reasons.append({"rule": "Covered", "detail": f"{COVERAGE_FOR[i.incident_type]} applies; no exclusions matched."})
            reasons.append({"rule": "Clean file", "detail": "No fraud signals and the intake is complete."})
            reasons.append({"rule": "Under limit",
                            "detail": f"${i.amount_claimed or 0:,.0f} is within the ${AUTO_APPROVE_LIMIT:,.0f} auto-approve limit."})
        if signals and path != "fraud_review":
            reasons += [{"rule": "Signal noted", "detail": s} for s in signals]

    deductible = DEDUCTIBLES.get(i.incident_type, 1000.0)
    payout = max(0.0, (i.amount_claimed or 0) - deductible) if path in ("auto_approve", "adjuster_review") else None
    return {
        "path": path,
        **PATH_META[path],
        "confidence": confidence,
        "coverage": COVERAGE_FOR.get(i.incident_type, "To be determined") if path != "not_covered" else None,
        "deductible": deductible,
        "estimated_payout": payout,
        "reasons": reasons,
        "missing": gaps,
        "policy": POLICY_NAME,
        "disclaimer": "Synthetic demo. Rules are illustrative, not a real carrier's underwriting or claims guidelines.",
    }


def intake_from_dict(d: dict) -> Intake:
    def _d(v: object) -> date:
        return v if isinstance(v, date) else date.fromisoformat(str(v))

    return Intake(
        incident_type=d["incident_type"], description=d["description"], incident_date=_d(d["incident_date"]),
        reported_date=_d(d["reported_date"]), policy_start_date=_d(d["policy_start_date"]),
        policy_end_date=_d(d["policy_end_date"]), amount_claimed=d.get("amount_claimed"),
        vehicle_value=float(d["vehicle_value"]), photos=int(d.get("photos", 0)),
        police_report=bool(d.get("police_report", False)), prior_claims_12mo=int(d.get("prior_claims_12mo", 0)),
        vehicle_use=d.get("vehicle_use", "personal"),
    )
