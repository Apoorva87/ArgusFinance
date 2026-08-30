"""Tests for immutable Parquet market-snapshot persistence."""

from pathlib import Path
from uuid import UUID

import pyarrow.parquet as pq
import pytest

from argusfinance.adapters.mock_market import MockMarketDataProvider
from argusfinance.storage.snapshots import (
    SnapshotConflictError,
    SnapshotNotFoundError,
    SnapshotStore,
)


@pytest.fixture
def snapshot_store(tmp_path: Path) -> SnapshotStore:
    return SnapshotStore(tmp_path)


@pytest.fixture
def snapshot():  # type: ignore[no-untyped-def]
    return MockMarketDataProvider().get_snapshot("NVDA", weeks=8)


def test_parquet_snapshot_round_trip(snapshot_store: SnapshotStore, snapshot) -> None:  # type: ignore[no-untyped-def]
    path = snapshot_store.write(snapshot)

    assert path.suffix == ".parquet"
    assert snapshot_store.read(snapshot.snapshot_id) == snapshot
    assert snapshot_store.write(snapshot) == path


def test_write_uses_exact_partitioned_relative_path(
    snapshot_store: SnapshotStore, snapshot  # type: ignore[no-untyped-def]
) -> None:
    path = snapshot_store.write(snapshot)

    assert path.relative_to(snapshot_store.root) == Path(
        "market/ticker=NVDA/date=2026-08-28/snapshot=00000000-0000-0000-0000-000000000001.parquet"
    )


def test_write_uses_exact_explicit_parquet_schema(
    snapshot_store: SnapshotStore, snapshot  # type: ignore[no-untyped-def]
) -> None:
    path = snapshot_store.write(snapshot)

    assert pq.read_schema(path).names == [
        "snapshot_id",
        "snapshot_created_at",
        "underlying_ticker",
        "underlying_price",
        "underlying_source",
        "underlying_source_timestamp",
        "underlying_retrieved_at",
        "underlying_status",
        "option_ticker",
        "option_expiration",
        "option_strike",
        "option_type",
        "option_bid",
        "option_ask",
        "option_volume",
        "option_open_interest",
        "option_implied_volatility",
        "option_delta",
        "option_gamma",
        "option_theta",
        "option_vega",
        "option_source",
        "option_source_timestamp",
        "option_retrieved_at",
        "option_status",
    ]


def test_read_returns_options_in_canonical_order(
    snapshot_store: SnapshotStore, snapshot  # type: ignore[no-untyped-def]
) -> None:
    shuffled = snapshot.model_copy(update={"options": tuple(reversed(snapshot.options))})
    snapshot_store.write(shuffled)

    actual = snapshot_store.read(shuffled.snapshot_id)

    assert actual.options == tuple(
        sorted(
            snapshot.options,
            key=lambda option: (option.expiration, option.strike, option.option_type),
        )
    )


def test_write_rejects_different_content_for_existing_snapshot_id(
    snapshot_store: SnapshotStore, snapshot  # type: ignore[no-untyped-def]
) -> None:
    snapshot_store.write(snapshot)
    conflicting = snapshot.model_copy(
        update={"underlying": snapshot.underlying.model_copy(update={"price": "181.00"})}
    )

    with pytest.raises(SnapshotConflictError, match="immutable"):
        snapshot_store.write(conflicting)

    assert snapshot_store.read(snapshot.snapshot_id) == snapshot


def test_read_missing_snapshot_raises_domain_error(snapshot_store: SnapshotStore) -> None:
    with pytest.raises(SnapshotNotFoundError):
        snapshot_store.read(UUID("00000000-0000-0000-0000-000000000099"))


def test_delete_removes_exact_uuid_file_idempotently(
    snapshot_store: SnapshotStore, snapshot  # type: ignore[no-untyped-def]
) -> None:
    path = snapshot_store.write(snapshot)

    snapshot_store.delete(str(snapshot.snapshot_id))
    snapshot_store.delete(snapshot.snapshot_id)

    assert not path.exists()
    with pytest.raises(SnapshotNotFoundError):
        snapshot_store.read(snapshot.snapshot_id)


def test_failed_atomic_replace_cleans_temporary_file(
    monkeypatch: pytest.MonkeyPatch, snapshot_store: SnapshotStore, snapshot  # type: ignore[no-untyped-def]
) -> None:
    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr("argusfinance.storage.snapshots.os.replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        snapshot_store.write(snapshot)

    assert list(snapshot_store.root.rglob("*.tmp")) == []
