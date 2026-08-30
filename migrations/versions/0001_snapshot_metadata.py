"""Create the market snapshot metadata table.

Revision ID: 0001_snapshot_metadata
Revises:
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_snapshot_metadata"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create operational metadata and its latest-ticker lookup index."""
    op.create_table(
        "market_snapshot_metadata",
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parquet_path", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("snapshot_id"),
    )
    op.create_index(
        "ix_market_snapshot_metadata_ticker_retrieved_at",
        "market_snapshot_metadata",
        ["ticker", "retrieved_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove only the operational metadata objects created by this revision."""
    op.drop_index(
        "ix_market_snapshot_metadata_ticker_retrieved_at",
        table_name="market_snapshot_metadata",
    )
    op.drop_table("market_snapshot_metadata")
