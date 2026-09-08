"""Migrations own the operational schema for every local entry point."""

from collections.abc import Callable
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from argusfinance.bootstrap import build_container
from argusfinance.config import Settings

_HEAD_REVISION = "0002_saved_strategies"


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
    tmp_path: Path, apply_migrations: Callable[[str | None], None]
) -> None:
    """Alembic alone is a sufficient schema owner for the application."""
    database_url = f"sqlite:///{tmp_path / 'workspace.sqlite'}"

    apply_migrations(database_url)

    assert {"market_snapshot_metadata", "saved_strategies", "strategy_events"} <= set(
        inspect(create_engine(database_url)).get_table_names()
    )


def test_migrations_use_database_url_from_dotenv(
    tmp_path: Path,
    monkeypatch,
    apply_migrations: Callable[[str | None], None],
) -> None:
    database_path = tmp_path / "dotenv.sqlite"
    database_url = f"sqlite:///{database_path}"
    (tmp_path / ".env").write_text(f"ARGUS_DATABASE_URL={database_url}\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ARGUS_DATABASE_URL", raising=False)

    apply_migrations(None)

    assert _stamped_revisions(database_url) == [_HEAD_REVISION]


def test_explicit_migration_url_overrides_dotenv(
    tmp_path: Path,
    monkeypatch,
    apply_migrations: Callable[[str | None], None],
) -> None:
    dotenv_path = tmp_path / "dotenv.sqlite"
    explicit_path = tmp_path / "explicit.sqlite"
    dotenv_url = f"sqlite:///{dotenv_path}"
    explicit_url = f"sqlite:///{explicit_path}"
    (tmp_path / ".env").write_text(f"ARGUS_DATABASE_URL={dotenv_url}\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ARGUS_DATABASE_URL", raising=False)

    apply_migrations(explicit_url)

    assert _stamped_revisions(explicit_url) == [_HEAD_REVISION]
    assert not dotenv_path.exists()
