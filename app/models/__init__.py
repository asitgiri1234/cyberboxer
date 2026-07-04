"""
app.models package
------------------
Aggregates all ORM models and re-exports them for convenient importing:

    from app.models import Customer, Policy, Claim

Importing this package also has an important side effect: it imports every
model module, which registers each table on `Base.metadata`. Alembic's
`env.py` relies on this so that autogeneration sees the full schema.
"""

from app.models.claim import Claim
from app.models.customer import Customer
from app.models.policy import Policy

# Explicit public API of this package.
__all__ = ["Customer", "Policy", "Claim"]
