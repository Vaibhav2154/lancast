from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.interfaces import (
    CodeTestCase,
    ExecutionJobPayload,
    ExecutionQueueContract,
)
from app.core.errors import api_error
from app.core.timeutil import as_utc, utcnow
from app.db.models import (
    Assessment,
    AssessmentEnrollment,
    AssessmentVersion,
    Attempt,
    ExecutionJob,
    Question,
    Response,
    Submission,
    User,
)
from app.services import assessments as assessment_service
from app.services import audit
from app.services.execution_queue import QueueFullError
from app.services.question_modules import QuestionValidationError, get_module


@dataclass
class FinalizeResult:
    submission: Submission
    jobs: list[ExecutionJobPayload]


# ---------------------------------------------------------------- scoring helpers


def recompute_submission(submission: Submission) -> None:
    """Derive total score and overall status from per-question entries."""
    total = 0.0
    coding_pending = False
    needs_review = False
    for entry in submission.scores_json.values():
        total += entry.get("score") or 0.0
        if entry["status"] == "pending":
            if entry["type"] == "coding":
                coding_pending = True
            else:
                needs_review = True
        elif entry["status"] == "error":
            needs_review = True
    submission.score = round(total, 4)
    if coding_pending:
        submission.status = "evaluating"
    elif needs_review:
        submission.status = "pending_review"
    else:
        submission.status = "scored"


def set_entry(submission: Submission, question_id: UUID, entry: dict[str, Any]) -> None:
    scores = dict(submission.scores_json)
    scores[str(question_id)] = entry
    submission.scores_json = scores  # reassign so the JSON change is tracked


# ---------------------------------------------------------------- start / view


async def start_attempt(
    db: AsyncSession,
    queue: ExecutionQueueContract,
    user: User,
    assessment: Assessment,
) -> tuple[Attempt, bool, list[ExecutionJobPayload]]:
    """Returns (attempt, resumed, jobs_to_dispatch_after_commit)."""
    if assessment.status != "active":
        raise api_error(409, "NOT_ACTIVE", "This assessment is not currently active")

    enrolled = await db.scalar(
        select(AssessmentEnrollment.id).where(
            AssessmentEnrollment.assessment_id == assessment.id,
            AssessmentEnrollment.candidate_id == user.id,
        )
    )
    if enrolled is None:
        await audit.record(
            db,
            action="attempt.denied",
            resource_type="assessment",
            resource_id=str(assessment.id),
            actor_id=user.id,
            tenant_id=assessment.tenant_id,
            reason_code="NOT_ENROLLED",
        )
        await db.commit()
        raise api_error(403, "NOT_ENROLLED", "You are not enrolled in this assessment")

    version = await assessment_service.current_version(db, assessment.id)
    if not version.is_frozen or not await assessment_service.verify_version_integrity(db, version):
        await audit.record(
            db,
            action="integrity.violation",
            resource_type="assessment_version",
            resource_id=str(version.id),
            actor_id=user.id,
            tenant_id=assessment.tenant_id,
            reason_code="DIGEST_MISMATCH",
        )
        await db.commit()
        raise api_error(409, "INTEGRITY_ERROR", "Assessment integrity check failed")

    config = assessment_service.parse_config(version)
    now = utcnow()
    if config.closes_at is not None and now >= as_utc(config.closes_at):
        raise api_error(409, "ASSESSMENT_CLOSED", "The assessment window has closed")

    jobs: list[ExecutionJobPayload] = []
    open_attempt = await db.scalar(
        select(Attempt).where(
            Attempt.candidate_id == user.id,
            Attempt.assessment_version_id == version.id,
            Attempt.status == "in_progress",
        )
    )
    if open_attempt is not None:
        if now <= as_utc(open_attempt.deadline_at):
            return open_attempt, True, []
        result = await finalize_attempt(
            db, open_attempt, idempotency_key=f"auto-expire-{open_attempt.id}", final_status="expired"
        )
        jobs.extend(result.jobs)

    used = int(
        await db.scalar(
            select(func.count())
            .select_from(Attempt)
            .where(
                Attempt.candidate_id == user.id,
                Attempt.assessment_version_id == version.id,
            )
        )
        or 0
    )
    if used >= config.max_attempts:
        await db.commit()
        await dispatch_jobs(db, queue, jobs)
        raise api_error(409, "ATTEMPTS_EXHAUSTED", "No attempts remaining")

    deadline = now + timedelta(minutes=config.duration_minutes)
    if config.closes_at is not None:
        deadline = min(deadline, as_utc(config.closes_at))
    attempt = Attempt(
        id=uuid4(),
        tenant_id=assessment.tenant_id,
        assessment_version_id=version.id,
        candidate_id=user.id,
        status="in_progress",
        started_at=now,
        deadline_at=deadline,
    )
    db.add(attempt)
    await db.flush()
    await audit.record(
        db,
        action="attempt.start",
        resource_type="attempt",
        resource_id=str(attempt.id),
        actor_id=user.id,
        tenant_id=assessment.tenant_id,
    )
    return attempt, False, jobs


