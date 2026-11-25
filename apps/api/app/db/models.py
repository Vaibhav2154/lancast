from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import utcnow
from app.db.session import Base

# BIGSERIAL on PostgreSQL; plain INTEGER PK on SQLite so autoincrement works in tests.
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


def _uuid_pk() -> Mapped[UUID]:
    return mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)


def _fk(table: str, *, nullable: bool = False, index: bool = True) -> Mapped[UUID]:
    return mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(f"{table}.id"), nullable=nullable, index=index
    )


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = _uuid_pk()
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class UserSession(Base):
    """Server-side session record; the JWT `jti` maps here so tokens can be revoked (FR-ID-03)."""

    __tablename__ = "user_sessions"

    id: Mapped[UUID] = _uuid_pk()
    user_id: Mapped[UUID] = _fk("users")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),)

    id: Mapped[UUID] = _uuid_pk()
    tenant_id: Mapped[UUID] = _fk("tenants")
    user_id: Mapped[UUID] = _fk("users")
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # tenant_admin | organizer | candidate
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[UUID] = _uuid_pk()
    tenant_id: Mapped[UUID] = _fk("tenants")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    created_by: Mapped[UUID] = _fk("users", index=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AssessmentVersion(Base):
    __tablename__ = "assessment_versions"
    __table_args__ = (
        UniqueConstraint("assessment_id", "version_number", name="uq_assessment_version_number"),
    )

    id: Mapped[UUID] = _uuid_pk()
    tenant_id: Mapped[UUID] = _fk("tenants")
    assessment_id: Mapped[UUID] = _fk("assessments")
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    canonical_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AssessmentEnrollment(Base):
    """Explicit candidate assignment to an assessment (FR-AS-04, FR-ATT-01)."""

    __tablename__ = "assessment_enrollments"
    __table_args__ = (
        UniqueConstraint("assessment_id", "candidate_id", name="uq_enrollment_assessment_candidate"),
    )

    id: Mapped[UUID] = _uuid_pk()
    tenant_id: Mapped[UUID] = _fk("tenants")
    assessment_id: Mapped[UUID] = _fk("assessments")
    candidate_id: Mapped[UUID] = _fk("users")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[UUID] = _uuid_pk()
    tenant_id: Mapped[UUID] = _fk("tenants")
    assessment_version_id: Mapped[UUID] = _fk("assessment_versions")
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    hidden_eval_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[UUID] = _uuid_pk()
    tenant_id: Mapped[UUID] = _fk("tenants")
    assessment_version_id: Mapped[UUID] = _fk("assessment_versions")
    candidate_id: Mapped[UUID] = _fk("users")
    status: Mapped[str] = mapped_column(String(32), default="in_progress", nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Response(Base):
    __tablename__ = "responses"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_response_attempt_question"),)

    id: Mapped[UUID] = _uuid_pk()
    tenant_id: Mapped[UUID] = _fk("tenants")
    attempt_id: Mapped[UUID] = _fk("attempts")
    question_id: Mapped[UUID] = _fk("questions")
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    # Monotonic client sequence: rejects stale/replayed autosaves (FR-SEC-05).
    client_seq: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[UUID] = _uuid_pk()
    tenant_id: Mapped[UUID] = _fk("tenants")
    attempt_id: Mapped[UUID] = _fk("attempts")
    question_id: Mapped[UUID] = _fk("questions")
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(128), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("attempt_id", name="uq_submission_attempt"),
        UniqueConstraint("attempt_id", "idempotency_key", name="uq_submission_attempt_idempotency"),
    )

    id: Mapped[UUID] = _uuid_pk()
    tenant_id: Mapped[UUID] = _fk("tenants")
    attempt_id: Mapped[UUID] = _fk("attempts")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    scores_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ExecutionJob(Base):
    __tablename__ = "execution_jobs"

    id: Mapped[UUID] = _uuid_pk()
    tenant_id: Mapped[UUID] = _fk("tenants")
    submission_id: Mapped[UUID] = _fk("submissions")
    question_id: Mapped[UUID] = _fk("questions")
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    priority_class: Mapped[str] = mapped_column(String(32), default="coding_standard", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    sequence_num: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), unique=True, nullable=False, default=uuid4)
    tenant_id: Mapped[UUID | None] = _fk("tenants", nullable=True)
    actor_id: Mapped[UUID | None] = _fk("users", nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), default="OK", nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class SignedAuditCheckpoint(Base):
    __tablename__ = "signed_audit_checkpoints"

    id: Mapped[UUID] = _uuid_pk()
    up_to_sequence: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("audit_events.sequence_num"), nullable=False, index=True
    )
    root_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_ed25519: Mapped[str] = mapped_column(String(256), nullable=False)
    key_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class WorkerNode(Base):
    __tablename__ = "worker_nodes"

    worker_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    deployment_mode: Mapped[str] = mapped_column(String(32), default="standalone", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="online", nullable=False)
    judge0_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
