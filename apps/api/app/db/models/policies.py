from datetime import date

from sqlalchemy import JSON, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, EncryptedString, IdMixin, TimestampMixin


class Carrier(IdMixin, TimestampMixin, Base):
    __tablename__ = "carriers"

    name: Mapped[str] = mapped_column(String(120), unique=True)
    short_name: Mapped[str] = mapped_column(String(40))
    phone: Mapped[str | None] = mapped_column(String(30))
    claims_email: Mapped[str | None] = mapped_column(String(120))
    rating: Mapped[str | None] = mapped_column(String(10))
    brand_color: Mapped[str | None] = mapped_column(String(9))


class Policy(IdMixin, TimestampMixin, Base):
    __tablename__ = "policies"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    carrier_id: Mapped[str] = mapped_column(ForeignKey("carriers.id"))
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"))
    category: Mapped[str] = mapped_column(String(20), index=True)  # auto|home|renters|health|life|travel|pet|commercial
    product_name: Mapped[str] = mapped_column(String(120))
    policy_number: Mapped[str] = mapped_column(EncryptedString)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|pending_renewal|lapsed|cancelled|quote
    effective_date: Mapped[date] = mapped_column(Date)
    expiration_date: Mapped[date] = mapped_column(Date)
    premium_annual: Mapped[float] = mapped_column(Numeric(12, 2))
    prior_premium_annual: Mapped[float | None] = mapped_column(Numeric(12, 2))
    billing_frequency: Mapped[str] = mapped_column(String(20), default="monthly")
    deductible: Mapped[float | None] = mapped_column(Numeric(12, 2))
    summary: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    renewal_changes: Mapped[dict] = mapped_column(JSON, default=dict)

    carrier: Mapped[Carrier] = relationship()
    coverages: Mapped[list["PolicyCoverage"]] = relationship(back_populates="policy", cascade="all, delete-orphan")
    exclusions: Mapped[list["PolicyExclusion"]] = relationship(back_populates="policy", cascade="all, delete-orphan")
    endorsements: Mapped[list["PolicyEndorsement"]] = relationship(back_populates="policy", cascade="all, delete-orphan")
    beneficiaries: Mapped[list["Beneficiary"]] = relationship(back_populates="policy", cascade="all, delete-orphan")


class PolicyCoverage(IdMixin, Base):
    __tablename__ = "policy_coverages"

    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120))
    plain_language: Mapped[str] = mapped_column(Text)
    limit_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    limit_text: Mapped[str | None] = mapped_column(String(80))
    deductible: Mapped[float | None] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default="covered")  # covered|partial|not_covered|review
    source_section: Mapped[str | None] = mapped_column(String(80))
    source_page: Mapped[int | None]
    policy: Mapped[Policy] = relationship(back_populates="coverages")


class PolicyExclusion(IdMixin, Base):
    __tablename__ = "policy_exclusions"

    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    plain_language: Mapped[str] = mapped_column(Text)
    source_section: Mapped[str | None] = mapped_column(String(80))
    source_page: Mapped[int | None]
    policy: Mapped[Policy] = relationship(back_populates="exclusions")


class PolicyEndorsement(IdMixin, Base):
    __tablename__ = "policy_endorsements"

    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120))
    plain_language: Mapped[str] = mapped_column(Text)
    limit_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    premium_annual: Mapped[float | None] = mapped_column(Numeric(10, 2))
    source_section: Mapped[str | None] = mapped_column(String(80))
    source_page: Mapped[int | None]
    policy: Mapped[Policy] = relationship(back_populates="endorsements")


class Beneficiary(IdMixin, Base):
    __tablename__ = "beneficiaries"

    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(EncryptedString)
    relationship_type: Mapped[str] = mapped_column(String(30))
    designation: Mapped[str] = mapped_column(String(20))  # primary | contingent
    share_percent: Mapped[int] = mapped_column(default=100)
    policy: Mapped[Policy] = relationship(back_populates="beneficiaries")


class Payment(IdMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    due_date: Mapped[date] = mapped_column(Date)
    paid_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")  # scheduled|paid|overdue
    method_last4: Mapped[str | None] = mapped_column(String(4))


class Quote(IdMixin, TimestampMixin, Base):
    __tablename__ = "quotes"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(20))
    carrier_name: Mapped[str] = mapped_column(String(120))
    premium_annual: Mapped[float] = mapped_column(Numeric(12, 2))
    deductible: Mapped[float | None] = mapped_column(Numeric(12, 2))
    coverages: Mapped[dict] = mapped_column(JSON, default=dict)
    exclusions: Mapped[list] = mapped_column(JSON, default=list)
    add_ons: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(40), default="mock_marketplace")
    valid_until: Mapped[date | None] = mapped_column(Date)
