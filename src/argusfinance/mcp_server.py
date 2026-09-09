"""Local STDIO MCP tools backed by the shared market application service."""

from typing import cast
from uuid import UUID

from mcp.server.mcpserver import MCPServer

from argusfinance.bootstrap import build_container
from argusfinance.config import Settings
from argusfinance.domain.market import MarketSnapshot
from argusfinance.domain.strategy import StrategyDraft
from argusfinance.services.market import MarketService
from argusfinance.services.strategies import StrategyService


class MarketMcpTools:
    """JSON-safe market operations exposed at the MCP boundary."""

    def __init__(self, service: MarketService) -> None:
        self._service = service

    def capture_market_snapshot(self, ticker: str, weeks: int = 8) -> dict[str, object]:
        """Capture and persist one market snapshot."""
        return cast(
            dict[str, object],
            self._service.capture(ticker, weeks).model_dump(mode="json"),
        )

    def get_latest_market_snapshot(self, ticker: str) -> dict[str, object]:
        """Read the newest persisted market snapshot for a ticker."""
        return cast(dict[str, object], self._service.latest(ticker).model_dump(mode="json"))

    def import_market_snapshot(self, snapshot: dict[str, object]) -> dict[str, object]:
        """Validate and persist one normalized snapshot object."""
        normalized = MarketSnapshot.model_validate(snapshot)
        return cast(
            dict[str, object],
            self._service.import_snapshot(normalized).model_dump(mode="json"),
        )


class StrategyMcpTools:
    """JSON-safe strategy operations using the API/CLI service contract."""

    def __init__(self, service: StrategyService) -> None:
        self._service = service

    def evaluate_strategy(self, draft: dict[str, object]) -> dict[str, object]:
        return cast(dict[str, object], self._service.evaluate(StrategyDraft.model_validate(draft)).model_dump(mode="json"))

    def save_strategy(self, draft: dict[str, object]) -> dict[str, object]:
        return cast(dict[str, object], self._service.save(StrategyDraft.model_validate(draft)).model_dump(mode="json"))

    def list_strategies(self) -> list[dict[str, object]]:
        return [cast(dict[str, object], saved.model_dump(mode="json")) for saved in self._service.list()]

    def get_strategy(self, strategy_id: str) -> dict[str, object]:
        return cast(dict[str, object], self._service.get(UUID(strategy_id)).model_dump(mode="json"))


def build_mcp_server(
    service: MarketService, strategy_service: StrategyService | None = None
) -> MCPServer[object]:
    """Register market tools and additive strategy tools for a composed container."""
    server = MCPServer(name="ArgusFinance")
    tools = MarketMcpTools(service)

    @server.tool(name="capture_market_snapshot")
    def capture_market_snapshot(ticker: str, weeks: int = 8) -> dict[str, object]:
        return tools.capture_market_snapshot(ticker, weeks)

    @server.tool(name="get_latest_market_snapshot")
    def get_latest_market_snapshot(ticker: str) -> dict[str, object]:
        return tools.get_latest_market_snapshot(ticker)

    @server.tool(name="import_market_snapshot")
    def import_market_snapshot(snapshot: dict[str, object]) -> dict[str, object]:
        return tools.import_market_snapshot(snapshot)

    if strategy_service is not None:
        strategy_tools = StrategyMcpTools(strategy_service)

        @server.tool(name="evaluate_strategy")
        def evaluate_strategy(draft: dict[str, object]) -> dict[str, object]:
            return strategy_tools.evaluate_strategy(draft)

        @server.tool(name="save_strategy")
        def save_strategy(draft: dict[str, object]) -> dict[str, object]:
            return strategy_tools.save_strategy(draft)

        @server.tool(name="list_strategies")
        def list_strategies() -> list[dict[str, object]]:
            return strategy_tools.list_strategies()

        @server.tool(name="get_strategy")
        def get_strategy(strategy_id: str) -> dict[str, object]:
            return strategy_tools.get_strategy(strategy_id)

    return server


def main() -> None:
    """Start the local MCP server on a clean STDIO transport."""
    settings = Settings()
    container = build_container(settings)
    server = build_mcp_server(container.market_service, container.strategy_service)
    server.run(transport="stdio")
