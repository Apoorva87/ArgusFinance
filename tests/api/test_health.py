from fastapi.testclient import TestClient

from argusfinance.api.app import create_app
from argusfinance.config import Settings


def test_health_reports_local_service_identity(tmp_path):
    settings = Settings(
        state_dir=tmp_path,
        database_url=f"sqlite:///{tmp_path / 'workspace.sqlite'}",
    )
    response = TestClient(create_app(settings)).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "argusfinance",
        "status": "ok",
        "mode": "local",
    }
