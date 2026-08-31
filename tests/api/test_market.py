"""HTTP contract tests for the shared market snapshot workflow."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from argusfinance.api.app import create_app
from argusfinance.config import Settings


@pytest.fixture
def client(tmp_path: Path, apply_migrations: Callable[[str], None]) -> Iterator[TestClient]:
    database_url = f"sqlite:///{tmp_path / 'metadata.sqlite'}"
    apply_migrations(database_url)
    settings = Settings(
        state_dir=tmp_path / "snapshots",
        database_url=database_url,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_capture_and_latest_return_the_same_persisted_snapshot(client: TestClient) -> None:
    captured = client.post("/api/market/NVDA/snapshots?weeks=8")
    latest = client.get("/api/market/NVDA/latest")

    assert captured.status_code == 201
    assert latest.status_code == 200
    assert latest.json() == captured.json()
    assert captured.json()["underlying"]["ticker"] == "NVDA"


def test_unsupported_mock_ticker_returns_provider_message(client: TestClient) -> None:
    response = client.post("/api/market/AAPL/snapshots?weeks=8")

    assert response.status_code == 422
    assert response.json() == {"detail": "Mock provider supports only NVDA"}


def test_latest_without_snapshot_returns_stable_not_found_detail(client: TestClient) -> None:
    response = client.get("/api/market/NVDA/latest")

    assert response.status_code == 404
    assert response.json() == {"detail": "No latest market snapshot found"}


def test_health_response_remains_unchanged(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "argusfinance",
        "status": "ok",
        "mode": "local",
    }
