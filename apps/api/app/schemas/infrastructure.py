from datetime import datetime
from typing import Any

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
