"""Database engine and session setup."""

import logging

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from aiseo.config import get_settings

logger = logging.getLogger(__name__)

_engine = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        if settings.database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(settings.database_url, connect_args=connect_args)
    return _engine


def create_db_and_tables():
    """Create all tables in the database."""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _run_migrations(engine)


def _run_migrations(engine):
    """Apply lightweight schema migrations for new columns."""
    migrations = [
        ("scan_result", "brands_ranked_json", "TEXT DEFAULT '[]'"),
    ]
    inspector = inspect(engine)
    for table, column, col_type in migrations:
        if table not in inspector.get_table_names():
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        if column not in existing:
            logger.info("Migrating: adding %s.%s", table, column)
            with engine.begin() as conn:
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                )


def get_session():
    """Yield a database session."""
    with Session(get_engine()) as session:
        yield session
