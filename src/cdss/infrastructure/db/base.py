"""Declarative base.

This holds the shared SQLAlchemy metadata that Alembic targets. No ORM models
are defined yet; future models will subclass ``Base`` so their tables register
on ``Base.metadata`` and become visible to Alembic autogenerate.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
