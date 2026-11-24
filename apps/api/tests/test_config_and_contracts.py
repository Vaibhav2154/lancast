from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.contracts.interfaces import (
    AdmissionDecision,
    ExecutionJobContract,
    SecurityContext,
    TelemetrySample,
    WorkloadDescriptor,
)
from app.core.config import Settings
from app.core.logging import StructuredJsonFormatter
from app.db.models import Base


def test_settings_validates_postgres_url_and_sync_conversion() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://lancast:secret@postgres:5432/lancast",
        deployment_profile="standalone",
    )
    assert settings.sync_database_url == "postgresql+psycopg://lancast:secret@postgres:5432/lancast"

    with pytest.raises(ValidationError):
        Settings(database_url="mysql://user:pass@localhost/db")


def test_core_tables_registered_in_metadata() -> None:
    expected_tables = {
        "tenants",
        "users",
        "memberships",
        "assessments",
        "assessment_versions",
        "questions",
        "attempts",
        "responses",
        "submissions",
        "execution_jobs",
        "audit_events",
        "signed_audit_checkpoints",
    }
    assert expected_tables.issubset(set(Base.metadata.tables.keys()))


def test_orchestration_and_security_contracts() -> None:
    workload = WorkloadDescriptor(
        tenant_id=uuid4(),
        assessment_id=uuid4(),
        expected_candidates=120,
        duration_minutes=60,
        mcq_count=30,
        coding_count=2,
    )
    assert workload.expected_candidates == 120

    sample = TelemetrySample(
        machine_id="node-dev-01",
        collected_at=datetime.now(UTC),
        cpu_percent=42.5,
        memory_percent=61.0,
        disk_percent=50.0,
        queue_depth=3,
    )
    assert sample.healthy is True

    decision = AdmissionDecision(decision="accept", reasons=["within_envelope"], policy_version="v1")
    assert decision.decision == "accept"

    job = ExecutionJobContract(
        job_id=uuid4(),
        tenant_id=workload.tenant_id,
        attempt_id=uuid4(),
        question_id=uuid4(),
        language="python3",
    )
    assert job.priority_class == "coding_standard"

    sec_ctx = SecurityContext(role="candidate", operation="save_response", assessment_type="mcq")
    assert sec_ctx.operation == "save_response"


def test_structured_logger_redacts_sensitive_keys() -> None:
    import logging

    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="lancast.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="auth event",
        args=(),
        exc_info=None,
    )
    record.structured = {"password": "super-secret", "token": "abc123", "user": "alice"}
    formatted = formatter.format(record)
    assert "super-secret" not in formatted
    assert "abc123" not in formatted
    assert '"[REDACTED]"' in formatted
    assert '"alice"' in formatted
