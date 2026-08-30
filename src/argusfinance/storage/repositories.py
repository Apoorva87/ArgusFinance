"""Repository for immutable market snapshot metadata."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from argusfinance.storage.models import MarketSnapshotMetadataRow


class DuplicateSnapshotError(Exception):
    """Raised when metadata already exists for a snapshot identifier."""


@dataclass(frozen=True)
class SnapshotMetadata:
    """Operational location and provenance of an immutable market snapshot."""

    snapshot_id: str
    ticker: str
    provider: str
    status: str
    source_timestamp: datetime
    retrieved_at: datetime
    parquet_path: str


class SnapshotMetadataRepository:
    """Persist and retrieve snapshot metadata using short-lived sessions."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, metadata: SnapshotMetadata) -> None:
        """Persist metadata, rejecting a duplicate identifier without poisoning sessions."""
        row = MarketSnapshotMetadataRow(
            snapshot_id=metadata.snapshot_id,
            ticker=_normalize_ticker(metadata.ticker),
            provider=metadata.provider,
            status=metadata.status,
            source_timestamp=_normalize_timestamp(metadata.source_timestamp),
            retrieved_at=_normalize_timestamp(metadata.retrieved_at),
            parquet_path=metadata.parquet_path,
        )
        with self._factory() as session:
            session.add(row)
            try:
                session.commit()
            except IntegrityError as error:
                session.rollback()
                raise DuplicateSnapshotError(metadata.snapshot_id) from error

    def get(self, snapshot_id: str) -> SnapshotMetadata | None:
        """Return metadata for an exact snapshot identifier, when present."""
        with self._factory() as session:
            row = session.get(MarketSnapshotMetadataRow, snapshot_id)
            return _to_metadata(row) if row is not None else None

    def latest_for_ticker(self, ticker: str) -> SnapshotMetadata | None:
        """Return the deterministic newest metadata row for a ticker."""
        normalized_ticker = _normalize_ticker(ticker)
        statement = (
            select(MarketSnapshotMetadataRow)
            .where(MarketSnapshotMetadataRow.ticker == normalized_ticker)
            .order_by(
                desc(MarketSnapshotMetadataRow.retrieved_at),
                desc(MarketSnapshotMetadataRow.snapshot_id),
            )
            .limit(1)
        )
        with self._factory() as session:
            row = session.scalar(statement)
            return _to_metadata(row) if row is not None else None


def _normalize_ticker(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if not normalized:
        raise ValueError("ticker must not be blank")
    return normalized


def _normalize_timestamp(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return timestamp.astimezone(UTC)


def _to_metadata(row: MarketSnapshotMetadataRow) -> SnapshotMetadata:
    return SnapshotMetadata(
        snapshot_id=row.snapshot_id,
        ticker=row.ticker,
        provider=row.provider,
        status=row.status,
        source_timestamp=_attach_utc(row.source_timestamp),
        retrieved_at=_attach_utc(row.retrieved_at),
        parquet_path=row.parquet_path,
    )


def _attach_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)
