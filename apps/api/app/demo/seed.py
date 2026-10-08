"""Synthetic demo profile: a complete Insurance Digital Twin that works without carrier integrations."""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import (
    EOB,
    AIToolExecution,
    Asset,
    Authorization,
    Beneficiary,
    Bill,
    Carrier,
    Claim,
    ClaimEvent,
    Consent,
    Dependent,
    Document,
    HealthPlan,
    Household,
    Integration,
    Notification,
    Payment,
    Policy,
    PolicyCoverage,
    PolicyEndorsement,
    PolicyExclusion,
    Property,
    Provider,
    Quote,
    User,
    Vehicle,
)
from app.demo import policy_documents as docs
from app.rag.chunking import Page
from app.rag.ingest import extract_structured, index_pages

DEMO_EMAIL = "demo@insurepilot.ai"
DEMO_PASSWORD = "DemoPilot!2026"


def _dt(d: date, hour: int = 10) -> datetime:
    return datetime.combine(d, time(hour, 0), tzinfo=UTC)


def _add_document(db: Session, user: User, title: str, doc_type: str, pages: dict[int, str], *,
                  policy: Policy | None = None, claim: Claim | None = None, category: str | None = None,
                  summary: str | None = None) -> Document:
    full = "\n".join(pages.values())
    doc = Document(
        user_id=user.id, policy_id=policy.id if policy else None, claim_id=claim.id if claim else None,
        title=title, filename=f"{title.lower().replace(' ', '-')}.pdf", mime_type="application/pdf",
        size_bytes=len(full.encode()) * 12, doc_type=doc_type, status="ready",
        classification_confidence="high", extracted=extract_structured(full), summary=summary,
    )
    db.add(doc)
    db.flush()
    index_pages(db, doc, [Page(n, t) for n, t in sorted(pages.items())], category or (policy.category if policy else None))
    return doc