async def load_questions(db: AsyncSession, version_id: UUID) -> list[Question]:
    return await assessment_service.list_questions(db, version_id)


async def attempt_view(db: AsyncSession, attempt: Attempt) -> dict[str, Any]:
    questions = await load_questions(db, attempt.assessment_version_id)
    responses = (await db.scalars(select(Response).where(Response.attempt_id == attempt.id))).all()
    assessment_title = await db.scalar(
        select(Assessment.title)
        .join(AssessmentVersion, AssessmentVersion.assessment_id == Assessment.id)
        .where(AssessmentVersion.id == attempt.assessment_version_id)
    )
    now = utcnow()
    remaining = max(0, int((as_utc(attempt.deadline_at) - now).total_seconds()))
    return {
        "id": attempt.id,
        "status": attempt.status,
        "started_at": attempt.started_at,
        "deadline_at": attempt.deadline_at,
        "server_time": now,
        "remaining_seconds": remaining if attempt.status == "in_progress" else 0,
        "assessment_title": assessment_title,
        "questions": [assessment_service.candidate_question(q) for q in questions],
        "responses": {
            str(r.question_id): {
                "payload": r.payload_json,
                "client_seq": r.client_seq,
                "saved_at": r.saved_at,
            }
            for r in responses
        },
    }


# ---------------------------------------------------------------- autosave


def ensure_open(attempt: Attempt) -> None:
    if attempt.status != "in_progress":
        raise api_error(409, "ATTEMPT_CLOSED", "This attempt is no longer accepting changes")
    if utcnow() > as_utc(attempt.deadline_at):
        raise api_error(409, "DEADLINE_PASSED", "The attempt deadline has passed")


async def get_attempt_question(db: AsyncSession, attempt: Attempt, question_id: UUID) -> Question:
    question = await db.scalar(
        select(Question).where(
            Question.id == question_id,
            Question.assessment_version_id == attempt.assessment_version_id,
        )
    )
    if question is None:
        raise api_error(404, "NOT_FOUND", "Question not found")
    return question


async def save_response(
    db: AsyncSession,
    attempt: Attempt,
    question: Question,
    payload: dict[str, Any],
    client_seq: int,
) -> tuple[Response, bool]:
    """Durable autosave. Returns (response, applied). Stale/replayed seq is not applied."""
    ensure_open(attempt)
    try:
        normalized = get_module(question.question_type).validate_response(
            question.prompt_json, payload
        )
    except QuestionValidationError as exc:
        raise api_error(422, "INVALID_RESPONSE", str(exc)) from exc
    return await upsert_response(db, attempt, question, normalized, client_seq)


async def upsert_response(
    db: AsyncSession,
    attempt: Attempt,
    question: Question,
    normalized: dict[str, Any],
    client_seq: int,
) -> tuple[Response, bool]:
    existing = await db.scalar(
        select(Response).where(
            Response.attempt_id == attempt.id, Response.question_id == question.id
        )
    )
    if existing is None:
        response = Response(
            id=uuid4(),
            tenant_id=attempt.tenant_id,
            attempt_id=attempt.id,
            question_id=question.id,
            payload_json=normalized,
            idempotency_key=f"seq:{client_seq}",
            client_seq=client_seq,
        )
        db.add(response)
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise api_error(409, "CONCURRENT_SAVE", "Concurrent save; retry with a higher seq") from exc
        return response, True

    if client_seq < existing.client_seq:
        return existing, False  # stale/replayed older save: ignored
    if client_seq == existing.client_seq:
        if existing.payload_json != normalized:
            raise api_error(409, "SEQ_CONFLICT", "Same client_seq with a different payload")
        return existing, False  # idempotent retry
    existing.payload_json = normalized
    existing.client_seq = client_seq
    existing.idempotency_key = f"seq:{client_seq}"
    existing.saved_at = utcnow()
    await db.flush()
    return existing, True


# ---------------------------------------------------------------- submission


