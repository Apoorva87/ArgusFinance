"""Migrations own the operational schema for every local entry point."""

from collections.abc import Callable
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from argusfinance.bootstrap import build_container
from argusfinance.config import Settings

_HEAD_REVISION = "0001_snapshot_metadata"


def _stamped_revisions(database_url: str) -> list[str]:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        return [
            row[0] for row in connection.execute(text("SELECT version_num FROM alembic_version"))
        ]


def test_alembic_upgrade_succeeds_after_the_application_container_is_built(
    tmp_path: Path, apply_migrations: Callable[[str], None]
) -> None:
    """Building the container must not create schema Alembic then collides with."""
    database_url = f"sqlite:///{tmp_path / 'workspace.sqlite'}"
    settings = Settings(state_dir=tmp_path / "state", database_url=database_url)

    build_container(settings)
    apply_migrations(database_url)

    assert _stamped_revisions(database_url) == [_HEAD_REVISION]


def test_migrations_create_the_metadata_table_the_repository_uses(
    tmp_path: Path, apply_migrations: Callable[[str], None]
) -> None:
    """Alembic alone is a sufficient schema owner for the application."""
    database_url = f"sqlite:///{tmp_path / 'workspace.sqlite'}"

    apply_migrations(database_url)

    assert "market_snapshot_metadata" in inspect(create_engine(database_url)).get_table_names()
