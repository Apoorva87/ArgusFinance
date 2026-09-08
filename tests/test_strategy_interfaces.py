"""CLI boundary for the shared strategy service."""

import json

from typer.testing import CliRunner

from argusfinance.bootstrap import build_container
from argusfinance.cli import app
from argusfinance.config import Settings
from argusfinance.mcp_server import StrategyMcpTools


def test_cli_strategy_evaluate_save_list_and_get_share_saved_id(monkeypatch, tmp_path, apply_migrations) -> None:
    """If a CLI command bypasses the common strategy service, this saved-ID flow breaks."""
    database_url = f"sqlite:///{tmp_path / 'interfaces.sqlite'}"
    monkeypatch.setenv("ARGUS_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("ARGUS_DATABASE_URL", database_url)
    apply_migrations(database_url)
    runner = CliRunner()
    snapshot = json.loads(runner.invoke(app, ["market", "snapshot", "NVDA"]).stdout)
    draft_path = tmp_path / "draft.json"
    draft_path.write_text(json.dumps({
        "snapshot_id": snapshot["snapshot_id"], "name": "CLI vertical", "status": "PAPER", "pricing": "NATURAL",
        "legs": [
            {"expiration": "2026-09-18", "strike": "175", "option_type": "CALL", "side": "BUY", "quantity": 1},
            {"expiration": "2026-09-18", "strike": "185", "option_type": "CALL", "side": "SELL", "quantity": 1},
        ],
    }))

    evaluated = runner.invoke(app, ["strategy", "evaluate", str(draft_path)])
    saved = runner.invoke(app, ["strategy", "save", str(draft_path)])
    saved_id = json.loads(saved.stdout)["id"]
    listed = runner.invoke(app, ["strategy", "list"])
    reopened = runner.invoke(app, ["strategy", "get", saved_id])

    assert evaluated.exit_code == 0
    assert json.loads(evaluated.stdout)["net_debit"] == "505"
    assert saved.exit_code == listed.exit_code == reopened.exit_code == 0
    assert json.loads(listed.stdout)[0]["id"] == saved_id == json.loads(reopened.stdout)["id"]

    tools = StrategyMcpTools(build_container(Settings()).strategy_service)
    assert tools.get_strategy(saved_id) == json.loads(reopened.stdout)
    assert tools.list_strategies()[0]["id"] == saved_id
