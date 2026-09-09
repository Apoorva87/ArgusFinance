"""Command-line behavior for the local market workflow."""

import json
from pathlib import Path

from typer.testing import CliRunner

from argusfinance.cli import app


def _configure_local_state(monkeypatch, tmp_path, apply_migrations) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli.sqlite'}"
    monkeypatch.setenv("ARGUS_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("ARGUS_DATABASE_URL", database_url)
    apply_migrations(database_url)


def test_market_snapshot_prints_pretty_json(monkeypatch, tmp_path, apply_migrations):
    _configure_local_state(monkeypatch, tmp_path, apply_migrations)

    result = CliRunner().invoke(app, ["market", "snapshot", "NVDA", "--weeks", "8"])

    assert result.exit_code == 0
    assert result.stdout.startswith("{\n")
    snapshot = json.loads(result.stdout)
    assert snapshot["snapshot_id"]
    assert snapshot["underlying"]["ticker"] == "NVDA"


def test_market_latest_uses_the_persisted_local_snapshot(monkeypatch, tmp_path, apply_migrations):
    _configure_local_state(monkeypatch, tmp_path, apply_migrations)
    runner = CliRunner()

    captured = runner.invoke(app, ["market", "snapshot", "NVDA", "--weeks", "8"])
    latest = runner.invoke(app, ["market", "latest", "NVDA"])

    assert captured.exit_code == 0
    assert latest.exit_code == 0
    assert json.loads(latest.stdout)["snapshot_id"] == json.loads(captured.stdout)["snapshot_id"]


def test_market_snapshot_rejects_unsupported_ticker_concisely(monkeypatch, tmp_path, apply_migrations):
    _configure_local_state(monkeypatch, tmp_path, apply_migrations)

    result = CliRunner().invoke(app, ["market", "snapshot", "AAPL"])

    assert result.exit_code != 0
    assert "Mock provider supports only NVDA" in result.stderr
    assert "Traceback" not in result.stderr


def test_market_latest_reports_missing_snapshot_concisely(monkeypatch, tmp_path, apply_migrations):
    _configure_local_state(monkeypatch, tmp_path, apply_migrations)

    result = CliRunner().invoke(app, ["market", "latest", "NVDA"])

    assert result.exit_code != 0
    assert "No latest market snapshot found" in result.stderr
    assert "Traceback" not in result.stderr


def test_market_import_ibkr_normalizes_and_persists_raw_bundle(
    monkeypatch, tmp_path: Path, apply_migrations
) -> None:
    _configure_local_state(monkeypatch, tmp_path, apply_migrations)
    bundle_path = tmp_path / "nvda.json"
    bundle_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "ticker": "NVDA",
                "underlying": {
                    "response": {
                        "last": {"price": 226.06, "ts": 1788933498},
                        "top-status": {"status": "REALTIME"},
                    },
                    "retrieved_at": "2026-09-09T06:00:01Z",
                },
                "options": [
                    {
                        "expiration": "2026-09-18",
                        "strike": "225",
                        "option_type": "CALL",
                        "response": {
                            "bid-ask": {"bid": 5.55, "ask": 5.65},
                            "top-status": {"status": "FROZEN_DELAYED"},
                        },
                        "retrieved_at": "2026-09-09T06:00:02Z",
                    }
                ],
                "notes": ["One sampled contract."],
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()

    imported = runner.invoke(app, ["market", "import-ibkr", str(bundle_path)])
    latest = runner.invoke(app, ["market", "latest", "NVDA"])

    assert imported.exit_code == 0
    assert latest.exit_code == 0
    assert json.loads(latest.stdout) == json.loads(imported.stdout)
    assert json.loads(imported.stdout)["notes"][0] == "One sampled contract."


def test_market_import_ibkr_reports_invalid_input_without_traceback(
    monkeypatch, tmp_path: Path, apply_migrations
) -> None:
    _configure_local_state(monkeypatch, tmp_path, apply_migrations)
    path = tmp_path / "invalid.json"
    path.write_text("{}", encoding="utf-8")

    result = CliRunner().invoke(app, ["market", "import-ibkr", str(path)])

    assert result.exit_code != 0
    assert "schema_version" in result.stderr
    assert "Traceback" not in result.stderr


def test_provider_diagnostic_prints_json_from_the_ibkr_boundary(monkeypatch):
    class FakeIbkrProvider:
        def diagnostic(self) -> dict[str, str | bool]:
            return {"provider": "ibkr", "connected": True, "mode": "read-only"}

    monkeypatch.setattr("argusfinance.cli.IbkrMarketDataProvider", FakeIbkrProvider)

    result = CliRunner().invoke(app, ["provider", "diagnostic", "ibkr"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "provider": "ibkr",
        "connected": True,
        "mode": "read-only",
    }
