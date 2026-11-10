from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class TriageClaim(IdMixin, TimestampMixin, Base):
    """A synthetic first-notice-of-loss in the carrier-side triage queue (demo samples only)."""

    __tablename__ = "triage_claims"

    claim_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    claimant: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(160))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    expected_path: Mapped[str] = mapped_column(String(30))
    intake: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text)
