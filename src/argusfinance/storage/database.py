"""SQLAlchemy session construction for local SQLite metadata."""

from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(database_url: str) -> tuple[sessionmaker[Session], Engine]:
    """Create short-lived sessions and an engine for the supplied database URL."""
    ensure_sqlite_file_parent(database_url)
    engine = create_engine(database_url)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return sessionmaker(bind=engine), engine


def ensure_sqlite_file_parent(database_url: str) -> None:
    """Create the parent directory for a file-backed SQLite database URL."""
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        return
    if url.database is None or url.database == ":memory:":
        return
    Path(url.database).parent.mkdir(parents=True, exist_ok=True)
