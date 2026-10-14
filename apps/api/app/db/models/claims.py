from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin, utcnow


class Claim(IdMixin, TimestampMixin, Base):
    __tablename__ = "claims"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    claim_number: Mapped[str] = mapped_column(String(30), index=True)
    category: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))  # draft|submitted|in_review|approved|denied|paid|closed
    stage: Mapped[str] = mapped_column(String(40))
    incident_date: Mapped[date] = mapped_column(Date)
    amount_claimed: Mapped[float | None] = mapped_column(Numeric(12, 2))
    amount_paid: Mapped[float | None] = mapped_column(Numeric(12, 2))
    deductible_applied: Mapped[float | None] = mapped_column(Numeric(12, 2))
    adjuster_name: Mapped[str | None] = mapped_column(String(80))
    adjuster_email: Mapped[str | None] = mapped_column(String(120))
    denial_reason: Mapped[str | None] = mapped_column(Text)
    missing_documents: Mapped[list] = mapped_column(JSON, default=list)
    deadlines: Mapped[list] = mapped_column(JSON, default=list)
    details: Mapped[dict] = mapped_column(JSON, default=dict)

    events: Mapped[list["ClaimEvent"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan", order_by="ClaimEvent.occurred_at"
    )


class ClaimEvent(IdMixin, Base):
    __tablename__ = "claim_events"

    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="done")  # done|current|upcoming|blocked
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    claim: Mapped[Claim] = relationship(back_populates="events")


class ClaimPhoto(IdMixin, TimestampMixin, Base):
    __tablename__ = "claim_photos"

    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(255))
    observations: Mapped[dict] = mapped_column(JSON, default=dict)
