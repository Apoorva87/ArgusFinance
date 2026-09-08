"""HTTP contracts for deterministic strategy evaluation and saved records."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from argusfinance.api.app import create_app
from argusfinance.config import Settings


@pytest.fixture
def client(tmp_path: Path, apply_migrations: Callable[[str], None]) -> Iterator[TestClient]:
    database_url = f"sqlite:///{tmp_path / 'strategies.sqlite'}"
    apply_migrations(database_url)
    settings = Settings(state_dir=tmp_path / "snapshots", database_url=database_url)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def _draft(snapshot_id: str) -> dict[str, object]:
    return {
        "snapshot_id": snapshot_id,
        "name": "HTTP vertical",
        "status": "PAPER",
        "pricing": "NATURAL",
        "legs": [
            {"expiration": "2026-09-18", "strike": "175", "option_type": "CALL", "side": "BUY", "quantity": 1},
            {"expiration": "2026-09-18", "strike": "185", "option_type": "CALL", "side": "SELL", "quantity": 1},
        ],
    }


def test_evaluate_save_list_and_get_preserve_entry_evaluation(client: TestClient) -> None:
    """Breaking API-to-service persistence must fail the same-ID end-to-end workflow."""
    snapshot = client.post("/api/market/NVDA/snapshots?weeks=8").json()
    draft = _draft(snapshot["snapshot_id"])

    evaluation = client.post("/api/strategies/evaluate", json=draft)
    saved = client.post("/api/strategies", json=draft)
    listed = client.get("/api/strategies")
    reopened = client.get(f"/api/strategies/{saved.json()['id']}")

    assert evaluation.status_code == 200
    assert evaluation.json()["net_debit"] == "505"
    assert saved.status_code == 201
    assert listed.json()[0]["id"] == saved.json()["id"]
    assert reopened.json()["evaluation"] == saved.json()["evaluation"]


def test_get_missing_strategy_returns_not_found(client: TestClient) -> None:
    """An absent saved ID must not produce an empty numerical preview."""
    response = client.get("/api/strategies/00000000-0000-0000-0000-000000000099")

    assert response.status_code == 404
    assert response.json() == {"detail": "Saved strategy was not found"}


@pytest.mark.parametrize("change", [
    {"legs": []}, {"fee_per_contract": "-1"}, {"fee_per_contract": "NaN"},
    {"fee_per_contract": "Infinity"}, {"name": "   "},
    {"boundaries": [{"kind": "PRICE_BELOW", "value": "NaN", "note": "Review"}]},
])
def test_invalid_drafts_return_validation_errors(client: TestClient, change) -> None:
    snapshot = client.post("/api/market/NVDA/snapshots?weeks=8").json()
    draft = {**_draft(snapshot["snapshot_id"]), **change}
    assert client.post("/api/strategies/evaluate", json=draft).status_code == 422
    assert client.post("/api/strategies", json=draft).status_code == 422
    assert client.get("/api/strategies").json() == []


def test_absent_snapshot_returns_not_found(client: TestClient) -> None:
    draft = _draft("00000000-0000-0000-0000-000000000099")
    assert client.post("/api/strategies/evaluate", json=draft).status_code == 404


@pytest.mark.parametrize("mutation", ["mixed", "duplicate", "offsetting"])
def test_invalid_contract_combinations_return_validation_errors(client: TestClient, mutation) -> None:
    snapshot = client.post("/api/market/NVDA/snapshots?weeks=8").json()
    draft = _draft(snapshot["snapshot_id"])
    if mutation == "mixed":
        draft["legs"][1]["expiration"] = "2026-09-25"
    else:
        draft["legs"][1] = {**draft["legs"][0], "side": "SELL" if mutation == "offsetting" else "BUY"}
    assert client.post("/api/strategies/evaluate", json=draft).status_code == 422
