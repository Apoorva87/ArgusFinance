"""HTTP contract tests for the shared market snapshot workflow."""

from collections.abc import Callable, Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from argusfinance.adapters.mock_market import MockMarketDataProvider
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


def test_import_and_latest_return_the_same_normalized_snapshot(client: TestClient) -> None:
    snapshot = MockMarketDataProvider().get_snapshot("NVDA").model_copy(
        update={"notes": ("Imported connector evidence.",)}
    )

    imported = client.post("/api/market/import", json=snapshot.model_dump(mode="json"))
    latest = client.get("/api/market/NVDA/latest")

    assert imported.status_code == 201
    assert latest.status_code == 200
    assert imported.json() == latest.json()
    assert imported.json()["notes"] == ["Imported connector evidence."]


def test_import_conflict_returns_explicit_input_error_and_preserves_first(
    client: TestClient,
) -> None:
    snapshot = MockMarketDataProvider().get_snapshot("NVDA")
    first = client.post("/api/market/import", json=snapshot.model_dump(mode="json"))
    conflicting = snapshot.model_copy(
        update={
            "underlying": snapshot.underlying.model_copy(
                update={"price": Decimal("999.00")}
            )
        }
    )

    conflict = client.post(
        "/api/market/import", json=conflicting.model_dump(mode="json")
    )
    latest = client.get("/api/market/NVDA/latest")

    assert first.status_code == 201
    assert conflict.status_code == 422
    assert "immutable" in conflict.json()["detail"]
    assert latest.json() == first.json()


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
