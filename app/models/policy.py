"""
app.models.policy
----------------
Policy ORM model.

A policy belongs to exactly one customer and can accumulate many claims:

    Customer 1 --- * Policy 1 --- * Claim

The foreign key `customer_id` references the customer's unique *business*
identifier (`customers.customer_id`), matching how the source datasets link
records. Money fields use `Numeric` (maps to Python `Decimal`) to avoid the
rounding errors of floating point.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.claim import Claim
    from app.models.customer import Customer


class Policy(Base, TimestampMixin):
    """An insurance policy owned by a customer."""

    __tablename__ = "policies"

    # Surrogate primary key.
    id: Mapped[int] = mapped_column(primary_key=True)

    # Unique business identifier (e.g. "P1001").
    policy_id: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )

    # Foreign key to the owning customer's business id.
    customer_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("customers.customer_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Policy attributes.
    policy_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    coverage_limit: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    premium_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Many-to-one: the customer that owns this policy.
    customer: Mapped["Customer"] = relationship(back_populates="policies")

    # One-to-many: claims filed against this policy.
    claims: Mapped[list["Claim"]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Policy id={self.id} policy_id={self.policy_id!r}>"
