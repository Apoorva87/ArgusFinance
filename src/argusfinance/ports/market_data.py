"""Market-data provider boundary."""

from typing import Protocol

from argusfinance.domain.market import MarketSnapshot


class MarketDataProvider(Protocol):
    """Provides normalized market snapshots without leaking provider objects."""

    def get_snapshot(self, ticker: str, weeks: int = 8) -> MarketSnapshot: ...

    def diagnostic(self) -> dict[str, str | bool]: ...
