"""FastAPI dependencies backed by the application container."""

from typing import cast

from fastapi import Request

from argusfinance.services.market import MarketService
from argusfinance.services.strategies import StrategyService


def get_market_service(request: Request) -> MarketService:
    """Return the singleton market service composed for this application."""
    return cast(MarketService, request.app.state.container.market_service)


def get_strategy_service(request: Request) -> StrategyService:
    """Return the composed strategy workflow service."""
    return cast(StrategyService, request.app.state.container.strategy_service)
