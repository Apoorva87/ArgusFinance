"""Tests for the shared market snapshot application service."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

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


class BlockingFailingMetadataRepository(FailingMetadataRepository):
    """Pause after Parquet publication, then fail metadata persistence."""

    def __init__(self, entered: Event, release: Event) -> None:
        self._entered = entered
        self._release = release

    def add(self, metadata: object) -> None:
        self._entered.set()
        if not self._release.wait(timeout=5):
            raise TimeoutError("test did not release metadata failure")
        raise RuntimeError("metadata failed")


class SignalingMetadataRepository:
    """Signal when a second service has committed snapshot metadata."""

    def __init__(self, delegate: SnapshotMetadataRepository, added: Event) -> None:
        self._delegate = delegate
        self._added = added

    def add(self, metadata: SnapshotMetadata) -> None:
        self._delegate.add(metadata)
        self._added.set()

    def latest_for_ticker(self, ticker: str) -> SnapshotMetadata | None:
        return self._delegate.latest_for_ticker(ticker)


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


def test_capture_serializes_compensation_across_service_instances(
    snapshot_store: SnapshotStore,
    metadata_repository: SnapshotMetadataRepository,
) -> None:
    failed_add_entered = Event()
    release_failed_add = Event()
    successful_add = Event()
    failing_service = MarketService(
        MockMarketDataProvider(),
        SnapshotStore(snapshot_store.root),
        BlockingFailingMetadataRepository(failed_add_entered, release_failed_add),
    )
    successful_service = MarketService(
        MockMarketDataProvider(),
        SnapshotStore(snapshot_store.root),
        SignalingMetadataRepository(metadata_repository, successful_add),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        failed_capture = executor.submit(failing_service.capture, "NVDA")
        assert failed_add_entered.wait(timeout=2)
        successful_capture = executor.submit(successful_service.capture, "NVDA")
        assert not successful_add.wait(timeout=0.5)
        release_failed_add.set()

        with pytest.raises(RuntimeError, match="metadata failed"):
            failed_capture.result(timeout=5)
        captured = successful_capture.result(timeout=5)

    assert snapshot_store.read(captured.snapshot_id) == captured
    assert metadata_repository.get(str(captured.snapshot_id)) is not None


def test_repeated_capture_returns_persisted_snapshot_without_duplicate_metadata_error(
    snapshot_store: SnapshotStore, metadata_repository: SnapshotMetadataRepository
) -> None:
    provider = CountingProvider()
    service = MarketService(provider, snapshot_store, metadata_repository)

    first = service.capture("NVDA")
    parquet_path = snapshot_store.write(first)
    before = parquet_path.read_bytes()

    second = service.capture("NVDA")

    assert second == first
    assert provider.calls == 2
    assert parquet_path.read_bytes() == before
    assert metadata_repository.get(str(first.snapshot_id)) is not None
