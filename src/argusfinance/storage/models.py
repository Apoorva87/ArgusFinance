"""SQLAlchemy mappings for operational snapshot metadata."""

from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for local SQLAlchemy mappings."""


class MarketSnapshotMetadataRow(Base):
    """Persisted location and provenance for an immutable market snapshot."""

    __tablename__ = "market_snapshot_metadata"
    __table_args__ = (
        Index(
            "ix_market_snapshot_metadata_ticker_retrieved_at",
            "ticker",
            "retrieved_at",
        ),
    )

    snapshot_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    parquet_path: Mapped[str] = mapped_column(String, nullable=False)
