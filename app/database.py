"""
app.database
------------
SQLAlchemy 2.x database setup.

Responsibilities:
* Create the SQLAlchemy `Engine` from the configured `DATABASE_URL`.
* Provide a `SessionLocal` factory (the classic session-per-request pattern).
* Expose a declarative `Base` class that all ORM models will inherit from.
* Provide a `get_db` FastAPI dependency that yields a session and always
  closes it, even if the request raises.

Keeping all database wiring in one module means the rest of the codebase
depends on these few well-defined objects rather than on connection details.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# The Engine is the central source of database connectivity. It manages a
# pool of connections. `pool_pre_ping=True` transparently checks that a
# pooled connection is still alive before using it, avoiding "stale
# connection" errors after the DB restarts or times out an idle connection.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,  # Use SQLAlchemy 2.0-style behaviour explicitly.
)

# Session factory. Each call to `SessionLocal()` produces a new Session bound
# to the engine above. We disable autocommit/autoflush so the unit-of-work is
# explicit and predictable per request.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
    future=True,
)


class Base(DeclarativeBase):
    """Declarative base class.

    All ORM models (added in later phases) should subclass `Base`. Sharing a
    single base lets SQLAlchemy track metadata for every table in one place.
    """


def get_db():
    """FastAPI dependency that provides a scoped database session.

    Yields a session for the lifetime of a single request and guarantees it
    is closed afterwards. Usage:

        @router.get("/thing")
        def read_thing(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# NOTE: The database schema is managed with Alembic migrations, not
# `Base.metadata.create_all()`. Create/upgrade the schema with:
#     alembic upgrade head
# See the "Database Migrations" section of the README.
