from datetime import date

from sqlalchemy import JSON, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, EmbeddingVector, IdMixin, TimestampMixin


class Document(IdMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("policies.id", ondelete="SET NULL"), index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(80))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_key: Mapped[str | None] = mapped_column(String(255))
    doc_type: Mapped[str] = mapped_column(String(40), default="unknown")
    status: Mapped[str] = mapped_column(String(20), default="processing")  # processing|ready|failed
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text)
    extracted: Mapped[dict] = mapped_column(JSON, default=dict)
    classification_confidence: Mapped[str | None] = mapped_column(String(30))

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(IdMixin, Base):
    __tablename__ = "document_chunks"

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    policy_id: Mapped[str | None] = mapped_column(String(32), index=True)
    claim_id: Mapped[str | None] = mapped_column(String(32), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(160))
    page: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding: Mapped[list | None] = mapped_column(EmbeddingVector)

    document: Mapped[Document] = relationship(back_populates="chunks")


class Bill(IdMixin, TimestampMixin, Base):
    __tablename__ = "bills"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"))
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.id", ondelete="SET NULL"))
    service_description: Mapped[str] = mapped_column(String(200))
    service_date: Mapped[date] = mapped_column(Date)
    total_charge: Mapped[float] = mapped_column(Numeric(12, 2))
    amount_due: Mapped[float] = mapped_column(Numeric(12, 2))
    due_date: Mapped[date | None] = mapped_column(Date)
    line_items: Mapped[list] = mapped_column(JSON, default=list)


class EOB(IdMixin, TimestampMixin, Base):
    __tablename__ = "eobs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.id", ondelete="SET NULL"))
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"))
    service_date: Mapped[date] = mapped_column(Date)
    billed_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    allowed_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    plan_paid: Mapped[float] = mapped_column(Numeric(12, 2))
    deductible: Mapped[float] = mapped_column(Numeric(12, 2))
    coinsurance: Mapped[float] = mapped_column(Numeric(12, 2))
    copay: Mapped[float] = mapped_column(Numeric(12, 2))
    patient_responsibility: Mapped[float] = mapped_column(Numeric(12, 2))
    network_status: Mapped[str] = mapped_column(String(20))
    remark_codes: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
