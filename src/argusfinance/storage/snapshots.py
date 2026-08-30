"""Immutable, normalized Parquet storage for market snapshots."""

import os
from datetime import UTC
from pathlib import Path
from typing import Any
from uuid import UUID

import duckdb
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from argusfinance.domain.market import (
    MarketDataStatus,
    MarketSnapshot,
    OptionQuote,
    UnderlyingQuote,
)


class SnapshotNotFoundError(LookupError):
    """Raised when an immutable snapshot Parquet file cannot be found."""


class SnapshotConflictError(ValueError):
    """Raised when a UUID-addressed immutable snapshot would be changed."""


_SCHEMA = pa.schema(
    [
        pa.field("snapshot_id", pa.string(), nullable=False),
        pa.field("snapshot_created_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("underlying_ticker", pa.string(), nullable=False),
        pa.field("underlying_price", pa.decimal128(28, 10), nullable=False),
        pa.field("underlying_source", pa.string(), nullable=False),
        pa.field("underlying_source_timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("underlying_retrieved_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("underlying_status", pa.string(), nullable=False),
        pa.field("option_ticker", pa.string(), nullable=False),
        pa.field("option_expiration", pa.date32(), nullable=False),
        pa.field("option_strike", pa.decimal128(28, 10), nullable=False),
        pa.field("option_type", pa.string(), nullable=False),
        pa.field("option_bid", pa.decimal128(28, 10), nullable=False),
        pa.field("option_ask", pa.decimal128(28, 10), nullable=False),
        pa.field("option_volume", pa.int64(), nullable=False),
        pa.field("option_open_interest", pa.int64(), nullable=False),
        pa.field("option_implied_volatility", pa.decimal128(28, 12), nullable=False),
        pa.field("option_delta", pa.decimal128(28, 12), nullable=False),
        pa.field("option_gamma", pa.decimal128(28, 12), nullable=False),
        pa.field("option_theta", pa.decimal128(28, 12), nullable=False),
        pa.field("option_vega", pa.decimal128(28, 12), nullable=False),
        pa.field("option_source", pa.string(), nullable=False),
        pa.field("option_source_timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("option_retrieved_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("option_status", pa.string(), nullable=False),
    ]
)


class SnapshotStore:
    """Store and retrieve complete market snapshots under an injected root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def write(self, snapshot: MarketSnapshot) -> Path:
        """Persist a snapshot once, preserving UUID-addressed immutable history."""
        canonical = _canonical_snapshot(snapshot)
        existing = self._paths_for_snapshot(canonical.snapshot_id)
        if existing:
            if len(existing) == 1 and self.read(canonical.snapshot_id) == canonical:
                return existing[0]
            raise SnapshotConflictError(
                f"snapshot {canonical.snapshot_id} already exists with different immutable content"
            )

        path = self._path_for(canonical)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".parquet.tmp")
        try:
            pq.write_table(pa.Table.from_pylist(_rows(canonical), schema=_SCHEMA), temporary)
            os.replace(temporary, path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return path

    def read(self, snapshot_id: UUID | str) -> MarketSnapshot:
        """Read exactly one UUID-addressed file through DuckDB."""
        resolved_id = _parse_snapshot_id(snapshot_id)
        paths = self._paths_for_snapshot(resolved_id)
        if not paths:
            raise SnapshotNotFoundError(f"snapshot {resolved_id} was not found")
        if len(paths) != 1:
            raise SnapshotConflictError(f"snapshot {resolved_id} has multiple immutable files")

        connection = duckdb.connect()
        try:
            relation = connection.execute(
                """
                SELECT * FROM read_parquet(?)
                ORDER BY option_expiration, option_strike, option_type
                """,
                [str(paths[0])],
            )
            rows = relation.to_arrow_table().to_pylist()
        finally:
            connection.close()
        if not rows:
            raise SnapshotNotFoundError(f"snapshot {resolved_id} contains no option quotes")
        return _snapshot_from_rows(rows, resolved_id)

    def delete(self, snapshot_id: UUID | str) -> None:
        """Delete only the exact UUID-addressed Parquet file, if present."""
        resolved_id = _parse_snapshot_id(snapshot_id)
        for path in self._paths_for_snapshot(resolved_id):
            path.unlink(missing_ok=True)

    def _path_for(self, snapshot: MarketSnapshot) -> Path:
        return (
            self.root
            / "market"
            / f"ticker={snapshot.underlying.ticker}"
            / f"date={snapshot.created_at.astimezone(UTC).date().isoformat()}"
            / f"snapshot={snapshot.snapshot_id}.parquet"
        )

    def _paths_for_snapshot(self, snapshot_id: UUID) -> list[Path]:
        market_root = self.root / "market"
        if not market_root.is_dir():
            return []
        filename = f"snapshot={snapshot_id}.parquet"
        return sorted(
            path
            for path in market_root.rglob(filename)
            if path.is_file() and path.name == filename and path.resolve().is_relative_to(self.root)
        )


def _canonical_snapshot(snapshot: MarketSnapshot) -> MarketSnapshot:
    return snapshot.model_copy(
        update={
            "options": tuple(
                sorted(
                    snapshot.options,
                    key=lambda option: (option.expiration, option.strike, option.option_type),
                )
            )
        }
    )


def _rows(snapshot: MarketSnapshot) -> list[dict[str, object]]:
    return [
        {
            "snapshot_id": str(snapshot.snapshot_id),
            "snapshot_created_at": snapshot.created_at,
            "underlying_ticker": snapshot.underlying.ticker,
            "underlying_price": snapshot.underlying.price,
            "underlying_source": snapshot.underlying.source,
            "underlying_source_timestamp": snapshot.underlying.source_timestamp,
            "underlying_retrieved_at": snapshot.underlying.retrieved_at,
            "underlying_status": snapshot.underlying.status.value,
            "option_ticker": option.ticker,
            "option_expiration": option.expiration,
            "option_strike": option.strike,
            "option_type": option.option_type,
            "option_bid": option.bid,
            "option_ask": option.ask,
            "option_volume": option.volume,
            "option_open_interest": option.open_interest,
            "option_implied_volatility": option.implied_volatility,
            "option_delta": option.delta,
            "option_gamma": option.gamma,
            "option_theta": option.theta,
            "option_vega": option.vega,
            "option_source": option.source,
            "option_source_timestamp": option.source_timestamp,
            "option_retrieved_at": option.retrieved_at,
            "option_status": option.status.value,
        }
        for option in snapshot.options
    ]


def _snapshot_from_rows(rows: list[dict[str, Any]], snapshot_id: UUID) -> MarketSnapshot:
    first = rows[0]
    underlying = UnderlyingQuote(
        ticker=first["underlying_ticker"],
        price=first["underlying_price"],
        source=first["underlying_source"],
        source_timestamp=first["underlying_source_timestamp"],
        retrieved_at=first["underlying_retrieved_at"],
        status=MarketDataStatus(first["underlying_status"]),
    )
    options = tuple(
        OptionQuote(
            ticker=row["option_ticker"],
            expiration=row["option_expiration"],
            strike=row["option_strike"],
            option_type=row["option_type"],
            bid=row["option_bid"],
            ask=row["option_ask"],
            volume=row["option_volume"],
            open_interest=row["option_open_interest"],
            implied_volatility=row["option_implied_volatility"],
            delta=row["option_delta"],
            gamma=row["option_gamma"],
            theta=row["option_theta"],
            vega=row["option_vega"],
            source=row["option_source"],
            source_timestamp=row["option_source_timestamp"],
            retrieved_at=row["option_retrieved_at"],
            status=MarketDataStatus(row["option_status"]),
        )
        for row in rows
    )
    return MarketSnapshot(
        snapshot_id=snapshot_id,
        underlying=underlying,
        options=options,
        created_at=first["snapshot_created_at"],
    )


def _parse_snapshot_id(snapshot_id: UUID | str) -> UUID:
    try:
        return UUID(str(snapshot_id))
    except (TypeError, ValueError) as error:
        raise ValueError("snapshot_id must be a valid UUID") from error
