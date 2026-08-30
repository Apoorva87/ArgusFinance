"""Deterministic, local-only market-data provider for the NVDA first slice."""

import json
from importlib.resources import files
from typing import Any

from argusfinance.domain.market import MarketSnapshot


class MockMarketDataProvider:
    """Loads the fixed packaged NVDA snapshot without network or clock access."""

    _SUPPORTED_TICKER = "NVDA"
    _SUPPORTED_WEEKS = 8

    def get_snapshot(self, ticker: str, weeks: int = _SUPPORTED_WEEKS) -> MarketSnapshot:
        if ticker.strip().upper() != self._SUPPORTED_TICKER:
            raise ValueError("Mock provider supports only NVDA")
        if weeks != self._SUPPORTED_WEEKS:
            raise ValueError("Mock provider supports only weeks=8")

        fixture = files("argusfinance.adapters.fixtures").joinpath("nvda_snapshot.json")
        payload: Any = json.loads(fixture.read_text(encoding="utf-8"))
        return MarketSnapshot.model_validate(payload)

    def diagnostic(self) -> dict[str, str | bool]:
        return {"provider": "mock", "connected": True, "mode": "deterministic"}
