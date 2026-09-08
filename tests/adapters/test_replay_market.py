"""Tests for the deterministic path-injected replay provider."""

import json
from pathlib import Path

import pytest

from argusfinance.adapters.replay_market import ReplayMarketDataProvider


def test_replay_provider_loads_normalized_snapshot_from_injected_json_path(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "snapshot.json"
    fixture.write_text(
        json.dumps(
            {
                "snapshot_id": "00000000-0000-0000-0000-000000000010",
                "underlying": {
                    "ticker": "nvda",
                    "price": "180.25",
                    "source": "replay-file",
                    "source_timestamp": "2026-08-28T20:00:00Z",
                    "retrieved_at": "2026-08-28T20:00:00Z",
                    "status": "FROZEN",
                },
                "options": [
                    {
                        "ticker": "nvda",
                        "expiration": "2026-09-18",
                        "strike": "175",
                        "option_type": "CALL",
                        "bid": "8.60",
                        "ask": "8.80",
                        "volume": 1,
                        "open_interest": 2,
                        "implied_volatility": "0.44",
                        "delta": None,
                        "gamma": None,
                        "theta": None,
                        "vega": None,
                        "source": "replay-file",
                        "source_timestamp": "2026-08-28T20:00:00Z",
                        "retrieved_at": "2026-08-28T20:00:00Z",
                        "status": "UNAVAILABLE",
                    }
                ],
                "created_at": "2026-08-28T20:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    provider = ReplayMarketDataProvider(fixture)
    first = provider.get_snapshot(" NVDA ", weeks=8)
    second = provider.get_snapshot("NVDA", weeks=8)

    assert first == second
    assert first.underlying.ticker == "NVDA"
    assert first.options[0].delta is None
    assert provider.diagnostic() == {
        "provider": "replay",
        "connected": False,
        "mode": "deterministic",
        "path": str(fixture.resolve()),
    }


def test_replay_provider_rejects_ticker_and_horizon_mismatch(tmp_path: Path) -> None:
    fixture = tmp_path / "snapshot.json"
    fixture.write_text(
        json.dumps(
            {
                "snapshot_id": "00000000-0000-0000-0000-000000000010",
                "underlying": {
                    "ticker": "NVDA",
                    "price": "180.25",
                    "source": "replay",
                    "source_timestamp": "2026-08-28T20:00:00Z",
                    "retrieved_at": "2026-08-28T20:00:00Z",
                    "status": "FROZEN",
                },
                "options": [],
                "created_at": "2026-08-28T20:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    provider = ReplayMarketDataProvider(fixture)

    with pytest.raises(ValueError, match="ticker NVDA"):
        provider.get_snapshot("AAPL")
    with pytest.raises(ValueError, match="weeks=8"):
        provider.get_snapshot("NVDA", weeks=4)


def test_replay_provider_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="fixture path"):
        ReplayMarketDataProvider(tmp_path / "missing.json").get_snapshot("NVDA")
