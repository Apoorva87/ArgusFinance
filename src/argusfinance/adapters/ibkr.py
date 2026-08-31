"""Read-only Interactive Brokers connection diagnostics."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from argusfinance.domain.market import MarketSnapshot


class IbkrClient(Protocol):
    """The small portion of an ``ib_async.IB`` client used by diagnostics."""

    def connect(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        clientId: int = 1,
        timeout: float = 4,
        readonly: bool = False,
    ) -> bool: ...

    def isConnected(self) -> bool: ...

    def disconnect(self) -> str | None: ...


@dataclass(frozen=True)
class IbkrConnectionSettings:
    """Safe, local defaults for a diagnostic-only TWS/Gateway handshake."""

    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 17
    readonly: bool = True
    timeout: float = 4

    def __post_init__(self) -> None:
        if not self.readonly:
            raise ValueError("IBKR diagnostics must be read-only")


def _default_client_factory() -> IbkrClient:
    """Instantiate the official client only when a diagnostic is requested."""
    from ib_async import IB

    return IB()


class IbkrMarketDataProvider:
    """Expose only a read-only connectivity check for the foundation slice."""

    def __init__(
        self,
        settings: IbkrConnectionSettings | None = None,
        client_factory: Callable[[], IbkrClient] = _default_client_factory,
    ) -> None:
        self._settings = settings or IbkrConnectionSettings()
        self._client_factory = client_factory

    def diagnostic(self) -> dict[str, str | bool]:
        """Perform a connection handshake without fetching or changing IBKR data."""
        client = self._client_factory()
        result: dict[str, str | bool] = {"provider": "ibkr", "connected": False, "mode": "read-only"}
        try:
            client.connect(
                host=self._settings.host,
                port=self._settings.port,
                clientId=self._settings.client_id,
                timeout=self._settings.timeout,
                readonly=True,
            )
            if client.isConnected():
                result["connected"] = True
            else:
                result["error"] = "connection was not established"
        except Exception:  # noqa: BLE001 - client libraries use varied error types
            result["error"] = "connection failed"
        finally:
            client.disconnect()
        return result

    def get_snapshot(self, ticker: str, weeks: int = 8) -> MarketSnapshot:
        """Reject live retrieval until a later, explicitly scoped project phase."""
        raise NotImplementedError("IBKR snapshot retrieval is not part of the foundation slice")
