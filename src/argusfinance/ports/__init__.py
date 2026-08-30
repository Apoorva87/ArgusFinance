"""Ports that isolate application services from external systems."""

from argusfinance.ports.market_data import MarketDataProvider

__all__ = ["MarketDataProvider"]
