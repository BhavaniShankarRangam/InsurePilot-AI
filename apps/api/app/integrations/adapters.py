"""External-system adapter interfaces and mock implementations.

Each Protocol is the contract a real integration must satisfy. The mocks operate on the
synthetic Digital Twin so the product is fully functional before carrier APIs exist.
"""

from datetime import UTC, date, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import EOB, Claim, ClaimEvent, HealthPlan, Policy, Provider, Quote

log = get_logger(__name__)


# ---------- Carrier systems -------------------------------------------------
class CarrierAdapter(Protocol):
    def fetch_policy(self, policy: Policy) -> dict: ...
    def claim_status(self, claim: Claim) -> dict: ...
    def submit_claim(self, claim: Claim, packet: dict) -> dict: ...


class MockCarrierAdapter:
    """Simulates a carrier REST API (policy admin + claims)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def fetch_policy(self, policy: Policy) -> dict:
        return {"source": "mock-carrier-api", "carrier": policy.carrier.name, "status": policy.status,
                "premium_annual": float(policy.premium_annual), "expires": policy.expiration_date.isoformat()}

    def claim_status(self, claim: Claim) -> dict:
        return {"source": "mock-carrier-api", "claim_number": claim.claim_number, "status": claim.status, "stage": claim.stage,
                "adjuster": claim.adjuster_name, "outstanding_items": claim.missing_documents}

    def submit_claim(self, claim: Claim, packet: dict) -> dict:
        claim.status = "submitted"
        claim.stage = "Claim submitted"
        self.db.add(ClaimEvent(claim_id=claim.id, kind="submitted", title="Claim submitted",
                               description="Submitted through InsurePilot after your approval.", occurred_at=datetime.now(UTC)))
        return {"confirmation": f"MOCK-{claim.claim_number}", "received_at": datetime.now(UTC).isoformat()}


# ---------- Health payer (FHIR R4) -----------------------------------------
class HealthPayerAdapter(Protocol):
    def coverage(self, plan: HealthPlan) -> dict: ...
    def explanation_of_benefit(self, eob: EOB) -> dict: ...


class MockFHIRPayerAdapter:
    """Returns FHIR R4-shaped resources (Coverage, ExplanationOfBenefit)."""

    def coverage(self, plan: HealthPlan) -> dict:
        return {
            "resourceType": "Coverage",
            "status": "active",
            "type": {"text": plan.plan_type},
            "class": [{"type": {"text": "network"}, "value": plan.network_name}],
            "costToBeneficiary": [
                {"type": {"text": "deductible"}, "valueMoney": {"value": float(plan.deductible_individual), "currency": "USD"}},
                {"type": {"text": "coinsurance"}, "valueQuantity": {"value": plan.coinsurance_in_network, "unit": "%"}},
            ],
        }

    def explanation_of_benefit(self, eob: EOB) -> dict:
        def money(v) -> dict:
            return {"value": float(v), "currency": "USD"}

        return {
            "resourceType": "ExplanationOfBenefit",
            "status": "active",
            "outcome": "complete",
            "total": [
                {"category": {"text": "submitted"}, "amount": money(eob.billed_amount)},
                {"category": {"text": "eligible"}, "amount": money(eob.allowed_amount)},
                {"category": {"text": "benefit"}, "amount": money(eob.plan_paid)},
                {"category": {"text": "deductible"}, "amount": money(eob.deductible)},
                {"category": {"text": "coinsurance"}, "amount": money(eob.coinsurance)},
            ],
        }


# ---------- Provider directory ---------------------------------------------
class ProviderDirectory(Protocol):
    def search(self, query: str, network: str | None) -> list[Provider]: ...
    def network_status(self, provider: Provider, network: str) -> dict: ...


class MockProviderDirectory:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(self, query: str, network: str | None = None) -> list[Provider]:
        q = query.lower()
        items = list(self.db.scalars(select(Provider)))
        hits = [p for p in items if any(w in f"{p.name} {p.specialty} {p.kind}".lower() for w in q.split() if len(w) > 2)]
        return hits or items

    def network_status(self, provider: Provider, network: str) -> dict:
        in_network = network in (provider.networks or [])
        return {"provider": provider.name, "network": network, "in_network": in_network,
                "verified_on": date.today().isoformat(), "source": "mock-provider-directory",
                "note": None if in_network else "Not found in the plan directory. Confirm with the provider and payer."}


# ---------- Quote marketplace ----------------------------------------------
class QuoteMarketplace(Protocol):
    def quotes(self, user_id: str, category: str, profile: dict) -> list[Quote]: ...


class MockQuoteMarketplace:
    def __init__(self, db: Session) -> None:
        self.db = db

    def quotes(self, user_id: str, category: str, profile: dict) -> list[Quote]:
        return list(self.db.scalars(select(Quote).where(Quote.user_id == user_id, Quote.category == category)))


# ---------- Email -----------------------------------------------------------
class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str) -> dict: ...


class MockEmailSender:
    """Records the message instead of sending it. Swap for SES/SendGrid/Gmail API."""

    def send(self, to: str, subject: str, body: str) -> dict:
        log.info("mock email sent", extra={"fields": {"subject": subject[:80]}})
        return {"status": "delivered (simulated)", "to": to, "message_id": f"mock-{abs(hash(subject + body)) % 10**8}"}
