from __future__ import annotations

from sqlalchemy import (
    String, Integer, Text, ForeignKey,
    UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Location(db.Model):
    __tablename__ = "locations"

    __table_args__ = (
        CheckConstraint(
            "type IN ('cabinet', 'shelf', 'drawer', 'slot')",
            name="ck_location_type"
        ),
        CheckConstraint(
            "parent_id IS NULL OR parent_id != id",
            name="ck_location_not_own_parent"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(150))

    type: Mapped[str] = mapped_column(String(20))

    position: Mapped[int] = mapped_column(
        Integer, default=0
    )

    description: Mapped[str | None] = mapped_column(
        Text
    )

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"),
        index=True
    )

    parent: Mapped[Location | None] = relationship(
        back_populates="children",
        remote_side=[id]
    )

    children: Mapped[list[Location]] = relationship(
        back_populates="parent",
        passive_deletes="all",
        order_by="Location.position"
    )

    placements: Mapped[list[Placement]] = relationship(
        back_populates="location",
        passive_deletes="all"
    )

class Medicine(db.Model):
    __tablename__ = "medicines"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(200), index=True
    )

    dosage: Mapped[str | None] = mapped_column(
        String(100)
    )

    form: Mapped[str | None] = mapped_column(
        String(100)
    )

    package_size: Mapped[str | None] = mapped_column(
        String(100)
    )

    barcode: Mapped[str | None] = mapped_column(
        String(64), index=True
    )

    placements: Mapped[list[Placement]] = relationship(
        back_populates="medicine",
        passive_deletes="all"
    )

class Placement(db.Model):
    __tablename__ = "placements"

    __table_args__ = (
        UniqueConstraint(
            "medicine_id",
            "location_id",
            name="uq_medicine_location"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    medicine_id: Mapped[int] = mapped_column(
        ForeignKey("medicines.id", ondelete="RESTRICT"),
        index=True
    )

    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"),
        index=True
    )

    medicine: Mapped[Medicine] = relationship(
        back_populates="placements"
    )

    location: Mapped[Location] = relationship(
        back_populates="placements"
    )