"""Local STDIO MCP tools backed by the shared market application service."""

from typing import cast

from mcp.server.mcpserver import MCPServer

from argusfinance.bootstrap import build_container
from argusfinance.config import Settings
from argusfinance.services.market import MarketService


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


def build_mcp_server(service: MarketService) -> MCPServer[object]:
    """Register the local market service as the two public MCP tools."""
    server = MCPServer(name="ArgusFinance")
    tools = MarketMcpTools(service)

    @server.tool(name="capture_market_snapshot")
    def capture_market_snapshot(ticker: str, weeks: int = 8) -> dict[str, object]:
        return tools.capture_market_snapshot(ticker, weeks)

    @server.tool(name="get_latest_market_snapshot")
    def get_latest_market_snapshot(ticker: str) -> dict[str, object]:
        return tools.get_latest_market_snapshot(ticker)

    return server


def main() -> None:
    """Start the local MCP server on a clean STDIO transport."""
    settings = Settings()
    server = build_mcp_server(build_container(settings).market_service)
    server.run(transport="stdio")
