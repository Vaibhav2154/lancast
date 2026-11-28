"""Phase 4 normalized telemetry_samples table for host and worker telemetry.

Revision ID: 0004_telemetry_samples
Revises: 0003_worker_registry
Create Date: 2026-11-27
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_telemetry_samples"
down_revision = "0003_worker_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telemetry_samples",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("machine_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=False),
        sa.Column("memory_percent", sa.Float(), nullable=False),
        sa.Column("disk_percent", sa.Float(), nullable=False),
        sa.Column("network_rx_kbps", sa.Float(), nullable=False),
        sa.Column("network_tx_kbps", sa.Float(), nullable=False),
        sa.Column("queue_depth", sa.Integer(), nullable=False),
        sa.Column("active_jobs", sa.Integer(), nullable=False),
        sa.Column("healthy", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_telemetry_samples_machine_id", "telemetry_samples", ["machine_id"])
    op.create_index("ix_telemetry_samples_collected_at", "telemetry_samples", ["collected_at"])


def downgrade() -> None:
    op.drop_index("ix_telemetry_samples_collected_at", table_name="telemetry_samples")
    op.drop_index("ix_telemetry_samples_machine_id", table_name="telemetry_samples")
    op.drop_table("telemetry_samples")
