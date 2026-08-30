"""Tests for the shared market snapshot application service."""

from pathlib import Path

import pytest

from argusfinance.adapters.mock_market import MockMarketDataProvider
from argusfinance.services.market import LatestSnapshotNotFoundError, MarketService
from argusfinance.storage.database import create_session_factory
from argusfinance.storage.models import Base
from argusfinance.storage.repositories import (
    SnapshotMetadata,
    SnapshotMetadataRepository,
)
from argusfinance.storage.snapshots import SnapshotStore


class CountingProvider:
    """Record provider use while delegating to the deterministic fixture."""

    def __init__(self) -> None:
        self.calls = 0
        self._provider = MockMarketDataProvider()

    def get_snapshot(self, ticker: str, weeks: int = 8):  # type: ignore[no-untyped-def]
        self.calls += 1
        return self._provider.get_snapshot(ticker, weeks)

    def diagnostic(self) -> dict[str, str | bool]:
        return self._provider.diagnostic()


class FailingMetadataRepository:
    """Fail metadata persistence after Parquet has been written."""

    def add(self, metadata: object) -> None:
        raise RuntimeError("metadata failed")

    def latest_for_ticker(self, ticker: str) -> None:
        return None


@pytest.fixture
def snapshot_store(tmp_path: Path) -> SnapshotStore:
    return SnapshotStore(tmp_path / "snapshots")


@pytest.fixture
def metadata_repository(tmp_path: Path) -> SnapshotMetadataRepository:
    factory, engine = create_session_factory(f"sqlite:///{tmp_path / 'metadata.sqlite'}")
    Base.metadata.create_all(engine)
    return SnapshotMetadataRepository(factory)


def test_capture_persists_snapshot_metadata_and_latest_identity(
    snapshot_store: SnapshotStore, metadata_repository: SnapshotMetadataRepository
) -> None:
    provider = CountingProvider()
    service = MarketService(provider, snapshot_store, metadata_repository)

    captured = service.capture("nvda", weeks=8)
    metadata = metadata_repository.get(str(captured.snapshot_id))

    assert provider.calls == 1
    assert metadata is not None
    assert metadata.ticker == "NVDA"
    assert metadata.parquet_path == str(
        snapshot_store.write(captured).relative_to(snapshot_store.root)
    )
    assert service.latest("NvDa") == captured


def test_latest_raises_clear_error_when_metadata_is_absent(
    snapshot_store: SnapshotStore, metadata_repository: SnapshotMetadataRepository
) -> None:
    service = MarketService(MockMarketDataProvider(), snapshot_store, metadata_repository)

    with pytest.raises(LatestSnapshotNotFoundError, match="No latest market snapshot"):
        service.latest("NVDA")


def test_latest_raises_clear_error_when_metadata_references_missing_file(
    snapshot_store: SnapshotStore, metadata_repository: SnapshotMetadataRepository
) -> None:
    snapshot = MockMarketDataProvider().get_snapshot("NVDA")
    metadata_repository.add(
        SnapshotMetadata(
            snapshot_id=str(snapshot.snapshot_id),
            ticker="NVDA",
            provider="mock",
            status="REALTIME",
            source_timestamp=snapshot.underlying.source_timestamp,
            retrieved_at=snapshot.underlying.retrieved_at,
            parquet_path="market/missing.parquet",
        )
    )
    service = MarketService(MockMarketDataProvider(), snapshot_store, metadata_repository)

    with pytest.raises(LatestSnapshotNotFoundError, match="No latest market snapshot"):
        service.latest("NVDA")


def test_capture_removes_new_parquet_file_when_metadata_persistence_fails(
    snapshot_store: SnapshotStore,
) -> None:
    service = MarketService(
        MockMarketDataProvider(), snapshot_store, FailingMetadataRepository()
    )

    with pytest.raises(RuntimeError, match="metadata failed"):
        service.capture("NVDA")

    assert list(snapshot_store.root.rglob("*.parquet")) == []


def test_capture_preserves_preexisting_parquet_when_metadata_persistence_fails(
    snapshot_store: SnapshotStore,
) -> None:
    snapshot = MockMarketDataProvider().get_snapshot("NVDA")
    preexisting_path = snapshot_store.write(snapshot)
    service = MarketService(
        MockMarketDataProvider(), snapshot_store, FailingMetadataRepository()
    )

    with pytest.raises(RuntimeError, match="metadata failed"):
        service.capture("NVDA")

    assert preexisting_path.exists()
    assert snapshot_store.read(snapshot.snapshot_id) == snapshot
