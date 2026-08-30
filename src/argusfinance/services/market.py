"""Application workflow for immutable market snapshots."""

from pathlib import Path

from argusfinance.domain.market import MarketSnapshot
from argusfinance.ports.market_data import MarketDataProvider
from argusfinance.storage.repositories import (
    SnapshotMetadata,
    SnapshotMetadataRepository,
)
from argusfinance.storage.snapshots import SnapshotNotFoundError, SnapshotStore


class LatestSnapshotNotFoundError(LookupError):
    """Raised when no readable latest snapshot is available for a ticker."""


class ProviderInputError(ValueError):
    """Raised when a market-data provider rejects requested input."""


class MarketService:
    """Capture normalized snapshots and retrieve their persisted latest version."""

    def __init__(
        self,
        provider: MarketDataProvider,
        snapshot_store: SnapshotStore,
        metadata_repository: SnapshotMetadataRepository,
    ) -> None:
        self._provider = provider
        self._snapshot_store = snapshot_store
        self._metadata_repository = metadata_repository

    def capture(self, ticker: str, weeks: int = 8) -> MarketSnapshot:
        """Capture once, persist Parquet, then commit metadata for that file."""
        try:
            snapshot = self._provider.get_snapshot(ticker, weeks)
        except ValueError as error:
            raise ProviderInputError(str(error)) from error

        existed_before_write = self._snapshot_exists(snapshot)
        parquet_path = self._snapshot_store.write(snapshot)
        metadata = SnapshotMetadata(
            snapshot_id=str(snapshot.snapshot_id),
            ticker=snapshot.underlying.ticker,
            provider=snapshot.underlying.source,
            status=snapshot.underlying.status.value,
            source_timestamp=snapshot.underlying.source_timestamp,
            retrieved_at=snapshot.underlying.retrieved_at,
            parquet_path=str(self._relative_parquet_path(parquet_path)),
        )
        try:
            self._metadata_repository.add(metadata)
        except Exception:
            if not existed_before_write:
                self._snapshot_store.delete(snapshot.snapshot_id)
            raise
        return self._snapshot_store.read(snapshot.snapshot_id)

    def latest(self, ticker: str) -> MarketSnapshot:
        """Read the exact snapshot referenced by the newest ticker metadata."""
        normalized_ticker = ticker.strip().upper()
        metadata = self._metadata_repository.latest_for_ticker(normalized_ticker)
        if metadata is None:
            raise LatestSnapshotNotFoundError("No latest market snapshot found")
        try:
            return self._snapshot_store.read(metadata.snapshot_id)
        except SnapshotNotFoundError as error:
            raise LatestSnapshotNotFoundError("No latest market snapshot found") from error

    def _snapshot_exists(self, snapshot: MarketSnapshot) -> bool:
        try:
            self._snapshot_store.read(snapshot.snapshot_id)
        except SnapshotNotFoundError:
            return False
        return True

    def _relative_parquet_path(self, parquet_path: Path) -> Path:
        """Produce metadata path under the configured snapshot root only."""
        return parquet_path.resolve().relative_to(self._snapshot_store.root)
