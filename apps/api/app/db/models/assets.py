from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, EncryptedString, IdMixin, TimestampMixin


class Asset(IdMixin, TimestampMixin, Base):
    """Anything insurable. Vehicle/Property hold type-specific attributes."""

    __tablename__ = "assets"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # vehicle | property | pet | person | business
    label: Mapped[str] = mapped_column(String(120))
    estimated_value: Mapped[float | None] = mapped_column(Numeric(12, 2))

    vehicle: Mapped["Vehicle | None"] = relationship(back_populates="asset", uselist=False)
    property: Mapped["Property | None"] = relationship(back_populates="asset", uselist=False)


class Vehicle(IdMixin, Base):
    __tablename__ = "vehicles"

    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), unique=True)
    year: Mapped[int]
    make: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(40))
    vin: Mapped[str | None] = mapped_column(EncryptedString)
    annual_mileage: Mapped[int | None]
    asset: Mapped[Asset] = relationship(back_populates="vehicle")


class Property(IdMixin, Base):
    __tablename__ = "properties"

    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), unique=True)
    address_line: Mapped[str] = mapped_column(EncryptedString)
    city: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(2))
    year_built: Mapped[int | None]
    square_feet: Mapped[int | None]
    estimated_rebuild_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    asset: Mapped[Asset] = relationship(back_populates="property")
