"""Direct and registration tests for the local MCP market tools."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from argusfinance.adapters.mock_market import MockMarketDataProvider
from argusfinance.domain.market import MarketSnapshot
from argusfinance.mcp_server import MarketMcpTools, build_mcp_server, main


class RecordingMarketService:
    """Narrow service double that makes tool delegation observable."""

    def __init__(self, snapshot: MarketSnapshot) -> None:
        self.snapshot = snapshot
        self.capture_calls: list[tuple[str, int]] = []
        self.latest_calls: list[str] = []

    def capture(self, ticker: str, weeks: int = 8) -> MarketSnapshot:
        self.capture_calls.append((ticker, weeks))
        return self.snapshot

    def latest(self, ticker: str) -> MarketSnapshot:
        self.latest_calls.append(ticker)
        return self.snapshot


@pytest.fixture
def snapshot() -> MarketSnapshot:
    return MockMarketDataProvider().get_snapshot("NVDA")


def test_capture_market_snapshot_delegates_once_and_returns_json_compatible_data(
    snapshot: MarketSnapshot,
) -> None:
    service = RecordingMarketService(snapshot)

    result = MarketMcpTools(service).capture_market_snapshot("nvda", weeks=4)

    assert service.capture_calls == [("nvda", 4)]
    assert result["snapshot_id"] == str(snapshot.snapshot_id)
    assert result["underlying"]["ticker"] == "NVDA"
    assert json.loads(json.dumps(result)) == result


def test_get_latest_market_snapshot_delegates_once_and_preserves_capture_identity(
    snapshot: MarketSnapshot,
) -> None:
    service = RecordingMarketService(snapshot)
    tools = MarketMcpTools(service)

    captured = tools.capture_market_snapshot("NVDA")
    latest = tools.get_latest_market_snapshot("NVDA")

    assert service.capture_calls == [("NVDA", 8)]
    assert service.latest_calls == ["NVDA"]
    assert latest["snapshot_id"] == captured["snapshot_id"]


def test_capture_market_snapshot_propagates_service_error(snapshot: MarketSnapshot) -> None:
    class FailingMarketService(RecordingMarketService):
        def capture(self, ticker: str, weeks: int = 8) -> MarketSnapshot:
            raise ValueError("unsupported ticker")

    with pytest.raises(ValueError, match="unsupported ticker"):
        MarketMcpTools(FailingMarketService(snapshot)).capture_market_snapshot("AAPL")


def test_build_mcp_server_registers_only_public_market_tools(snapshot: MarketSnapshot) -> None:
    server = build_mcp_server(RecordingMarketService(snapshot))

    registered_tools = asyncio.run(server.list_tools())

    assert {tool.name for tool in registered_tools} == {
        "capture_market_snapshot",
        "get_latest_market_snapshot",
    }


def test_main_builds_fresh_service_and_starts_stdio(monkeypatch) -> None:
    class FakeSettings:
        pass

    class FakeServer:
        def __init__(self) -> None:
            self.transport: str | None = None

        def run(self, transport: str) -> None:
            self.transport = transport

    server = FakeServer()
    observed_settings: list[FakeSettings] = []
    service = object()

    def fake_build_container(settings: FakeSettings) -> SimpleNamespace:
        observed_settings.append(settings)
        return SimpleNamespace(market_service=service)

    def fake_build_mcp_server(received_service: object) -> FakeServer:
        assert received_service is service
        return server

    monkeypatch.setattr("argusfinance.mcp_server.Settings", FakeSettings)
    monkeypatch.setattr("argusfinance.mcp_server.build_container", fake_build_container)
    monkeypatch.setattr("argusfinance.mcp_server.build_mcp_server", fake_build_mcp_server)

    main()

    assert len(observed_settings) == 1
    assert server.transport == "stdio"
