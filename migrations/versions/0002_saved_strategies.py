"""Create immutable saved strategy documents and creation events.

Revision ID: 0002_saved_strategies
Revises: 0001_snapshot_metadata
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_saved_strategies"
down_revision: str | None = "0001_snapshot_metadata"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create snapshot-provenanced saved strategy and append-only event tables."""
    op.create_table(
        "saved_strategies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("draft_json", sa.Text(), nullable=False),
        sa.Column("evaluation_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["market_snapshot_metadata.snapshot_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "strategy_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("strategy_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["strategy_id"], ["saved_strategies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strategy_events_strategy_id", "strategy_events", ["strategy_id"], unique=False)


def downgrade() -> None:
    """Remove only strategy tables, preserving immutable snapshot metadata."""
    op.drop_index("ix_strategy_events_strategy_id", table_name="strategy_events")
    op.drop_table("strategy_events")
    op.drop_table("saved_strategies")
