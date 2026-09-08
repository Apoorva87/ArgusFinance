"""SQLite persistence contract for immutable saved strategy evaluations."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from argusfinance.domain.market import MarketDataStatus
from argusfinance.domain.strategy import (
    LegSide,
    NetGreeks,
    OptionLeg,
    OptionType,
    Pricing,
    SavedStrategy,
    StrategyDraft,
    StrategyEvaluation,
    StrategyStatus,
)
from argusfinance.storage.database import create_session_factory
from argusfinance.storage.repositories import (
    SnapshotMetadata,
    SnapshotMetadataRepository,
)
from argusfinance.storage.strategies import StrategyRepository


def test_repository_persists_entry_evaluation_and_creation_event_atomically(tmp_path, apply_migrations) -> None:
    """Dropping either stored document or its creation event must fail this restart read."""
    database_url = f"sqlite:///{tmp_path / 'strategy.sqlite'}"
    apply_migrations(database_url)
    factory, _ = create_session_factory(database_url)
    saved = _saved()
    SnapshotMetadataRepository(factory).add(
        SnapshotMetadata(
            snapshot_id=str(saved.draft.snapshot_id), ticker="NVDA", provider="mock", status="FROZEN",
            source_timestamp=datetime(2026, 8, 28, tzinfo=UTC), retrieved_at=datetime(2026, 8, 28, tzinfo=UTC), parquet_path="market/test.parquet",
        )
    )

    StrategyRepository(factory).save(saved)
    reopened = StrategyRepository(factory).get(saved.id)

    assert reopened == saved
    assert StrategyRepository(factory).event_count(saved.id) == 1


def test_failed_creation_event_rolls_back_entire_saved_document(tmp_path, apply_migrations) -> None:
    database_url = f"sqlite:///{tmp_path / 'rollback.sqlite'}"
    apply_migrations(database_url)
    factory, engine = create_session_factory(database_url)
    saved = _saved()
    SnapshotMetadataRepository(factory).add(SnapshotMetadata(
        snapshot_id=str(saved.draft.snapshot_id), ticker="NVDA", provider="mock", status="FROZEN",
        source_timestamp=datetime(2026, 8, 28, tzinfo=UTC), retrieved_at=datetime(2026, 8, 28, tzinfo=UTC), parquet_path="market/test.parquet",
    ))
    with engine.begin() as connection:
        connection.execute(text("CREATE TRIGGER reject_event BEFORE INSERT ON strategy_events BEGIN SELECT RAISE(ABORT, 'event failed'); END"))
    with pytest.raises(IntegrityError, match="event failed"):
        StrategyRepository(factory).save(saved)
    fresh_factory, _ = create_session_factory(database_url)
    assert StrategyRepository(fresh_factory).list() == []
    assert StrategyRepository(fresh_factory).event_count(saved.id) == 0


def test_strategy_migration_roundtrip_preserves_snapshot_metadata(tmp_path, apply_migrations) -> None:
    database_url = f"sqlite:///{tmp_path / 'roundtrip.sqlite'}"
    apply_migrations(database_url)
    factory, _ = create_session_factory(database_url)
    snapshot_id = str(_saved().draft.snapshot_id)
    SnapshotMetadataRepository(factory).add(SnapshotMetadata(
        snapshot_id=snapshot_id, ticker="NVDA", provider="mock", status="FROZEN",
        source_timestamp=datetime(2026, 8, 28, tzinfo=UTC), retrieved_at=datetime(2026, 8, 28, tzinfo=UTC), parquet_path="market/test.parquet",
    ))
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["argus_database_url_explicit"] = True
    command.downgrade(config, "0001_snapshot_metadata")
    command.upgrade(config, "head")
    fresh_factory, engine = create_session_factory(database_url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT snapshot_id FROM market_snapshot_metadata")).scalar_one() == snapshot_id
    assert StrategyRepository(fresh_factory).list() == []


def _saved() -> SavedStrategy:
    draft = StrategyDraft(
        snapshot_id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Stored",
        status=StrategyStatus.PAPER,
        legs=(OptionLeg(expiration=datetime(2026, 9, 18, tzinfo=UTC).date(), strike=Decimal(175), option_type=OptionType.CALL, side=LegSide.BUY, quantity=1),),
    )
    evaluation = StrategyEvaluation(
        snapshot_id=draft.snapshot_id,
        ticker="NVDA",
        expiration=datetime(2026, 9, 18, tzinfo=UTC).date(),
        spot=Decimal("180.25"),
        pricing=Pricing.NATURAL,
        legs=(),
        net_debit=Decimal(505),
        entry_fees=Decimal(0),
        maximum_profit=Decimal(495),
        maximum_loss=Decimal(505),
        breakevens=[Decimal("180.05")],
        payoff_points=[],
        net_greeks=NetGreeks(delta=None, gamma=None, theta=None, vega=None),
        warnings=["FROZEN/mock snapshot: hypothetical analysis, not live market evidence"],
        eligible=True,
        analytics_version="expiration-payoff-v1",
        source_timestamp=datetime(2026, 8, 28, tzinfo=UTC),
        source_status=MarketDataStatus.FROZEN,
        boundaries=(),
    )
    return SavedStrategy(id=uuid4(), created_at=datetime.now(UTC), draft=draft, evaluation=evaluation)
