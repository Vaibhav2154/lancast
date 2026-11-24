import hmac
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header

from app.core.deps import AppSettings, DbSession
from app.core.errors import api_error
from app.db.models import ExecutionJob, Question
from app.schemas.attempts import ExecutionResultIn
from app.services import attempts as attempt_svc

# Worker-only surface. Traefik blocks /api/internal from browsers; the shared secret is a
# second layer (defense in depth). Workers hold no database credentials (T19).
router = APIRouter(prefix="/api/internal", tags=["internal"], include_in_schema=False)

_TERMINAL = {"completed", "failed", "timed_out"}


@router.post("/execution/jobs/{job_id}/result")
async def report_result(
    job_id: UUID,
    body: ExecutionResultIn,
    db: DbSession,
    settings: AppSettings,
    x_worker_token: Annotated[str | None, Header()] = None,
) -> dict:
    if x_worker_token is None or not hmac.compare_digest(
        x_worker_token.encode(), settings.worker_shared_secret.encode()
    ):
        raise api_error(401, "BAD_WORKER_TOKEN", "Invalid worker credentials")

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
