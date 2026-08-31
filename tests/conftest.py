"""Shared test setup: Alembic owns the operational schema."""

from collections.abc import Callable
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _upgrade_to_head(database_url: str) -> None:
    """Apply the documented local setup step against one database URL."""
    config = Config(str(_REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


@pytest.fixture
def apply_migrations() -> Callable[[str], None]:
    """Provision a test database the same way `make migrate` provisions a local one."""
    return _upgrade_to_head
