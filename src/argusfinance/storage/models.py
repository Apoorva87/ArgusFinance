"""SQLAlchemy mappings for operational snapshot metadata."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
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


class SavedStrategyRow(Base):
    """Immutable strategy draft and entry evaluation saved as one JSON document pair."""

    __tablename__ = "saved_strategies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("market_snapshot_metadata.snapshot_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    draft_json: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_json: Mapped[str] = mapped_column(Text, nullable=False)


class StrategyEventRow(Base):
    """Append-only audit event created with each saved research document."""

    __tablename__ = "strategy_events"
    __table_args__ = (Index("ix_strategy_events_strategy_id", "strategy_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("saved_strategies.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
