"""Phase 3 worker registry table for infrastructure & execution health tracking.

Revision ID: 0003_worker_registry
Revises: 0002_phase2_core_extensions
Create Date: 2026-11-25
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_worker_registry"
down_revision = "0002_phase2_core_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "worker_nodes",
        sa.Column("worker_id", sa.String(length=128), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("deployment_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("judge0_ok", sa.Boolean(), nullable=False),
        sa.Column("active_jobs", sa.Integer(), nullable=False),
        sa.Column("jobs_completed", sa.Integer(), nullable=False),
        sa.Column("jobs_failed", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("worker_id"),
    )
    op.create_index(
        "ix_worker_nodes_last_heartbeat_at", "worker_nodes", ["last_heartbeat_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_worker_nodes_last_heartbeat_at", table_name="worker_nodes")
    op.drop_table("worker_nodes")
