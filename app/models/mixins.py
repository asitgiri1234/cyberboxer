"""
app.models.mixins
-----------------
Reusable model mixins shared across all ORM models.

`TimestampMixin` provides the `created_at` / `updated_at` columns so every
table gets consistent, database-populated audit timestamps without repeating
the same column definitions in each model (DRY).
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds automatically managed `created_at` and `updated_at` columns.

    * `created_at` is set once, on INSERT, via the database `now()` default.
    * `updated_at` is set on INSERT and refreshed on every UPDATE via
      `onupdate`, so it always reflects the last modification time.

    Timezone-aware timestamps (`DateTime(timezone=True)`) are used to avoid
    ambiguity across environments.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
