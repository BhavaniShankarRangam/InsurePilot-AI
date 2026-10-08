"""Loads a user's full insurance portfolio in a few queries for services and agents."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    EOB,
    Asset,
    Authorization,
    Bill,
    Claim,
    Document,
    HealthPlan,
    Notification,
    Policy,
    Provider,
    Quote,
    User,
)


@dataclass
class Portfolio:
    user: User
    policies: list[Policy]
    claims: list[Claim]
    assets: list[Asset]
    health_plan: HealthPlan | None
    authorizations: list[Authorization]
    bills: list[Bill]
    eobs: list[EOB]
    documents: list[Document]
    providers: dict[str, Provider]
    quotes: list[Quote]
    notifications: list[Notification]

    @property
    def active_policies(self) -> list[Policy]:
        return [p for p in self.policies if p.status in ("active", "pending_renewal")]

    def policy(self, category: str) -> Policy | None:
        return next((p for p in self.active_policies if p.category == category), None) or next(
            (p for p in self.policies if p.category == category), None
        )

    def policy_by_id(self, policy_id: str) -> Policy | None:
        return next((p for p in self.policies if p.id == policy_id), None)

    def claim_by_ref(self, ref: str) -> Claim | None:
        return next((c for c in self.claims if c.id == ref or c.claim_number == ref), None)

    @property
    def open_claims(self) -> list[Claim]:
        return [c for c in self.claims if c.status in ("draft", "submitted", "in_review")]

    def days_until(self, d: date) -> int:
        return (d - date.today()).days


def load_portfolio(db: Session, user_id: str) -> Portfolio:
    user = db.get(User, user_id)
    if user is None:
        raise LookupError("user not found")
    policies = list(db.scalars(
        select(Policy).where(Policy.user_id == user_id).options(
            selectinload(Policy.carrier), selectinload(Policy.coverages), selectinload(Policy.exclusions),
            selectinload(Policy.endorsements), selectinload(Policy.beneficiaries),
        ).order_by(Policy.category)
    ))
    policy_ids = [p.id for p in policies]
    health_plan = db.scalar(select(HealthPlan).where(HealthPlan.policy_id.in_(policy_ids))) if policy_ids else None
    return Portfolio(
        user=user,
        policies=policies,
        claims=list(db.scalars(select(Claim).where(Claim.user_id == user_id).options(selectinload(Claim.events))
                               .order_by(Claim.incident_date.desc()))),
        assets=list(db.scalars(select(Asset).where(Asset.user_id == user_id))),
        health_plan=health_plan,
        authorizations=list(db.scalars(select(Authorization).where(Authorization.user_id == user_id))),
        bills=list(db.scalars(select(Bill).where(Bill.user_id == user_id))),
        eobs=list(db.scalars(select(EOB).where(EOB.user_id == user_id))),
        documents=list(db.scalars(select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc()))),
        providers={p.id: p for p in db.scalars(select(Provider))},
        quotes=list(db.scalars(select(Quote).where(Quote.user_id == user_id))),
        notifications=list(db.scalars(select(Notification).where(Notification.user_id == user_id)
                                      .order_by(Notification.priority, Notification.created_at.desc()))),
    )
