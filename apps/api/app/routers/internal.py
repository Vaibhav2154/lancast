import hmac
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header

from app.core.config import Settings
from app.core.deps import AppSettings, DbSession
from app.core.errors import api_error
from app.core.timeutil import utcnow
from app.db.models import ExecutionJob, Question, WorkerNode
from app.schemas.attempts import ExecutionResultIn
from app.schemas.infrastructure import TelemetrySampleIn, WorkerHeartbeatIn, WorkerHeartbeatOut
from app.services import attempts as attempt_svc
from app.services import telemetry as telemetry_svc

# Worker-only surface. Traefik blocks /api/internal on candidate ports; the shared secret is a
# second layer (defense in depth). Workers hold no database credentials (T19).
router = APIRouter(prefix="/api/internal", tags=["internal"], include_in_schema=False)

_TERMINAL = {"completed", "failed", "timed_out"}


def _verify_worker_token(x_worker_token: str | None, settings: Settings) -> None:
    if x_worker_token is None or not hmac.compare_digest(
        x_worker_token.encode(), settings.worker_shared_secret.encode()
    ):
        raise api_error(401, "BAD_WORKER_TOKEN", "Invalid worker credentials")


@router.post("/execution/jobs/{job_id}/result")
async def report_result(
    job_id: UUID,
    body: ExecutionResultIn,
    db: DbSession,
    settings: AppSettings,
    x_worker_token: Annotated[str | None, Header()] = None,
) -> dict:
    _verify_worker_token(x_worker_token, settings)

    job = await db.get(ExecutionJob, job_id)
    if job is None:
        raise api_error(404, "NOT_FOUND", "Job not found")
    if job.status in _TERMINAL:
        return {"job_id": job.id, "status": job.status, "duplicate": True}

    question = await db.get(Question, job.question_id)
    total = len(question.hidden_eval_json["test_cases"]) if question else 0
    passed = sum(1 for r in body.test_results if r.passed)
    await attempt_svc.apply_job_outcome(
        db,
        job,
        status=body.status,
        passed=min(passed, total),
        total=total,
        error=body.error,
        worker_id=body.worker_id,
    )
    await db.commit()
    return {"job_id": job.id, "status": job.status, "duplicate": False}


@router.post("/workers/heartbeat", response_model=WorkerHeartbeatOut)
async def worker_heartbeat(
    body: WorkerHeartbeatIn,
    db: DbSession,
    settings: AppSettings,
    x_worker_token: Annotated[str | None, Header()] = None,
) -> WorkerHeartbeatOut:
    """Upsert worker node health and queue execution counters (FR-ADM-02, DEP-01)."""
    _verify_worker_token(x_worker_token, settings)
    now = utcnow()
    status = "online" if body.judge0_ok else "degraded"

    node = await db.get(WorkerNode, body.worker_id)
    if node is None:
        node = WorkerNode(
            worker_id=body.worker_id,
            hostname=body.hostname,
            deployment_mode=body.deployment_mode,
            status=status,
            judge0_ok=body.judge0_ok,
            active_jobs=body.active_jobs,
            jobs_completed=body.jobs_completed,
            jobs_failed=body.jobs_failed,
            metadata_json=body.metadata,
            registered_at=now,
            last_heartbeat_at=now,
        )
        db.add(node)
    else:
        node.hostname = body.hostname
        node.deployment_mode = body.deployment_mode
        node.status = status
        node.judge0_ok = body.judge0_ok
        node.active_jobs = body.active_jobs
        node.jobs_completed = body.jobs_completed
        node.jobs_failed = body.jobs_failed
        node.metadata_json = body.metadata
        node.last_heartbeat_at = now

    await db.commit()
    return WorkerHeartbeatOut(worker_id=node.worker_id, status=node.status, recorded_at=now)


@router.post("/telemetry/samples")
async def ingest_telemetry_sample(
    body: TelemetrySampleIn,
    db: DbSession,
    settings: AppSettings,
    x_worker_token: Annotated[str | None, Header()] = None,
) -> dict:
    """Ingest a normalized host/worker telemetry sample (FR-RES-01, T12)."""
    _verify_worker_token(x_worker_token, settings)
    row = await telemetry_svc.ingest_sample(db, settings, body)
    await db.commit()
    return {"id": row.id, "machine_id": row.machine_id, "collected_at": row.collected_at}
