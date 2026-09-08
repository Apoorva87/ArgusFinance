"""Tests for immutable Parquet market-snapshot persistence."""

import multiprocessing
import sys
from decimal import Decimal
from multiprocessing.synchronize import Barrier
from pathlib import Path
from queue import Queue
from threading import BrokenBarrierError
from typing import Any
from uuid import UUID

import pyarrow.parquet as pq
import pytest

from argusfinance.adapters.mock_market import MockMarketDataProvider
from argusfinance.storage.snapshots import (
    SnapshotConflictError,
    SnapshotNotFoundError,
    SnapshotStore,
)


class _CoordinatedSnapshotStore(SnapshotStore):
    """Make concurrent workers return the same initial existence check."""

    def __init__(self, root: Path, barrier: Barrier) -> None:
        super().__init__(root)
        self._barrier = barrier
        self._first_check = True

    def _paths_for_snapshot(self, snapshot_id: UUID) -> list[Path]:
        paths = super()._paths_for_snapshot(snapshot_id)
        if self._first_check:
            self._first_check = False
            try:
                self._barrier.wait(timeout=0.5)
            except BrokenBarrierError:
                pass
        return paths


def _write_in_process(
    root: Path,
    snapshot: Any,
    barrier: Barrier,
    results: Queue[str],
) -> None:
    store = _CoordinatedSnapshotStore(root, barrier)
    try:
        store.write(snapshot)
    except SnapshotConflictError:
        results.put("conflict")
    else:
        results.put("ok")


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


def test_parquet_snapshot_round_trip_preserves_unavailable_greeks(
    snapshot_store: SnapshotStore, snapshot  # type: ignore[no-untyped-def]
) -> None:
    option = snapshot.options[0].model_copy(
        update={"delta": None, "gamma": None, "theta": None, "vega": None}
    )
    unavailable = snapshot.model_copy(update={"options": (option, *snapshot.options[1:])})

    path = snapshot_store.write(unavailable)

    schema = pq.read_schema(path)
    assert schema.field("option_delta").nullable
    assert schema.field("option_gamma").nullable
    assert schema.field("option_theta").nullable
    assert schema.field("option_vega").nullable
    assert snapshot_store.read(unavailable.snapshot_id).options[0].delta is None
    assert snapshot_store.read(unavailable.snapshot_id).options[0].gamma is None
    assert snapshot_store.read(unavailable.snapshot_id).options[0].theta is None
    assert snapshot_store.read(unavailable.snapshot_id).options[0].vega is None


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
        update={
            "underlying": snapshot.underlying.model_copy(update={"price": Decimal("181.00")})
        }
    )

    with pytest.raises(SnapshotConflictError, match="immutable"):
        snapshot_store.write(conflicting)

    assert snapshot_store.read(snapshot.snapshot_id) == snapshot


def test_identical_concurrent_process_writes_are_both_idempotent(
    tmp_path: Path, snapshot  # type: ignore[no-untyped-def]
) -> None:
    results = _run_concurrent_writes(tmp_path, (snapshot, snapshot))

    assert results == ["ok", "ok"]
    assert SnapshotStore(tmp_path).read(snapshot.snapshot_id) == snapshot
    assert list(tmp_path.rglob("*.tmp")) == []


def test_conflicting_concurrent_process_writes_never_replace_first_content(
    tmp_path: Path, snapshot  # type: ignore[no-untyped-def]
) -> None:
    conflicting = snapshot.model_copy(
        update={
            "underlying": snapshot.underlying.model_copy(update={"price": Decimal("181.00")})
        }
    )

    results = _run_concurrent_writes(tmp_path, (snapshot, conflicting))

    assert results == ["conflict", "ok"]
    assert SnapshotStore(tmp_path).read(snapshot.snapshot_id) in (snapshot, conflicting)
    assert list(tmp_path.rglob("*.tmp")) == []


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


def test_write_rejects_ticker_path_traversal_before_creating_outside_root(
    tmp_path: Path, snapshot  # type: ignore[no-untyped-def]
) -> None:
    store_root = tmp_path / "store"
    outside_path = tmp_path / "escaped"
    store = SnapshotStore(store_root)
    crafted = snapshot.model_copy(
        update={
            "underlying": snapshot.underlying.model_copy(
                update={"ticker": "EVIL/../../../escaped"}
            )
        }
    )

    with pytest.raises(ValueError, match="safe partition token"):
        store.write(crafted)

    assert not outside_path.exists()


def _run_concurrent_writes(root: Path, snapshots: tuple[Any, Any]) -> list[str]:
    repository_root = str(Path(__file__).resolve().parents[2])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    results = context.Queue()
    processes = [
        context.Process(
            target=_write_in_process,
            args=(root, snapshot, barrier, results),
        )
        for snapshot in snapshots
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=10)

    assert [process.exitcode for process in processes] == [0, 0]
    return sorted(results.get(timeout=1) for _ in processes)
