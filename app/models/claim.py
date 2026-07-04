"""
app.models.claim
---------------
Claim ORM model.

A claim is filed against exactly one policy; a policy can have many claims:

    Customer 1 --- * Policy 1 --- * Claim

The foreign key `policy_id` references the policy's unique *business*
identifier (`policies.policy_id`). `fraud_flag` is a Boolean, monetary amounts
use `Numeric`/`Decimal`, and dates use `Date`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.policy import Policy


class Claim(Base, TimestampMixin):
    """A claim filed against a policy."""

    __tablename__ = "claims"

    # Surrogate primary key.
    id: Mapped[int] = mapped_column(primary_key=True)

    # Unique business identifier (e.g. "CL001").
    claim_id: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )

    # Foreign key to the policy this claim belongs to.
    policy_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("policies.policy_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Claim attributes.
    cause: Mapped[str | None] = mapped_column(String(255), nullable=True)
    loss_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    claim_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    loss_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    payout_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Fraud indicator; defaults to False so it is always a definite boolean.
    fraud_flag: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Many-to-one: the policy this claim was filed against.
    policy: Mapped["Policy"] = relationship(back_populates="claims")

    def __repr__(self) -> str:
        return f"<Claim id={self.id} claim_id={self.claim_id!r}>"
