from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkerHeartbeatIn(BaseModel):
    worker_id: str = Field(min_length=1, max_length=128)
    hostname: str = Field(min_length=1, max_length=255)
    deployment_mode: str = Field(default="standalone", min_length=1, max_length=32)
    judge0_ok: bool
    active_jobs: int = Field(default=0, ge=0)
    jobs_completed: int = Field(default=0, ge=0)
    jobs_failed: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerHeartbeatOut(BaseModel):
    worker_id: str
    status: str
    recorded_at: datetime


class WorkerNodeOut(BaseModel):
    worker_id: str
    hostname: str
    deployment_mode: str
    status: str
    judge0_ok: bool
    active_jobs: int
    jobs_completed: int
    jobs_failed: int
    registered_at: datetime
    last_heartbeat_at: datetime
    stale: bool


class InfrastructureStatusOut(BaseModel):
    deployment_profile: str
    environment: str
    app_version: str
    public_base_url: str
    dependencies: dict[str, str]
    queue_depth: int | None
    dead_letter_depth: int | None
    worker_stale_seconds: int
    workers: list[WorkerNodeOut]


class TelemetrySampleIn(BaseModel):
    machine_id: str = Field(min_length=1, max_length=128)
    role: Literal["server", "worker", "standalone"] = "worker"
    collected_at: datetime | None = None
    cpu_percent: float = Field(ge=0.0, le=100.0)
    memory_percent: float = Field(ge=0.0, le=100.0)
    disk_percent: float = Field(ge=0.0, le=100.0)
    network_rx_kbps: float = Field(default=0.0, ge=0.0)
    network_tx_kbps: float = Field(default=0.0, ge=0.0)
    queue_depth: int = Field(default=0, ge=0)
    active_jobs: int = Field(default=0, ge=0)
    healthy: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class TelemetrySampleOut(BaseModel):
    id: int
    machine_id: str
    role: str
    collected_at: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_rx_kbps: float
    network_tx_kbps: float
    queue_depth: int
    active_jobs: int
    healthy: bool
    stale: bool
    age_seconds: float


class WorkloadLatencyOut(BaseModel):
    count: int
    p50_ms: float
    p95_ms: float
    p99_ms: float


class TelemetryOverviewOut(BaseModel):
    telemetry_state: Literal["healthy", "degraded", "missing"]
    safe_fallback_active: bool
    stale_threshold_seconds: int
    retention_hours: int
    machines: list[TelemetrySampleOut]
    workload_latencies: dict[str, WorkloadLatencyOut]