async def finalize_attempt(
    db: AsyncSession, attempt: Attempt, *, idempotency_key: str, final_status: str
) -> FinalizeResult:
    """Score saved responses and create the single submission for an attempt."""
    questions = await load_questions(db, attempt.assessment_version_id)
    responses = {
        r.question_id: r
        for r in (await db.scalars(select(Response).where(Response.attempt_id == attempt.id))).all()
    }
    submission = Submission(
        id=uuid4(),
        tenant_id=attempt.tenant_id,
        attempt_id=attempt.id,
        idempotency_key=idempotency_key,
        status="evaluating",
        score=0.0,
        scores_json={},
        submitted_at=utcnow(),
    )
    db.add(submission)
    attempt.status = final_status
    attempt.submitted_at = utcnow()
    await db.flush()

    jobs: list[ExecutionJobPayload] = []
    entries: dict[str, Any] = {}
    for q in questions:
        response = responses.get(q.id)
        if response is None:
            entries[str(q.id)] = {
                "score": 0.0,
                "status": "scored",
                "type": q.question_type,
                "answered": False,
            }
            continue
        result = get_module(q.question_type).evaluate(
            q.prompt_json, q.hidden_eval_json, response.payload_json, q.max_score
        )
        entry: dict[str, Any] = {
            "score": result.score,
            "status": result.status,
            "type": q.question_type,
            "answered": True,
        }
        entries[str(q.id)] = entry
        if q.question_type == "coding":
            job = ExecutionJob(
                id=uuid4(),
                tenant_id=attempt.tenant_id,
                submission_id=submission.id,
                question_id=q.id,
                language=response.payload_json["language"],
                priority_class="coding_standard",
                status="queued",
            )
            db.add(job)
            hidden = q.hidden_eval_json
            jobs.append(
                ExecutionJobPayload(
                    job_id=job.id,
                    tenant_id=attempt.tenant_id,
                    attempt_id=attempt.id,
                    question_id=q.id,
                    language=job.language,
                    priority_class="coding_standard",
                    cpu_time_limit_sec=hidden["cpu_time_limit_sec"],
                    memory_limit_mb=hidden["memory_limit_mb"],
                    source_code=response.payload_json["source_code"],
                    test_cases=[CodeTestCase(**tc) for tc in hidden["test_cases"]],
                )
            )
    submission.scores_json = entries
    recompute_submission(submission)
    await db.flush()
    await audit.record(
        db,
        action="attempt.submit" if final_status == "submitted" else "attempt.expire",
        resource_type="attempt",
        resource_id=str(attempt.id),
        actor_id=attempt.candidate_id,
        tenant_id=attempt.tenant_id,
        metadata={"submission_id": str(submission.id)},
    )
    return FinalizeResult(submission=submission, jobs=jobs)


async def _existing_submission(db: AsyncSession, attempt_id: UUID) -> Submission | None:
    return await db.scalar(select(Submission).where(Submission.attempt_id == attempt_id))


def _replay_or_conflict(existing: Submission, key: str) -> tuple[Submission, bool]:
    if existing.idempotency_key == key:
        return existing, False
    raise api_error(409, "ALREADY_SUBMITTED", "This attempt has already been submitted")


async def submit_attempt(
    db: AsyncSession, queue: ExecutionQueueContract, attempt: Attempt, key: str
) -> tuple[Submission, bool, list[ExecutionJobPayload]]:
    """Idempotent submit. Returns (submission, created, jobs_to_dispatch_after_commit)."""
    existing = await _existing_submission(db, attempt.id)
    if existing is not None:
        submission, _ = _replay_or_conflict(existing, key)
        return submission, False, []

    coding_count = await db.scalar(
        select(func.count())
        .select_from(Response)
        .join(Question, Question.id == Response.question_id)
        .where(Response.attempt_id == attempt.id, Question.question_type == "coding")
    )
    if coding_count and not await queue.has_capacity(int(coding_count)):
        raise api_error(503, "QUEUE_FULL", "Execution queue is full; retry shortly")

    late = utcnow() > as_utc(attempt.deadline_at)
    try:
        result = await finalize_attempt(
            db, attempt, idempotency_key=key, final_status="expired" if late else "submitted"
        )
    except IntegrityError:
        await db.rollback()
        existing = await _existing_submission(db, attempt.id)
        if existing is None:
            raise
        submission, _ = _replay_or_conflict(existing, key)
        return submission, False, []
    return result.submission, True, result.jobs


async def dispatch_jobs(
    db: AsyncSession, queue: ExecutionQueueContract, payloads: list[ExecutionJobPayload]
) -> None:
    """Push committed jobs to the bounded queue; mark any that cannot be queued as errored."""
    for payload in payloads:
        try:
            await queue.enqueue(payload)
        except QueueFullError:
            job = await db.get(ExecutionJob, payload.job_id)
            if job is not None:
                await apply_job_outcome(
                    db, job, status="failed", passed=0, total=1, error="QUEUE_FULL", worker_id=None
                )
    await db.commit()


# ---------------------------------------------------------------- execution results


async def apply_job_outcome(
    db: AsyncSession,
    job: ExecutionJob,
    *,
    status: str,
    passed: int,
    total: int,
    error: str | None,
    worker_id: str | None,
) -> None:
    submission = await db.get(Submission, job.submission_id)
    question = await db.get(Question, job.question_id)
    if submission is None or question is None:  # pragma: no cover - FK guarantees
        raise api_error(404, "NOT_FOUND", "Job context missing")

    job.status = status
    job.worker_id = worker_id
    job.completed_at = utcnow()
    job.result_json = {"passed": passed, "total": total, "error": error}

    if status == "failed":
        entry = {
            "score": 0.0,
            "status": "error",
            "type": "coding",
            "answered": True,
            "error": error or "EXECUTION_FAILED",
        }
    else:
        fraction = passed / total if total else 0.0
        entry = {
            "score": round(question.max_score * fraction, 4),
            "status": "scored",
            "type": "coding",
            "answered": True,
            "passed": passed,
            "total": total,
        }
    set_entry(submission, question.id, entry)
    recompute_submission(submission)
    await db.flush()
