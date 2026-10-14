from datetime import date

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EncryptedString, IdMixin, TimestampMixin


class HealthPlan(IdMixin, TimestampMixin, Base):
    __tablename__ = "health_plans"

    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), unique=True)
    plan_type: Mapped[str] = mapped_column(String(10))  # PPO|HMO|EPO|HDHP
    network_name: Mapped[str] = mapped_column(String(80))
    member_id: Mapped[str] = mapped_column(EncryptedString)
    deductible_individual: Mapped[float] = mapped_column(Numeric(10, 2))
    deductible_met: Mapped[float] = mapped_column(Numeric(10, 2))
    oop_max_individual: Mapped[float] = mapped_column(Numeric(10, 2))
    oop_met: Mapped[float] = mapped_column(Numeric(10, 2))
    coinsurance_in_network: Mapped[int] = mapped_column(default=20)
    coinsurance_out_network: Mapped[int] = mapped_column(default=40)
    copays: Mapped[dict] = mapped_column(JSON, default=dict)
    benefits: Mapped[list] = mapped_column(JSON, default=list)
    prior_auth_rules: Mapped[list] = mapped_column(JSON, default=list)
    plan_year_end: Mapped[date] = mapped_column(Date)


class Provider(IdMixin, TimestampMixin, Base):
    __tablename__ = "providers"

    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(30))  # hospital|clinic|physician|imaging|lab
    specialty: Mapped[str | None] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(2))
    npi: Mapped[str | None] = mapped_column(String(10))
    networks: Mapped[list] = mapped_column(JSON, default=list)
    accepting_patients: Mapped[bool] = mapped_column(Boolean, default=True)
    rating: Mapped[float | None] = mapped_column(Numeric(2, 1))
    price_estimates: Mapped[dict] = mapped_column(JSON, default=dict)  # cpt -> negotiated estimate


class Authorization(IdMixin, TimestampMixin, Base):
    __tablename__ = "authorizations"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"))
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"))
    procedure_name: Mapped[str] = mapped_column(String(160))
    cpt_code: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20))  # draft|submitted|pending|approved|denied
    requested_on: Mapped[date] = mapped_column(Date)
    decision_due: Mapped[date | None] = mapped_column(Date)
    requirements: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
