"""FastAPI dependencies backed by the application container."""

from typing import cast

from fastapi import Request

from argusfinance.services.market import MarketService


def get_market_service(request: Request) -> MarketService:
    """Return the singleton market service composed for this application."""
    return cast(MarketService, request.app.state.container.market_service)
