"""Phase 2 extensions: sessions, enrollments, uploads, scoring columns.

Revision ID: 0002_phase2_core_extensions
Revises: 0001_initial_schema
Create Date: 2026-11-24
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_phase2_core_extensions"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Phase 1 fix: 0001 created both a UNIQUE constraint and a redundant non-unique index on
    # these columns. Replace with the single unique index the ORM models declare.
    for table, column in (("tenants", "slug"), ("users", "email")):
        op.drop_constraint(f"{table}_{column}_key", table, type_="unique")
        op.drop_index(f"ix_{table}_{column}", table_name=table)
        op.create_index(f"ix_{table}_{column}", table, [column], unique=True)

    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])

    op.create_table(
        "assessment_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id"), nullable=False
        ),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("assessment_id", "candidate_id", name="uq_enrollment_assessment_candidate"),
    )
    op.create_index("ix_assessment_enrollments_tenant_id", "assessment_enrollments", ["tenant_id"])
    op.create_index(
        "ix_assessment_enrollments_assessment_id", "assessment_enrollments", ["assessment_id"]
    )
    op.create_index(
        "ix_assessment_enrollments_candidate_id", "assessment_enrollments", ["candidate_id"]
    )

    op.create_table(
        "uploaded_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attempts.id"), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("stored_name", sa.String(128), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_uploaded_files_tenant_id", "uploaded_files", ["tenant_id"])
    op.create_index("ix_uploaded_files_attempt_id", "uploaded_files", ["attempt_id"])
    op.create_index("ix_uploaded_files_question_id", "uploaded_files", ["question_id"])

    op.add_column(
        "responses",
        sa.Column("client_seq", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "submissions",
        sa.Column("scores_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_unique_constraint("uq_submission_attempt", "submissions", ["attempt_id"])
    op.add_column("execution_jobs", sa.Column("result_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("execution_jobs", "result_json")
    op.drop_constraint("uq_submission_attempt", "submissions", type_="unique")
    op.drop_column("submissions", "scores_json")
    op.drop_column("responses", "client_seq")
    op.drop_table("uploaded_files")
    op.drop_table("assessment_enrollments")
    op.drop_table("user_sessions")

    for table, column in (("tenants", "slug"), ("users", "email")):
        op.drop_index(f"ix_{table}_{column}", table_name=table)
        op.create_index(f"ix_{table}_{column}", table, [column])
        op.create_unique_constraint(f"{table}_{column}_key", table, [column])
