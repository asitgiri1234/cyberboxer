"""
app.models.customer
-------------------
Customer ORM model.

A customer is the top of the ownership hierarchy:

    Customer 1 --- * Policy 1 --- * Claim

Uses SQLAlchemy 2.x typed declarative style (`Mapped` / `mapped_column`).
`customer_id` is the unique *business* identifier (e.g. "C001") used to link
records across the datasets, distinct from the surrogate integer `id`.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    # Imported only for type checking to avoid a circular import at runtime;
    # the relationship itself is resolved lazily via the string class name.
    from app.models.policy import Policy


class Customer(Base, TimestampMixin):
    """A policyholder who can own one or more policies."""

    __tablename__ = "customers"

    # Surrogate primary key.
    id: Mapped[int] = mapped_column(primary_key=True)

    # Unique business identifier used to reference this customer elsewhere.
    customer_id: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )

    # Core identity (required).
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Optional demographic / contact details.
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)

    # One-to-many: a customer owns many policies. Deleting a customer cascades
    # to their policies (and, transitively, those policies' claims).
    policies: Mapped[list["Policy"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # Helpful for logs / debugging.
        return f"<Customer id={self.id} customer_id={self.customer_id!r}>"
