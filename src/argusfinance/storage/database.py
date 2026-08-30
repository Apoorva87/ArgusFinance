"""SQLAlchemy session construction for local SQLite metadata."""

from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(database_url: str) -> tuple[sessionmaker[Session], Engine]:
    """Create short-lived sessions and an engine for the supplied database URL."""
    engine = create_engine(database_url)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return sessionmaker(bind=engine), engine
