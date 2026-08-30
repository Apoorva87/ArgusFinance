"""Concrete local application composition root."""

from dataclasses import dataclass

from argusfinance.adapters.mock_market import MockMarketDataProvider
from argusfinance.config import Settings
from argusfinance.services.market import MarketService
from argusfinance.storage.database import create_session_factory
from argusfinance.storage.models import Base
from argusfinance.storage.repositories import SnapshotMetadataRepository
from argusfinance.storage.snapshots import SnapshotStore


@dataclass(frozen=True)
class Container:
    """Long-lived application dependencies."""

    market_service: MarketService


def build_container(settings: Settings) -> Container:
    """Build the local storage and deterministic market workflow once."""
    session_factory, engine = create_session_factory(settings.database_url)
    Base.metadata.create_all(engine)
    return Container(
        market_service=MarketService(
            MockMarketDataProvider(),
            SnapshotStore(settings.state_dir),
            SnapshotMetadataRepository(session_factory),
        )
    )
