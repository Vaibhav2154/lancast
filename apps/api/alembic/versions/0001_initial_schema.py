"""Initial LANCAST core schema (Phase 1).

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-11-24
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),
    )
    op.create_index("ix_memberships_tenant_id", "memberships", ["tenant_id"])
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])

    op.create_table(
        "assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assessments_tenant_id", "assessments", ["tenant_id"])
    op.create_index("ix_assessments_status", "assessments", ["status"])

    op.create_table(
        "assessment_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("canonical_digest", sa.String(64), nullable=False),
        sa.Column("is_frozen", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("assessment_id", "version_number", name="uq_assessment_version_number"),
    )
    op.create_index("ix_assessment_versions_tenant_id", "assessment_versions", ["tenant_id"])
    op.create_index("ix_assessment_versions_assessment_id", "assessment_versions", ["assessment_id"])

    op.create_table(
        "questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("assessment_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessment_versions.id"), nullable=False),
        sa.Column("question_type", sa.String(32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("prompt_json", sa.JSON(), nullable=False),
        sa.Column("hidden_eval_json", sa.JSON(), nullable=False),
        sa.Column("max_score", sa.Float(), nullable=False, server_default="1.0"),
    )
    op.create_index("ix_questions_tenant_id", "questions", ["tenant_id"])
    op.create_index("ix_questions_assessment_version_id", "questions", ["assessment_version_id"])

    op.create_table(
        "attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("assessment_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessment_versions.id"), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="in_progress"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_attempts_tenant_id", "attempts", ["tenant_id"])
    op.create_index("ix_attempts_assessment_version_id", "attempts", ["assessment_version_id"])
    op.create_index("ix_attempts_candidate_id", "attempts", ["candidate_id"])
    op.create_index("ix_attempts_status", "attempts", ["status"])

    op.create_table(
        "responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attempts.id"), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_response_attempt_question"),
    )
    op.create_index("ix_responses_tenant_id", "responses", ["tenant_id"])
    op.create_index("ix_responses_attempt_id", "responses", ["attempt_id"])
    op.create_index("ix_responses_question_id", "responses", ["question_id"])

    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attempts.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("attempt_id", "idempotency_key", name="uq_submission_attempt_idempotency"),
    )
    op.create_index("ix_submissions_tenant_id", "submissions", ["tenant_id"])
    op.create_index("ix_submissions_attempt_id", "submissions", ["attempt_id"])
    op.create_index("ix_submissions_status", "submissions", ["status"])

    op.create_table(
        "execution_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("submissions.id"), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("language", sa.String(32), nullable=False),
        sa.Column("priority_class", sa.String(32), nullable=False, server_default="coding_standard"),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("worker_id", sa.String(128), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_execution_jobs_tenant_id", "execution_jobs", ["tenant_id"])
    op.create_index("ix_execution_jobs_submission_id", "execution_jobs", ["submission_id"])
    op.create_index("ix_execution_jobs_question_id", "execution_jobs", ["question_id"])
    op.create_index("ix_execution_jobs_status", "execution_jobs", ["status"])

    op.create_table(
        "audit_events",
        sa.Column("sequence_num", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(128), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False, server_default="OK"),
        sa.Column("policy_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_event_hash", "audit_events", ["event_hash"])

    op.create_table(
        "signed_audit_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("up_to_sequence", sa.BigInteger(), sa.ForeignKey("audit_events.sequence_num"), nullable=False),
        sa.Column("root_hash", sa.String(64), nullable=False),
        sa.Column("signature_ed25519", sa.String(256), nullable=False),
        sa.Column("key_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_signed_audit_checkpoints_up_to_sequence", "signed_audit_checkpoints", ["up_to_sequence"])


def downgrade() -> None:
    op.drop_table("signed_audit_checkpoints")
    op.drop_table("audit_events")
    op.drop_table("execution_jobs")
    op.drop_table("submissions")
    op.drop_table("responses")
    op.drop_table("attempts")
    op.drop_table("questions")
    op.drop_table("assessment_versions")
    op.drop_table("assessments")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("tenants")
