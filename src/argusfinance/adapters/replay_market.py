"""Deterministic, offline market-data replay from an injected JSON file."""

import json
from pathlib import Path
from typing import Any

from argusfinance.domain.market import MarketSnapshot


class ReplayMarketDataProvider:
    """Load a normalized market snapshot from a local JSON replay file.

    The file is read for each request so callers can inject a fixture path
    without relying on package resources, network access, or broker state.
    Replay files represent the supported eight-week horizon explicitly through
    this provider's contract (the snapshot itself remains provider-neutral).
    """

    _SUPPORTED_WEEKS = 8

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path).expanduser().resolve()

    def get_snapshot(self, ticker: str, weeks: int = _SUPPORTED_WEEKS) -> MarketSnapshot:
        """Read, validate, and normalize one immutable replay snapshot."""
        normalized_ticker = ticker.strip().upper()
        if not normalized_ticker:
            raise ValueError("ticker must not be blank")
        if isinstance(weeks, bool) or not isinstance(weeks, int) or weeks != self._SUPPORTED_WEEKS:
            raise ValueError("Replay provider supports only weeks=8")
        if not self.path.is_file():
            raise ValueError(f"replay fixture path does not exist: {self.path}")
        try:
            payload: Any = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"unable to read replay fixture path: {self.path}") from error
        try:
            snapshot = MarketSnapshot.model_validate(payload)
        except (TypeError, ValueError) as error:
            raise ValueError(f"replay fixture is not a valid market snapshot: {self.path}") from error
        if snapshot.underlying.ticker != normalized_ticker:
            raise ValueError(
                f"replay fixture ticker {snapshot.underlying.ticker} does not match requested ticker {normalized_ticker}"
            )
        return snapshot

    def diagnostic(self) -> dict[str, str | bool]:
        """Report that this provider is deterministic and entirely offline."""
        return {
            "provider": "replay",
            "connected": False,
            "mode": "deterministic",
            "path": str(self.path),
        }
