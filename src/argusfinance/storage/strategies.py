"""Transactional SQLite storage for immutable saved strategy research."""

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, sessionmaker

from argusfinance.domain.strategy import SavedStrategy
from argusfinance.storage.models import SavedStrategyRow, StrategyEventRow


class StrategyRepository:
    """Persist a saved document and matching creation event in one transaction."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def save(self, saved: SavedStrategy) -> None:
        """Insert immutable draft/evaluation and its audit event atomically."""
        payload = _dump(saved)
        with self._factory() as session:
            session.add(
                SavedStrategyRow(
                    id=str(saved.id),
                    snapshot_id=str(saved.draft.snapshot_id),
                    created_at=saved.created_at,
                    draft_json=json.dumps(payload["draft"], separators=(",", ":")),
                    evaluation_json=json.dumps(payload["evaluation"], separators=(",", ":")),
                )
            )
            session.add(
                StrategyEventRow(
                    strategy_id=str(saved.id),
                    event_type="CREATED",
                    created_at=saved.created_at,
                    payload_json=json.dumps({"snapshot_id": str(saved.draft.snapshot_id)}, separators=(",", ":")),
                )
            )
            session.commit()

    def list(self) -> list[SavedStrategy]:
        """Return saved strategy documents newest first with no market reread."""
        statement = select(SavedStrategyRow).order_by(desc(SavedStrategyRow.created_at), desc(SavedStrategyRow.id))
        with self._factory() as session:
            return [_to_saved(row) for row in session.scalars(statement)]

    def get(self, strategy_id: UUID) -> SavedStrategy | None:
        """Return one exact stored entry evaluation."""
        with self._factory() as session:
            row = session.get(SavedStrategyRow, str(strategy_id))
            return _to_saved(row) if row is not None else None

    def event_count(self, strategy_id: UUID) -> int:
        """Return audit-event count for operational diagnostics."""
        with self._factory() as session:
            return int(
                session.scalar(
                    select(func.count()).select_from(StrategyEventRow).where(StrategyEventRow.strategy_id == str(strategy_id))
                )
                or 0
            )


def _dump(saved: SavedStrategy) -> dict[str, object]:
    return saved.model_dump(mode="json")


def _to_saved(row: SavedStrategyRow) -> SavedStrategy:
    return SavedStrategy.model_validate(
        {
            "id": row.id,
            "created_at": _attach_utc(row.created_at),
            "draft": json.loads(row.draft_json),
            "evaluation": json.loads(row.evaluation_json),
        }
    )


def _attach_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