def seed_demo(db: Session, force: bool = False) -> User:
    existing = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if existing and not force:
        return existing
    if existing:
        db.delete(existing)
        db.flush()

    today = date.today()
    carriers = {c.short_name: c for c in db.scalars(select(Carrier))}

    def carrier(name: str, short: str, color: str, rating: str, phone: str) -> Carrier:
        if short not in carriers:
            carriers[short] = Carrier(name=name, short_name=short, brand_color=color, rating=rating, phone=phone,
                                      claims_email=f"claims@{short.lower()}.example")
            db.add(carriers[short])
        return carriers[short]

    northstar = carrier("Northstar Mutual", "Northstar", "#3B82F6", "A+", "1-800-555-0141")
    harborline = carrier("Harborline Insurance", "Harborline", "#0EA5E9", "A", "1-800-555-0177")
    bluepeak = carrier("Bluepeak Health", "Bluepeak", "#14B8A6", "A", "1-800-555-0123")
    evergreen = carrier("Evergreen Life", "Evergreen", "#22C55E", "A++", "1-800-555-0190")
    pawsure = carrier("Pawsure Pet Insurance", "Pawsure", "#F59E0B", "A-", "1-800-555-0166")
    wayfarer = carrier("Wayfarer Travel Protection", "Wayfarer", "#A855F7", "A-", "1-800-555-0108")

    household = Household(name="Morgan Household", address_city="Austin", address_state="TX")
    db.add(household)
    db.flush()
    user = User(
        email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), full_name="Alex Morgan", preferred_name="Alex",
        roles=["customer", "analyst"], household_id=household.id, is_demo=True, onboarding_complete=True,
        date_of_birth="1988-04-12", phone="512-555-0182",
        preferences={"theme": "system", "reduced_motion": False, "low_power_3d": False},
    )
    db.add(user)
    db.flush()
    db.add_all([
        Dependent(user_id=user.id, full_name="Jordan Morgan", relationship_type="spouse", birth_year=1989),
        Dependent(user_id=user.id, full_name="Riley Morgan", relationship_type="child", birth_year=today.year - 15),
    ])

    # ---- Assets
    car = Asset(user_id=user.id, kind="vehicle", label="2022 Toyota RAV4", estimated_value=28400)
    home = Asset(user_id=user.id, kind="property", label="Home · Austin, TX", estimated_value=465000)
    pet = Asset(user_id=user.id, kind="pet", label="Miso (dog)")
    db.add_all([car, home, pet])
    db.flush()
    db.add(Vehicle(asset_id=car.id, year=2022, make="Toyota", model="RAV4 XLE", vin="2T3W1RFV8NW000000", annual_mileage=11000))
    db.add(Property(asset_id=home.id, address_line="1420 Cedar Bend Dr", city="Austin", state="TX", year_built=2009,
                    square_feet=2350, estimated_rebuild_cost=410000))

    # ---- Policies
    auto = Policy(
        user_id=user.id, carrier_id=northstar.id, asset_id=car.id, category="auto", product_name="Personal Auto",
        policy_number="NSM-AU-4471923", status="pending_renewal", effective_date=today - timedelta(days=344),
        expiration_date=today + timedelta(days=21), premium_annual=1916, prior_premium_annual=1610, deductible=1000,
        summary="Full coverage on your 2022 RAV4 with $100k/$300k liability.",
        details={"vehicle": "2022 Toyota RAV4 XLE", "drivers": ["Alex Morgan", "Jordan Morgan"]},
        renewal_changes={
            "new_premium": 1916, "prior_premium": 1610,
            "factors": [
                {"label": "At-fault collision claim within 36 months", "status": "confirmed", "impact": 168,
                 "source": "Renewal notice · Page 31"},
                {"label": "Multi-policy discount removed (renters policy ended)", "status": "confirmed", "impact": 97,
                 "source": "Renewal notice · Page 31"},
                {"label": "Base rate change in your area", "status": "confirmed", "impact": None,
                 "source": "Renewal notice · Page 31"},
                {"label": "Vehicle aging (typically lowers premium slightly)", "status": "possible", "impact": None,
                 "source": "General rating practice — not stated by carrier"},
            ],
            "coverage_changes": [],
            "discount_opportunities": ["Safe-driver program", "Paperless billing", "Re-bundle with home policy"],
        },
    )
    home_policy = Policy(
        user_id=user.id, carrier_id=harborline.id, asset_id=home.id, category="home", product_name="Homeowners HO-3",
        policy_number="HBL-HO-2208815", status="active", effective_date=today - timedelta(days=120),
        expiration_date=today + timedelta(days=245), premium_annual=2184, prior_premium_annual=2090, deductible=2500,
        summary="Replacement-cost dwelling coverage with a water-backup endorsement.",
        details={"rebuild_estimate": 410000, "coverage_a": 320000},
    )
    health = Policy(
        user_id=user.id, carrier_id=bluepeak.id, category="health", product_name="Choice PPO 2500",
        policy_number="BPH-PPO-88213", status="active", effective_date=date(today.year, 1, 1),
        expiration_date=date(today.year, 12, 31), premium_annual=5880, prior_premium_annual=5640, deductible=2500,
        summary="Employer PPO. $2,500 deductible, 20% coinsurance in-network.",
    )
    life = Policy(
        user_id=user.id, carrier_id=evergreen.id, category="life", product_name="Term 20",
        policy_number="EVL-T20-551902", status="active", effective_date=date(2023, 3, 1),
        expiration_date=date(2043, 3, 1), premium_annual=612, prior_premium_annual=612,
        summary="$750,000 level term life insurance through 2043.",
    )
    pet_policy = Policy(
        user_id=user.id, carrier_id=pawsure.id, asset_id=pet.id, category="pet", product_name="Accident & Illness",
        policy_number="PAW-AI-30019", status="active", effective_date=today - timedelta(days=200),
        expiration_date=today + timedelta(days=165), premium_annual=456, prior_premium_annual=432, deductible=250,
        summary="80% reimbursement for Miso's accidents and illnesses, $10k annual limit.",
    )
    travel = Policy(
        user_id=user.id, carrier_id=wayfarer.id, category="travel", product_name="Annual Multi-Trip",
        policy_number="WFR-AMT-7781", status="lapsed", effective_date=today - timedelta(days=395),
        expiration_date=today - timedelta(days=30), premium_annual=289, prior_premium_annual=289,
        summary="Annual trip protection — expired last month.",
    )
    db.add_all([auto, home_policy, health, life, pet_policy, travel])
    db.flush()

    db.add_all([
        PolicyCoverage(policy_id=auto.id, code="BI", name="Bodily injury liability", limit_text="$100k / $300k",
                       limit_amount=300000, plain_language="Pays for injuries you cause to other people in an accident.",
                       source_section="Section 1 — Liability Coverage", source_page=6),
        PolicyCoverage(policy_id=auto.id, code="PD", name="Property damage liability", limit_amount=100000,
                       limit_text="$100,000", plain_language="Pays for damage you cause to other people's cars or property.",
                       source_section="Section 1 — Liability Coverage", source_page=6),
        PolicyCoverage(policy_id=auto.id, code="COLL", name="Collision", deductible=1000, limit_text="Actual cash value",
                       plain_language="Repairs your car after hitting another car or object. You pay the first $1,000.",
                       source_section="Section 4 — Collision Coverage", source_page=18),
        PolicyCoverage(policy_id=auto.id, code="COMP", name="Comprehensive", deductible=500, limit_text="Actual cash value",
                       plain_language="Covers theft, hail, fire, animals and glass. You pay the first $500.",
                       source_section="Section 5 — Comprehensive Coverage", source_page=20),
        PolicyCoverage(policy_id=auto.id, code="MED", name="Medical payments", limit_amount=5000, limit_text="$5,000/person",
                       plain_language="Pays medical bills for you and passengers, no matter who caused the accident.",
                       source_section="Section 2 — Medical Payments Coverage", source_page=10),
        PolicyCoverage(policy_id=auto.id, code="UM", name="Uninsured motorist", limit_text="$100k / $300k", limit_amount=300000,
                       plain_language="Protects you if a driver with no insurance (or a hit-and-run) injures you.",
                       source_section="Section 3 — Uninsured Motorist Coverage", source_page=12),
        PolicyCoverage(policy_id=auto.id, code="RENT", name="Rental reimbursement", limit_amount=1200, limit_text="$40/day · $1,200 max",
                       plain_language="Pays for a rental car while yours is being repaired after a covered claim.",
                       source_section="Section 6 — Rental Reimbursement", source_page=23),
        PolicyCoverage(policy_id=auto.id, code="ROAD", name="Roadside assistance", limit_text="4 calls/term",
                       plain_language="Towing, jump-starts, flat tires and lockouts.",
                       source_section="Section 7 — Roadside Assistance", source_page=24),
        PolicyExclusion(policy_id=auto.id, name="Rideshare use", source_section="Exclusions", source_page=27,
                        plain_language="Driving for Uber/Lyft isn't covered unless you add a rideshare endorsement."),
        PolicyExclusion(policy_id=auto.id, name="Wear, tear & breakdown", source_section="Exclusions", source_page=27,
                        plain_language="Mechanical breakdowns and normal wear aren't covered."),
        PolicyExclusion(policy_id=auto.id, name="Custom equipment over $1,000", source_section="Exclusions", source_page=27,
                        plain_language="Aftermarket parts above $1,000 must be listed on the policy to be covered."),

        PolicyCoverage(policy_id=home_policy.id, code="A", name="Dwelling", limit_amount=320000, limit_text="$320,000",
                       status="review", plain_language="Rebuilds your house. Estimated rebuild cost is about $410,000, so this may be low.",
                       source_section="Section I — Coverage A Dwelling", source_page=5),
        PolicyCoverage(policy_id=home_policy.id, code="B", name="Other structures", limit_amount=32000, limit_text="$32,000",
                       plain_language="Fences, sheds and detached garages.", source_section="Declarations Page", source_page=1),
        PolicyCoverage(policy_id=home_policy.id, code="C", name="Personal property", limit_amount=160000, limit_text="$160,000",
                       status="partial", plain_language="Your belongings — paid at depreciated value, with special limits on jewelry.",
                       source_section="Section I — Coverage C Personal Property", source_page=7),
        PolicyCoverage(policy_id=home_policy.id, code="D", name="Loss of use", limit_amount=64000, limit_text="$64,000",
                       plain_language="Hotel and extra living costs if you can't live at home after a covered loss.",
                       source_section="Section I — Coverage D Loss of Use", source_page=9),
        PolicyCoverage(policy_id=home_policy.id, code="E", name="Personal liability", limit_amount=300000, limit_text="$300,000",
                       plain_language="If someone is hurt at your home and sues you.", source_section="Section II — Coverage E Personal Liability", source_page=18),
        PolicyCoverage(policy_id=home_policy.id, code="FLOOD", name="Flood", status="not_covered", limit_text="Not covered",
                       plain_language="Flooding from outside water isn't covered. A separate flood policy is needed.",
                       source_section="Section I — Exclusions", source_page=14),
        PolicyExclusion(policy_id=home_policy.id, name="Water damage (flood, sewer backup, groundwater)", source_section="Section I — Exclusions",
                        source_page=14, plain_language="Floods and backed-up drains aren't covered by the main policy — but your water-backup endorsement adds some coverage back."),
        PolicyExclusion(policy_id=home_policy.id, name="Long-term seepage, mold, wear and tear", source_section="Section I — Exclusions",
                        source_page=14, plain_language="Slow leaks over 14+ days and mold aren't covered."),
        PolicyEndorsement(policy_id=home_policy.id, code="HO-WB", name="Water backup & sump overflow", limit_amount=10000,
                          premium_annual=85, source_section="Endorsement HO-WB", source_page=31,
                          plain_language="Adds up to $10,000 for water that backs up through drains or a sump pump. $1,000 deductible."),

        PolicyCoverage(policy_id=health.id, code="DED", name="Deductible", limit_amount=2500, limit_text="$2,500 in-network",
                       plain_language="What you pay each year before the plan shares costs (except copay visits).",
                       source_section="Summary of Benefits and Coverage", source_page=1),
        PolicyCoverage(policy_id=health.id, code="OOP", name="Out-of-pocket max", limit_amount=6500, limit_text="$6,500 in-network",
                       plain_language="The most you'll pay in a year for in-network care.", source_section="Summary of Benefits and Coverage", source_page=1),
        PolicyCoverage(policy_id=health.id, code="IMG", name="Advanced imaging (MRI/CT)", limit_text="20% after deductible",
                       status="partial", plain_language="Covered, but you pay 20% after your deductible and it needs prior approval.",
                       source_section="Section 7 — Prior Authorization", source_page=22),
        PolicyCoverage(policy_id=health.id, code="PCP", name="Primary care", limit_text="$30 copay",
                       plain_language="A flat $30 per regular doctor visit.", source_section="Summary of Benefits and Coverage", source_page=1),

        PolicyCoverage(policy_id=life.id, code="DB", name="Death benefit", limit_amount=750000, limit_text="$750,000",
                       plain_language="Paid to your beneficiaries if you pass away during the 20-year term.",
                       source_section="Policy Schedule", source_page=1),
        PolicyCoverage(policy_id=life.id, code="CB", name="Contingent beneficiary", status="review", limit_text="None named",
                       plain_language="No backup beneficiary is named. If your primary beneficiary can't receive the benefit, payment may be delayed by probate.",
                       source_section="Section 2 — Beneficiaries", source_page=4),
        PolicyCoverage(policy_id=pet_policy.id, code="AI", name="Accident & illness", limit_amount=10000, limit_text="80% · $10k/yr",
                       plain_language="Reimburses 80% of vet bills after a $250 yearly deductible.", source_section="Policy Declarations", source_page=1),
        PolicyExclusion(policy_id=pet_policy.id, name="Pre-existing & wellness", source_section="Exclusions", source_page=3,
                        plain_language="Conditions Miso had before enrollment and routine checkups aren't covered."),
        Beneficiary(policy_id=life.id, full_name="Jordan Morgan", relationship_type="spouse", designation="primary", share_percent=100),
    ])

    # ---- Health plan & providers
    db.add(HealthPlan(
        policy_id=health.id, plan_type="PPO", network_name="Bluepeak Choice", member_id="BPX448120931",
        deductible_individual=2500, deductible_met=2300, oop_max_individual=6500, oop_met=3180,
        coinsurance_in_network=20, coinsurance_out_network=40,
        copays={"primary_care": 30, "specialist": 60, "urgent_care": 75, "emergency_room": 350},
        benefits=[
            {"name": "Preventive care", "coverage": "Covered at 100% in-network"},
            {"name": "Physical therapy", "coverage": "$60 copay · 30 visits/year"},
            {"name": "Mental health (outpatient)", "coverage": "$30 copay"},
            {"name": "Generic drugs", "coverage": "$10 copay"},
        ],
        prior_auth_rules=[
            {"service": "MRI", "cpt": ["72148", "73721", "70553"], "required": True,
             "documentation": ["Physician order", "Clinical notes", "6 weeks of conservative therapy (for spine)"],
             "source": "Section 7 — Prior Authorization · Page 22"},
            {"service": "CT", "cpt": ["74177"], "required": True, "documentation": ["Physician order", "Clinical notes"],
             "source": "Section 7 — Prior Authorization · Page 22"},
        ],
        plan_year_end=date(today.year, 12, 31),
    ))
    providers = [
        Provider(name="St. Brightwater Medical Center", kind="hospital", specialty="General hospital", city="Austin", state="TX",
                 npi="1730001111", networks=["Bluepeak Choice", "Harbor Health"], rating=4.4, price_estimates={"72148": 1850, "29881": 4300}),
        Provider(name="Lakeside Imaging Center", kind="imaging", specialty="Radiology / MRI", city="Austin", state="TX",
                 npi="1730002222", networks=["Bluepeak Choice"], rating=4.7, price_estimates={"72148": 1150, "73721": 980}),
        Provider(name="Northside Advanced Imaging", kind="imaging", specialty="Radiology / MRI", city="Round Rock", state="TX",
                 npi="1730003333", networks=[], rating=4.5, price_estimates={"72148": 2400}),
        Provider(name="Capitol Anesthesia Partners", kind="physician", specialty="Anesthesiology", city="Austin", state="TX",
                 npi="1730004444", networks=[], rating=4.1),
        Provider(name="Austin Orthopedic & Spine", kind="clinic", specialty="Orthopedics", city="Austin", state="TX",
                 npi="1730005555", networks=["Bluepeak Choice"], rating=4.8),
        Provider(name="Cedar Park Family Medicine", kind="clinic", specialty="Primary care", city="Cedar Park", state="TX",
                 npi="1730006666", networks=["Bluepeak Choice"], rating=4.6),
    ]
    db.add_all(providers)
    db.flush()
    hospital, lakeside, _northside, anesthesia, ortho, _pcp = providers

    # ---- Claims
    auto_claim = Claim(
        user_id=user.id, policy_id=auto.id, claim_number="39102", category="auto", title="Rear-end collision on I-35",
        description="Another driver rear-ended the RAV4 at a stoplight. Rear bumper, liftgate and tail light damaged. No injuries.",
        status="in_review", stage="Estimate received", incident_date=today - timedelta(days=12), amount_claimed=4860,
        deductible_applied=1000, adjuster_name="Dana Reyes", adjuster_email="dana.reyes@northstar.example",
        missing_documents=["Police report copy"],
        deadlines=[{"label": "Send photos & police report", "due": (today + timedelta(days=18)).isoformat(),
                    "source": "Auto Policy · Conditions · Page 29"}],
        details={"other_party_at_fault": True, "subrogation_possible": True, "repair_shop": "Precision Collision Austin",
                 "rental_in_use": True, "rental_days_used": 9},
    )
    home_claim = Claim(
        user_id=user.id, policy_id=home_policy.id, claim_number="77310", category="home", title="Basement water damage",
        description="Water came up through the basement floor drain during a heavy storm, damaging flooring, drywall and a sofa.",
        status="denied", stage="Decision issued", incident_date=today - timedelta(days=48), amount_claimed=8750,
        adjuster_name="Sam Whitfield", adjuster_email="s.whitfield@harborline.example",
        denial_reason="Loss excluded under Section I — Exclusions, Water: water which backs up through sewers or drains.",
        deadlines=[{"label": "Request reconsideration", "due": (today + timedelta(days=29)).isoformat(),
                    "source": "Home Policy · Appeals and Dispute Resolution · Page 33"}],
        details={"cause_reported": "Drain backup during storm", "plumber_report": False},
    )
    med_claim = Claim(
        user_id=user.id, policy_id=health.id, claim_number="MED-55821", category="health", title="Outpatient knee arthroscopy",
        description="Outpatient knee arthroscopy at St. Brightwater Medical Center.", status="paid", stage="Processed",
        incident_date=today - timedelta(days=41), amount_claimed=8400, amount_paid=1540,
    )
    db.add_all([auto_claim, home_claim, med_claim])
    db.flush()
    d = auto_claim.incident_date
    db.add_all([
        ClaimEvent(claim_id=auto_claim.id, kind="incident", title="Accident occurred", occurred_at=_dt(d, 17),
                   description="Rear-ended at a stoplight on I-35 near 38th St."),
        ClaimEvent(claim_id=auto_claim.id, kind="submitted", title="Claim submitted", occurred_at=_dt(d + timedelta(days=1)),
                   description="Submitted with 6 photos."),
        ClaimEvent(claim_id=auto_claim.id, kind="assigned", title="Adjuster assigned", occurred_at=_dt(d + timedelta(days=2)),
                   description="Dana Reyes is handling your claim."),
        ClaimEvent(claim_id=auto_claim.id, kind="review", title="Damage reviewed", occurred_at=_dt(d + timedelta(days=6)),
                   description="Photo inspection completed."),
        ClaimEvent(claim_id=auto_claim.id, kind="estimate", title="Estimate received", status="current",
                   occurred_at=_dt(d + timedelta(days=9)), description="Repair estimate of $4,860 from Precision Collision."),
        ClaimEvent(claim_id=auto_claim.id, kind="payment", title="Payment pending", status="upcoming",
                   occurred_at=_dt(today + timedelta(days=5)), description="Waiting on police report before payment."),
        ClaimEvent(claim_id=home_claim.id, kind="incident", title="Water entered basement", occurred_at=_dt(home_claim.incident_date)),
        ClaimEvent(claim_id=home_claim.id, kind="submitted", title="Claim submitted", occurred_at=_dt(home_claim.incident_date + timedelta(days=2))),
        ClaimEvent(claim_id=home_claim.id, kind="inspection", title="Adjuster inspection", occurred_at=_dt(home_claim.incident_date + timedelta(days=9))),
        ClaimEvent(claim_id=home_claim.id, kind="decision", title="Claim denied", status="blocked",
                   occurred_at=_dt(home_claim.incident_date + timedelta(days=19)), description="Water exclusion cited."),
        ClaimEvent(claim_id=home_claim.id, kind="appeal", title="Reconsideration window", status="upcoming",
                   occurred_at=_dt(today + timedelta(days=29))),
        ClaimEvent(claim_id=med_claim.id, kind="service", title="Procedure performed", occurred_at=_dt(med_claim.incident_date)),
        ClaimEvent(claim_id=med_claim.id, kind="processed", title="EOB issued", occurred_at=_dt(med_claim.incident_date + timedelta(days=21))),
    ])

    # ---- Bills, EOB, authorization
    db.add(EOB(
        user_id=user.id, claim_id=med_claim.id, provider_id=hospital.id, service_date=med_claim.incident_date,
        billed_amount=8400, allowed_amount=4300, plan_paid=1540, deductible=2000, coinsurance=760, copay=0,
        patient_responsibility=2760, network_status="in_network", remark_codes=["PR-1 Deductible", "PR-2 Coinsurance"],
        notes="Includes anesthesia services billed by Capitol Anesthesia Partners.",
    ))
    db.add(Bill(
        user_id=user.id, provider_id=hospital.id, claim_id=med_claim.id, service_description="Outpatient knee arthroscopy (CPT 29881)",
        service_date=med_claim.incident_date, total_charge=8400, amount_due=2760, due_date=today + timedelta(days=24),
        line_items=[
            {"description": "Facility fee — outpatient surgery", "charge": 5200, "provider": "St. Brightwater Medical Center"},
            {"description": "Surgeon — arthroscopy, knee", "charge": 2100, "provider": "Austin Orthopedic & Spine"},
            {"description": "Anesthesia services", "charge": 1100, "provider": "Capitol Anesthesia Partners",
             "network_note": "Provider not listed in Bluepeak Choice directory"},
        ],
    ))
    db.add(Authorization(
        user_id=user.id, policy_id=health.id, provider_id=lakeside.id, procedure_name="MRI, lumbar spine without contrast",
        cpt_code="72148", status="pending", requested_on=today - timedelta(days=5), decision_due=today + timedelta(days=10),
        requirements=[
            {"item": "Physician order", "status": "complete"},
            {"item": "Clinical notes", "status": "complete"},
            {"item": "6 weeks of conservative therapy documented", "status": "missing"},
        ],
        notes="Ordered by Austin Orthopedic & Spine for persistent lower back pain.",
    ))

    # ---- Documents (indexed for RAG)
    _add_document(db, user, "Auto Policy", "policy", docs.AUTO_POLICY, policy=auto,
                  summary="Northstar Mutual personal auto policy for the 2022 RAV4, including the renewal premium notice.")
    _add_document(db, user, "Home Policy", "policy", docs.HOME_POLICY, policy=home_policy,
                  summary="Harborline HO-3 homeowners policy with water-backup endorsement HO-WB.")
    _add_document(db, user, "Health Plan Benefits", "policy", docs.HEALTH_POLICY, policy=health,
                  summary="Bluepeak Choice PPO 2500 summary of benefits, network rules, prior authorization and appeals.")
    _add_document(db, user, "Life Policy", "policy", docs.LIFE_POLICY, policy=life,
                  summary="Evergreen Term 20 life policy — $750,000 death benefit.")
    _add_document(db, user, "Pet Policy", "policy", docs.PET_POLICY, policy=pet_policy,
                  summary="Pawsure accident & illness plan for Miso.")
    _add_document(db, user, "Home Claim Denial Letter", "claim_letter", {1: f"""CLAIM DETERMINATION
Claim number 77310. Date of loss {home_claim.incident_date:%B %d, %Y}. We have reviewed your claim for water damage to the basement.
Our inspection found water entered through the basement floor drain during a storm. Your policy excludes water which backs up through sewers or drains (Section I — Exclusions, Water, page 14).
Accordingly, your claim is denied. If you have additional information, please submit it within 60 days of this letter. Adjuster: Sam Whitfield."""},
                  policy=home_policy, claim=home_claim, category="home",
                  summary="Harborline denied the basement water claim, citing the water exclusion for drain backup.")
    _add_document(db, user, "Repair Estimate — Precision Collision", "repair_estimate", {1: """REPAIR ESTIMATE
Vehicle: 2022 Toyota RAV4 XLE. Rear bumper cover replace $1,240. Liftgate repair $1,380. Tail lamp assembly (left) $410.
Refinish and blend $920. Labor 14.5 hours $910. Total estimate $4,860. Estimate valid for 30 days."""},
                  policy=auto, claim=auto_claim, category="auto", summary="Body shop estimate totaling $4,860.")
    _add_document(db, user, "Explanation of Benefits — Knee Arthroscopy", "eob", {1: """EXPLANATION OF BENEFITS — THIS IS NOT A BILL
Bluepeak Health. Claim MED-55821. Provider: St. Brightwater Medical Center. Amount billed $8,400.00. Allowed amount $4,300.00.
Applied to deductible $2,000.00. Coinsurance $760.00. Plan paid $1,540.00. Patient responsibility $2,760.00.
Includes anesthesia services by Capitol Anesthesia Partners. If you have questions, you may file an appeal within 180 days."""},
                  policy=health, claim=med_claim, category="health", summary="EOB shows you owe $2,760 of an $8,400 charge.")
    _add_document(db, user, "Hospital Bill — St. Brightwater", "medical_bill", {1: f"""PATIENT STATEMENT
St. Brightwater Medical Center. Statement date {today - timedelta(days=6):%B %d, %Y}. Total charges $8,400.00.
Insurance payments $1,540.00. Insurance adjustments $4,100.00. Amount due $2,760.00. Please pay by {today + timedelta(days=24):%B %d, %Y}."""},
                  policy=health, claim=med_claim, category="health", summary="Hospital statement asking for $2,760.")

    # ---- Quotes for comparison/shopping (mock marketplace)
    db.add_all([
        Quote(user_id=user.id, category="auto", carrier_name="Lumen Auto", premium_annual=1742, deductible=1000,
              coverages={"liability": "$100k/$300k/$100k", "collision_deductible": 1000, "comprehensive_deductible": 500,
                         "rental": "$40/day · $1,200", "roadside": "Included", "medical_payments": 5000},
              exclusions=["Rideshare use"], add_ons=["Accident forgiveness (+$64/yr)"], valid_until=today + timedelta(days=30)),
        Quote(user_id=user.id, category="auto", carrier_name="Cascade Insurance", premium_annual=1688, deductible=1000,
              coverages={"liability": "$100k/$300k/$100k", "collision_deductible": 1000, "comprehensive_deductible": 1000,
                         "rental": "$30/day · $900", "roadside": "Not included", "medical_payments": 2500},
              exclusions=["Rideshare use", "Custom equipment over $500"], add_ons=["Roadside (+$24/yr)"], valid_until=today + timedelta(days=30)),
        Quote(user_id=user.id, category="auto", carrier_name="Meridian Direct", premium_annual=1812, deductible=500,
              coverages={"liability": "$250k/$500k/$100k", "collision_deductible": 500, "comprehensive_deductible": 500,
                         "rental": "$50/day · $1,500", "roadside": "Included", "medical_payments": 5000},
              exclusions=["Rideshare use"], add_ons=["New-car replacement"], valid_until=today + timedelta(days=30)),
    ])

    # ---- Payments
    for i in range(3):
        db.add(Payment(user_id=user.id, policy_id=auto.id, amount=134.17, due_date=today - timedelta(days=30 * (i + 1)),
                       paid_date=today - timedelta(days=30 * (i + 1)), status="paid", method_last4="4242"))
    db.add(Payment(user_id=user.id, policy_id=auto.id, amount=159.67, due_date=today + timedelta(days=21), status="scheduled", method_last4="4242"))
    db.add(Payment(user_id=user.id, policy_id=home_policy.id, amount=182.00, due_date=today + timedelta(days=9), status="scheduled", method_last4="4242"))

    # ---- Privacy: consents & integrations
    db.add_all([
        Consent(user_id=user.id, scope="documents.ai_processing", purpose="Let AI read your uploaded documents to explain and organize them."),
        Consent(user_id=user.id, scope="health_data.ai_analysis", purpose="Let AI analyze EOBs, bills and benefits to find discrepancies."),
        Consent(user_id=user.id, scope="communications.drafts", purpose="Let AI draft emails to insurers. Nothing is sent without your approval."),
        Consent(user_id=user.id, scope="marketplace.quotes", purpose="Share a coverage profile (no personal identifiers) to fetch comparable quotes.", granted=False),
    ])
    db.add_all([
        Integration(user_id=user.id, provider="Northstar Mutual", kind="carrier", data_shared=["Policy details", "Claims", "Billing"], connected_on=today - timedelta(days=60)),
        Integration(user_id=user.id, provider="Bluepeak Health (FHIR)", kind="health_payer", data_shared=["Coverage", "EOBs", "Prior authorizations"], connected_on=today - timedelta(days=60)),
        Integration(user_id=user.id, provider="Email (drafts only)", kind="email", data_shared=["Outgoing drafts you approve"], connected_on=today - timedelta(days=60)),
    ])

    # ---- Notifications
    db.add_all([
        Notification(user_id=user.id, title="Your adjuster requested another document", body="Claim 39102 needs a copy of the police report.",
                     category="claims", priority=1, link="/claims"),
        Notification(user_id=user.id, title="Auto policy renews in 21 days", body="Your premium is increasing 19% at renewal.",
                     category="renewal", priority=1, link="/policies"),
        Notification(user_id=user.id, title="Prior authorization pending", body="MRI at Lakeside Imaging — one requirement may be missing.",
                     category="health", priority=2, link="/health"),
        Notification(user_id=user.id, title="Possible provider-network mismatch", body="An anesthesia provider on your knee procedure isn't in the Bluepeak directory.",
                     category="health", priority=2, link="/health"),
        Notification(user_id=user.id, title="Travel coverage expired", body="Your annual travel plan lapsed 30 days ago.",
                     category="policy", priority=3, link="/wallet", read=True),
    ])

    for agent, tool, summary, days in [
        ("Claims Agent", "get_claim_status", "Checked status of claim 39102", 1),
        ("Document Intelligence Agent", "classify_document", "Classified hospital bill and linked it to claim MED-55821", 6),
        ("Renewal Agent", "get_policy", "Compared auto renewal premium with prior term", 2),
    ]:
        db.add(AIToolExecution(user_id=user.id, agent=agent, tool=tool, summary=summary, latency_ms=180,
                               created_at=datetime.now(UTC) - timedelta(days=days)))

    db.flush()
    from app.services.digital_twin import rebuild_graph

    rebuild_graph(db, user.id)
    db.commit()
    return user
