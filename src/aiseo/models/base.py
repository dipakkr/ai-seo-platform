"""Database engine and session setup."""

from sqlmodel import Session, SQLModel, create_engine

from aiseo.config import get_settings

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
    SQLModel.metadata.create_all(get_engine())


def get_session():
    """Yield a database session."""
    with Session(get_engine()) as session:
        yield session
