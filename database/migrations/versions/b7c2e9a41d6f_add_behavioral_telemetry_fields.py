
"""add behavioral telemetry fields

Revision ID: b7c2e9a41d6f
Revises: 70edc0f1d309
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7c2e9a41d6f"
down_revision: str | Sequence[str] | None = "70edc0f1d309"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "telemetry_packets",
        sa.Column("tx_interval_s", sa.Float(), nullable=True),
    )
    op.add_column(
        "telemetry_packets",
        sa.Column("freshness_status", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("telemetry_packets", "freshness_status")
    op.drop_column("telemetry_packets", "tx_interval_s")