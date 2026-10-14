from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, EncryptedString, IdMixin, TimestampMixin, utcnow


class Household(IdMixin, TimestampMixin, Base):
    __tablename__ = "households"

    name: Mapped[str] = mapped_column(String(120))
    address_city: Mapped[str | None] = mapped_column(String(80))
    address_state: Mapped[str | None] = mapped_column(String(2))
    members: Mapped[list["User"]] = relationship(back_populates="household")


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    preferred_name: Mapped[str | None] = mapped_column(String(60))
    roles: Mapped[list] = mapped_column(JSON, default=lambda: ["customer"])
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id"))
    date_of_birth: Mapped[str | None] = mapped_column(EncryptedString)
    phone: Mapped[str | None] = mapped_column(EncryptedString)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    household: Mapped[Household | None] = relationship(back_populates="members")


class Dependent(IdMixin, TimestampMixin, Base):
    __tablename__ = "dependents"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    relationship_type: Mapped[str] = mapped_column(String(30))
    birth_year: Mapped[int | None]


class Consent(IdMixin, TimestampMixin, Base):
    __tablename__ = "consents"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scope: Mapped[str] = mapped_column(String(60))  # e.g. "health_data.ai_analysis"
    purpose: Mapped[str] = mapped_column(Text)
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Integration(IdMixin, TimestampMixin, Base):
    __tablename__ = "integrations"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(30))  # carrier | health_payer | email | storage
    status: Mapped[str] = mapped_column(String(20), default="connected")
    data_shared: Mapped[list] = mapped_column(JSON, default=list)
    connected_on: Mapped[date | None] = mapped_column(Date)


class AuditLog(IdMixin, Base):
    __tablename__ = "audit_logs"

    user_id: Mapped[str | None] = mapped_column(String(32), index=True)
    actor: Mapped[str] = mapped_column(String(40))  # user | ai | system
    action: Mapped[str] = mapped_column(String(80))
    resource_type: Mapped[str | None] = mapped_column(String(40))
    resource_id: Mapped[str | None] = mapped_column(String(32))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
