"""Integration tests for SQLite snapshot metadata persistence."""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from argusfinance.storage.database import create_session_factory
from argusfinance.storage.models import Base
from argusfinance.storage.repositories import (
    DuplicateSnapshotError,
    SnapshotMetadata,
    SnapshotMetadataRepository,
)


@pytest.fixture
def repository(tmp_path: Path) -> SnapshotMetadataRepository:
    factory, engine = create_session_factory(f"sqlite:///{tmp_path / 'metadata.sqlite'}")
    Base.metadata.create_all(engine)
    return SnapshotMetadataRepository(factory)


def test_snapshot_metadata_round_trip(repository: SnapshotMetadataRepository) -> None:
    metadata = _metadata()

    repository.add(metadata)

    assert repository.get(metadata.snapshot_id) == metadata


def test_get_returns_none_for_unknown_snapshot_id(repository: SnapshotMetadataRepository) -> None:
    assert repository.get("00000000-0000-0000-0000-000000000099") is None


def test_latest_for_ticker_returns_none_when_no_metadata_exists(
    repository: SnapshotMetadataRepository,
) -> None:
    assert repository.latest_for_ticker("NVDA") is None


def test_latest_for_ticker_normalizes_lookup_and_breaks_timestamp_ties_by_id(
    repository: SnapshotMetadataRepository,
) -> None:
    retrieved_at = datetime(2026, 8, 28, 20, 0, tzinfo=UTC)
    first = _metadata(snapshot_id="00000000-0000-0000-0000-000000000001", retrieved_at=retrieved_at)
    tied_later_id = _metadata(
        snapshot_id="00000000-0000-0000-0000-000000000003",
        ticker="nvda",
        retrieved_at=retrieved_at,
    )
    older = _metadata(
        snapshot_id="00000000-0000-0000-0000-000000000002",
        retrieved_at=retrieved_at - timedelta(minutes=1),
    )

    repository.add(first)
    repository.add(tied_later_id)
    repository.add(older)

    latest = repository.latest_for_ticker("nVdA")
    assert latest is not None
    assert latest.snapshot_id == tied_later_id.snapshot_id
    assert latest.ticker == "NVDA"


def test_add_normalizes_ticker_for_storage(repository: SnapshotMetadataRepository) -> None:
    metadata = _metadata(ticker="nvda")

    repository.add(metadata)

    stored = repository.get(metadata.snapshot_id)
    assert stored is not None
    assert stored.ticker == "NVDA"


def test_add_rejects_naive_timestamps(repository: SnapshotMetadataRepository) -> None:
    naive = datetime.fromisoformat("2026-08-28T20:00:00")
    metadata = _metadata(source_timestamp=naive, retrieved_at=naive)

    with pytest.raises(ValueError, match="timezone-aware"):
        repository.add(metadata)

    assert repository.get(metadata.snapshot_id) is None


def test_add_canonicalizes_aware_timestamps_and_reattaches_utc_on_read(
    repository: SnapshotMetadataRepository,
) -> None:
    pacific = timezone(timedelta(hours=-7))
    metadata = _metadata(
        source_timestamp=datetime(2026, 8, 28, 13, 0, tzinfo=pacific),
        retrieved_at=datetime(2026, 8, 28, 13, 1, tzinfo=pacific),
    )

    repository.add(metadata)

    stored = repository.get(metadata.snapshot_id)
    assert stored is not None
    assert stored.source_timestamp == datetime(2026, 8, 28, 20, 0, tzinfo=UTC)
    assert stored.retrieved_at == datetime(2026, 8, 28, 20, 1, tzinfo=UTC)
    assert stored.source_timestamp.tzinfo is UTC
    assert stored.retrieved_at.tzinfo is UTC


def test_duplicate_snapshot_id_raises_domain_error_and_rolls_back(
    repository: SnapshotMetadataRepository,
) -> None:
    original = _metadata()
    duplicate = _metadata(ticker="AAPL")

    repository.add(original)

    with pytest.raises(DuplicateSnapshotError):
        repository.add(duplicate)

    assert repository.get(original.snapshot_id) == original
    assert repository.latest_for_ticker("AAPL") is None


def _metadata(
    *,
    snapshot_id: str = "00000000-0000-0000-0000-000000000001",
    ticker: str = "NVDA",
    source_timestamp: datetime | None = None,
    retrieved_at: datetime | None = None,
) -> SnapshotMetadata:
    source = source_timestamp or datetime(2026, 8, 28, 20, 0, tzinfo=UTC)
    retrieved = retrieved_at or datetime(2026, 8, 28, 20, 1, tzinfo=UTC)
    return SnapshotMetadata(
        snapshot_id=snapshot_id,
        ticker=ticker,
        provider="mock",
        status="REALTIME",
        source_timestamp=source,
        retrieved_at=retrieved,
        parquet_path="market/ticker=NVDA/date=2026-08-28/snapshot.parquet",
    )
