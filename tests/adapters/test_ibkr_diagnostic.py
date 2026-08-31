"""Tests for the narrowly read-only IBKR connection diagnostic."""

import pytest

from argusfinance.adapters.ibkr import IbkrConnectionSettings, IbkrMarketDataProvider


class FakeIbClient:
    def __init__(self, *, connect_result: bool = True, connect_error: Exception | None = None):
        self.connect_result = connect_result
        self.connect_error = connect_error
        self.connect_calls: list[dict[str, object]] = []
        self.disconnect_calls = 0

    def connect(self, **kwargs: object) -> bool:
        self.connect_calls.append(kwargs)
        if self.connect_error is not None:
            raise self.connect_error
        return self.connect_result

    def isConnected(self) -> bool:
        return self.connect_result

    def disconnect(self) -> None:
        self.disconnect_calls += 1

    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"diagnostic must not call IBKR {name}")


def test_diagnostic_uses_one_readonly_connection_and_always_disconnects():
    client = FakeIbClient()
    settings = IbkrConnectionSettings(timeout=4)
    provider = IbkrMarketDataProvider(settings, client_factory=lambda: client)

    result = provider.diagnostic()

    assert result == {"provider": "ibkr", "connected": True, "mode": "read-only"}
    assert client.connect_calls == [
        {
            "host": "127.0.0.1",
            "port": 7497,
            "clientId": 17,
            "timeout": 4,
            "readonly": True,
        }
    ]
    assert client.disconnect_calls == 1


def test_connection_settings_reject_non_readonly_configuration():
    with pytest.raises(ValueError, match="^IBKR diagnostics must be read-only$"):
        IbkrConnectionSettings(readonly=False)


def test_diagnostic_reports_a_failed_handshake_and_disconnects():
    client = FakeIbClient(connect_result=False)
    provider = IbkrMarketDataProvider(client_factory=lambda: client)

    result = provider.diagnostic()

    assert result == {
        "provider": "ibkr",
        "connected": False,
        "mode": "read-only",
        "error": "connection was not established",
    }
    assert client.disconnect_calls == 1


def test_diagnostic_reports_a_connection_exception_and_disconnects():
    client = FakeIbClient(connect_error=RuntimeError("gateway unavailable"))
    provider = IbkrMarketDataProvider(client_factory=lambda: client)

    result = provider.diagnostic()

    assert result == {
        "provider": "ibkr",
        "connected": False,
        "mode": "read-only",
        "error": "connection failed",
    }
    assert client.disconnect_calls == 1


def test_get_snapshot_is_explicitly_out_of_scope():
    provider = IbkrMarketDataProvider(client_factory=FakeIbClient)

    with pytest.raises(
        NotImplementedError,
        match="^IBKR snapshot retrieval is not part of the foundation slice$",
    ):
        provider.get_snapshot("NVDA")
