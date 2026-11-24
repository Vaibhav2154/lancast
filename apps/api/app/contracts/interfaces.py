"""Typed interface contracts between LANCAST core API, resource/security orchestrators, and queue."""

from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, Field


class WorkloadDescriptor(BaseModel):
    tenant_id: UUID
    assessment_id: UUID
    expected_candidates: int = Field(ge=1)
    duration_minutes: int = Field(ge=1)
    mcq_count: int = Field(default=0, ge=0)
    descriptive_count: int = Field(default=0, ge=0)
    upload_count: int = Field(default=0, ge=0)
    coding_count: int = Field(default=0, ge=0)
    expected_autosave_interval_sec: int = Field(default=30, ge=5)


class TelemetrySample(BaseModel):
    machine_id: str
    collected_at: datetime
    cpu_percent: float = Field(ge=0.0, le=100.0)
    memory_percent: float = Field(ge=0.0, le=100.0)
    disk_percent: float = Field(ge=0.0, le=100.0)
    queue_depth: int = Field(default=0, ge=0)
    healthy: bool = True


class CapacityEstimate(BaseModel):
    estimated_cpu_utilization: float = Field(ge=0.0)
    estimated_memory_mb: float = Field(ge=0.0)
    bottleneck: str
    uncertainty_band: float = Field(ge=0.0)
    fits_envelope: bool


class AdmissionDecision(BaseModel):
    decision: Literal["accept", "warn", "defer", "reject"]
    reasons: list[str]
    policy_version: str


class ExecutionJobContract(BaseModel):
    job_id: UUID
    tenant_id: UUID
    attempt_id: UUID
    question_id: UUID
    language: str
    priority_class: Literal["interactive", "coding_standard", "background"] = "coding_standard"
    cpu_time_limit_sec: float = Field(default=2.0, gt=0.0, le=30.0)
    memory_limit_mb: int = Field(default=256, ge=32, le=2048)


class CodeTestCase(BaseModel):
    stdin: str = ""
    expected_stdout: str


class ExecutionJobPayload(ExecutionJobContract):
    """Full job message placed on the bounded queue for an execution worker."""

    source_code: str
    test_cases: list[CodeTestCase]


class SchedulingDecision(BaseModel):
    job_id: UUID
    worker_id: str
    concurrency_budget: int = Field(ge=1)
    rationale: str
    policy_version: str


class SecurityContext(BaseModel):
    actor_id: UUID | None = None
    tenant_id: UUID | None = None
    role: str
    operation: str
    assessment_type: str | None = None
    attempt_state: str | None = None


class SecurityDecision(BaseModel):
    action: Literal["allow", "reject", "throttle", "reauthenticate", "flag", "alert"]
    reason_codes: list[str]
    policy_version: str


class ExecutionQueueContract(Protocol):
    """Queue abstraction decoupling API/scheduler from Redis or future brokers (TD-04)."""

    async def enqueue(self, job: ExecutionJobContract) -> int: ...

    async def depth(self) -> int: ...

    async def has_capacity(self, count: int) -> bool: ...

    async def health_check(self) -> bool: ...
