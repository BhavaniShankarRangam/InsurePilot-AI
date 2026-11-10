"""Five synthetic claims that walk the triage queue through every path. Dates are relative to today.

No real people, addresses or policy numbers: all names and details are invented.
"""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TriageClaim


def _samples(today: date) -> list[dict]:
    d = lambda n: (today - timedelta(days=n)).isoformat()  # noqa: E731
    term = {"policy_start_date": d(200), "policy_end_date": (today + timedelta(days=165)).isoformat()}
    return [
        {"claim_number": "TRI-1001", "claimant": "Priya Natarajan", "title": "Parking-lot bumper scrape",
         "expected_path": "auto_approve",
         "intake": {**term, "incident_type": "collision", "vehicle_use": "personal",
                    "description": "Backed into a concrete pillar in a grocery store parking garage. Rear bumper cover "
                                   "cracked and scuffed, no other damage, nobody hurt.",
                    "incident_date": d(3), "reported_date": d(2), "amount_claimed": 1850, "vehicle_value": 24500,
                    "photos": 4, "police_report": False, "prior_claims_12mo": 0}},
        {"claim_number": "TRI-1002", "claimant": "Marcus Oyelaran", "title": "Windshield cracked by road debris",
         "expected_path": "auto_approve",
         "intake": {**term, "incident_type": "glass", "vehicle_use": "commute",
                    "description": "A rock thrown up by a gravel truck on the highway hit the windshield. The chip spread "
                                   "into a 14-inch crack across the driver's side.",
                    "incident_date": d(1), "reported_date": d(1), "amount_claimed": 960, "vehicle_value": 31200,
                    "photos": 2, "police_report": False, "prior_claims_12mo": 0}},
        {"claim_number": "TRI-1003", "claimant": "Devon Halstrom", "title": "Vehicle stolen from driveway",
         "expected_path": "fraud_review",
         "intake": {"policy_start_date": d(50), "policy_end_date": (today + timedelta(days=315)).isoformat(),
                    "incident_type": "theft", "vehicle_use": "personal",
                    "description": "Car was taken from the driveway overnight. Keys were inside the house. Owner asks for "
                                   "a cash settlement for the full value plus aftermarket wheels and stereo.",
                    "incident_date": d(41), "reported_date": d(0), "amount_claimed": 31500, "vehicle_value": 28400,
                    "photos": 0, "police_report": False, "prior_claims_12mo": 2}},
        {"claim_number": "TRI-1004", "claimant": "Sofia Lindqvist", "title": "Side-swipe while driving for a rideshare app",
         "expected_path": "not_covered",
         "intake": {**term, "incident_type": "collision", "vehicle_use": "rideshare",
                    "description": "Was driving a passenger for a rideshare app when another car merged into the passenger "
                                   "side. Two doors dented, mirror broken. Passenger was not hurt.",
                    "incident_date": d(5), "reported_date": d(4), "amount_claimed": 3400, "vehicle_value": 19800,
                    "photos": 5, "police_report": True, "prior_claims_12mo": 0}},
        {"claim_number": "TRI-1005", "claimant": "Tomás Reinholt", "title": "Damage found, cause unknown",
         "expected_path": "low_confidence",
         "intake": {**term, "incident_type": "other", "vehicle_use": "personal",
                    "description": "Found damage on the car, not sure when it happened.",
                    "incident_date": d(6), "reported_date": d(2), "amount_claimed": None, "vehicle_value": 22100,
                    "photos": 0, "police_report": False, "prior_claims_12mo": 0}},
    ]


def seed_triage_samples(db: Session) -> int:
    """Creates or refreshes the five sample claims (dates move with today). Returns how many exist."""
    existing = {c.claim_number: c for c in db.scalars(select(TriageClaim))}
    for order, s in enumerate(_samples(date.today())):
        row = existing.get(s["claim_number"]) or TriageClaim(claim_number=s["claim_number"])
        row.claimant, row.title, row.expected_path, row.intake, row.sort_order = (
            s["claimant"], s["title"], s["expected_path"], s["intake"], order)
        db.add(row)
    db.commit()
    return len(_samples(date.today()))
