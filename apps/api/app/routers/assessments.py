import csv
import io
import re
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import Response as FastAPIResponse
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.contracts.interfaces import ExecutionQueueContract
from app.core.deps import AppSettings, DbSession, OrganizerCtx
from app.core.errors import api_error
from app.db.models import (
    Assessment,
    AssessmentVersion,
    Attempt,
    Question,
    Submission,
    UploadedFile,
    User,
)
from app.db.models import Response as AttemptResponse
from app.schemas.assessments import (
    AssessmentCreate,
    AssessmentDetailOut,
    AssessmentOut,
    AssessmentUpdate,
    CandidateQuestionOut,
    EnrollmentOut,
    EnrollRequest,
    EnrollResult,
    GradeRequest,
    OrganizerQuestionOut,
    PreviewOut,
    QuestionCreate,
    QuestionUpdate,
    ResultRow,
)
from app.services import assessments as svc
from app.services import attempts as attempt_svc
from app.services import audit, uploads
from app.services.execution_queue import get_execution_queue

router = APIRouter(prefix="/api/tenants/{tenant_id}/assessments", tags=["assessments"])
QueueDep = Annotated[ExecutionQueueContract, Depends(get_execution_queue)]


async def _load(db: DbSession, ctx: OrganizerCtx, assessment_id: UUID):
    assessment = await svc.get_assessment(db, ctx.tenant_id, assessment_id)
    version = await svc.current_version(db, assessment.id)
    return assessment, version


async def _detail(db: DbSession, assessment: Assessment, version: AssessmentVersion) -> dict:
    questions = await svc.list_questions(db, version.id)
    data = svc.summary(assessment, version, len(questions))
    data["questions"] = [svc.organizer_question(q) for q in questions]
    return data


@router.post("", response_model=AssessmentOut, status_code=201)
async def create_assessment(body: AssessmentCreate, ctx: OrganizerCtx, db: DbSession) -> dict:
    assessment, version = await svc.create_assessment(
        db,
        ctx.user,
        ctx.tenant_id,
        title=body.title,
        description=body.description,
        config=body.config,
    )
    await db.commit()
    return svc.summary(assessment, version, 0)


@router.get("", response_model=list[AssessmentOut])
async def list_assessments(ctx: OrganizerCtx, db: DbSession) -> list[dict]:
    assessments = (
        await db.scalars(
            select(Assessment)
            .where(Assessment.tenant_id == ctx.tenant_id)
            .order_by(Assessment.created_at.desc())
        )
    ).all()
    out = []
    for a in assessments:
        out.append(svc.summary(a, await svc.current_version(db, a.id)))
    return out


@router.get("/{assessment_id}", response_model=AssessmentDetailOut)
async def get_assessment(assessment_id: UUID, ctx: OrganizerCtx, db: DbSession) -> dict:
    assessment, version = await _load(db, ctx, assessment_id)
    return await _detail(db, assessment, version)


@router.patch("/{assessment_id}", response_model=AssessmentOut)
async def update_assessment(
    assessment_id: UUID, body: AssessmentUpdate, ctx: OrganizerCtx, db: DbSession
) -> dict:
    assessment, version = await _load(db, ctx, assessment_id)
    await svc.update_assessment(
        db,
        assessment,
        version,
        title=body.title,
        description=body.description,
        config=body.config,
    )
    await db.commit()
    return svc.summary(assessment, version)


@router.post("/{assessment_id}/questions", response_model=OrganizerQuestionOut, status_code=201)
async def add_question(
    assessment_id: UUID, body: QuestionCreate, ctx: OrganizerCtx, db: DbSession
) -> dict:
    assessment, version = await _load(db, ctx, assessment_id)
    question = await svc.add_question(
        db,
        assessment,
        version,
        question_type=body.question_type,
        prompt=body.prompt,
        hidden=body.hidden_eval,
        max_score=body.max_score,
        position=body.position,
    )
    await db.commit()
    return svc.organizer_question(question)


@router.put("/{assessment_id}/questions/{question_id}", response_model=OrganizerQuestionOut)
async def update_question(
    assessment_id: UUID,
    question_id: UUID,
    body: QuestionUpdate,
    ctx: OrganizerCtx,
    db: DbSession,
) -> dict:
    assessment, version = await _load(db, ctx, assessment_id)
    question = await svc.get_question(db, version, question_id)
    await svc.update_question(
        db,
        assessment,
        version,
        question,
        prompt=body.prompt,
        hidden=body.hidden_eval,
        max_score=body.max_score,
    )
    await db.commit()
    return svc.organizer_question(question)


@router.delete("/{assessment_id}/questions/{question_id}", status_code=204)
async def delete_question(
    assessment_id: UUID, question_id: UUID, ctx: OrganizerCtx, db: DbSession
) -> None:
    assessment, version = await _load(db, ctx, assessment_id)
    question = await svc.get_question(db, version, question_id)
    await svc.delete_question(db, assessment, version, question)
    await db.commit()


@router.get("/{assessment_id}/preview", response_model=PreviewOut)
async def preview(assessment_id: UUID, ctx: OrganizerCtx, db: DbSession) -> dict:
    """Exactly what a candidate would see (no hidden answers/tests)."""
    assessment, version = await _load(db, ctx, assessment_id)
    questions = await svc.list_questions(db, version.id)
    return {
        "assessment_id": assessment.id,
        "title": assessment.title,
        "questions": [CandidateQuestionOut(**svc.candidate_question(q)) for q in questions],
    }


@router.post("/{assessment_id}/publish", response_model=AssessmentOut)
async def publish(assessment_id: UUID, ctx: OrganizerCtx, db: DbSession) -> dict:
    assessment, version = await _load(db, ctx, assessment_id)
    await svc.publish(db, ctx.user, assessment, version)
    await db.commit()
    return svc.summary(assessment, version)


@router.post("/{assessment_id}/start", response_model=AssessmentOut)
async def start(assessment_id: UUID, ctx: OrganizerCtx, db: DbSession) -> dict:
    assessment, version = await _load(db, ctx, assessment_id)
    await svc.change_status(db, ctx.user, assessment, "active")
    await db.commit()
    return svc.summary(assessment, version)


@router.post("/{assessment_id}/close", response_model=AssessmentOut)
async def close(
    assessment_id: UUID, ctx: OrganizerCtx, db: DbSession, queue: QueueDep
) -> dict:
    """Closing ends the event: in-progress attempts are finalized from saved responses."""
    assessment, version = await _load(db, ctx, assessment_id)
    await svc.change_status(db, ctx.user, assessment, "closed")
    open_attempts = (
        await db.scalars(
            select(Attempt).where(
                Attempt.assessment_version_id == version.id, Attempt.status == "in_progress"
            )
        )
    ).all()
    jobs = []
    for attempt in open_attempts:
        result = await attempt_svc.finalize_attempt(
            db, attempt, idempotency_key=f"auto-close-{attempt.id}", final_status="expired"
        )
        jobs.extend(result.jobs)
    await db.commit()
    await attempt_svc.dispatch_jobs(db, queue, jobs)
    return svc.summary(assessment, version)


@router.post("/{assessment_id}/archive", response_model=AssessmentOut)
async def archive(assessment_id: UUID, ctx: OrganizerCtx, db: DbSession) -> dict:
    assessment, version = await _load(db, ctx, assessment_id)
    await svc.change_status(db, ctx.user, assessment, "archived")
    await db.commit()
    return svc.summary(assessment, version)


@router.post("/{assessment_id}/enrollments", response_model=EnrollResult, status_code=201)
async def enroll(
    assessment_id: UUID, body: EnrollRequest, ctx: OrganizerCtx, db: DbSession
) -> dict:
    assessment, _ = await _load(db, ctx, assessment_id)
    added = await svc.enroll_candidates(db, ctx.user, assessment, [str(e) for e in body.emails])
    await db.commit()
    return {"added": added}


@router.get("/{assessment_id}/enrollments", response_model=list[EnrollmentOut])
async def list_enrollments(assessment_id: UUID, ctx: OrganizerCtx, db: DbSession) -> list[dict]:
    assessment, _ = await _load(db, ctx, assessment_id)
    users = await svc.list_enrollments(db, assessment)
    return [{"email": u.email, "full_name": u.full_name} for u in users]


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    text = value.isoformat() if hasattr(value, "isoformat") else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{text}"
    return text


def _safe_slug(text: str, fallback: str = "assessment") -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-").lower()
    return slug[:80] or fallback


@router.get("/{assessment_id}/results", response_model=list[ResultRow])
async def results(assessment_id: UUID, ctx: OrganizerCtx, db: DbSession) -> list[dict]:
    assessment, _ = await _load(db, ctx, assessment_id)
    rows = (
        await db.execute(
            select(Attempt, User.email, Submission)
            .join(User, User.id == Attempt.candidate_id)
            .join(AssessmentVersion, AssessmentVersion.id == Attempt.assessment_version_id)
            .outerjoin(Submission, Submission.attempt_id == Attempt.id)
            .where(
                AssessmentVersion.assessment_id == assessment.id, Attempt.tenant_id == ctx.tenant_id
            )
            .order_by(Attempt.started_at)
        )
    ).all()

    attempt_ids = [attempt.id for attempt, _, _ in rows]
    responses_by_attempt: dict[UUID, dict[str, dict[str, Any]]] = {}
    if attempt_ids:
        saved = (
            await db.scalars(
                select(AttemptResponse).where(AttemptResponse.attempt_id.in_(attempt_ids))
            )
        ).all()
        for resp in saved:
            responses_by_attempt.setdefault(resp.attempt_id, {})[str(resp.question_id)] = (
                resp.payload_json
            )

    out = []
    for attempt, email, submission in rows:
        out.append(
            {
                "attempt_id": attempt.id,
                "candidate_email": email,
                "attempt_status": attempt.status,
                "started_at": attempt.started_at,
                "submitted_at": attempt.submitted_at,
                "submission_id": submission.id if submission else None,
                "submission_status": submission.status if submission else None,
                "score": submission.score if submission else None,
                "scores": submission.scores_json if submission else {},
                "responses": responses_by_attempt.get(attempt.id, {}),
            }
        )
    return out


@router.get("/{assessment_id}/results/export")
async def export_results_csv(
    assessment_id: UUID, ctx: OrganizerCtx, db: DbSession
) -> FastAPIResponse:
    """Export all attempts and per-question scores for an assessment as RFC 4180 CSV."""
    assessment, version = await _load(db, ctx, assessment_id)
    questions = await svc.list_questions(db, version.id)
    max_score = round(sum(q.max_score for q in questions), 4)

    rows = (
        await db.execute(
            select(Attempt, User.email, User.full_name, Submission)
            .join(User, User.id == Attempt.candidate_id)
            .join(AssessmentVersion, AssessmentVersion.id == Attempt.assessment_version_id)
            .outerjoin(Submission, Submission.attempt_id == Attempt.id)
            .where(
                AssessmentVersion.assessment_id == assessment.id, Attempt.tenant_id == ctx.tenant_id
            )
            .order_by(Attempt.started_at)
        )
    ).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "candidate_email",
            "candidate_name",
            "attempt_id",
            "attempt_status",
            "started_at",
            "submitted_at",
            "submission_status",
            "total_score",
            "max_score",
            *[f"Q{q.position} ({q.question_type}, max {q.max_score})" for q in questions],
        ]
    )
    for attempt, email, full_name, submission in rows:
        scores_map = submission.scores_json if submission else {}
        writer.writerow(
            [
                _csv_cell(email),
                _csv_cell(full_name),
                _csv_cell(attempt.id),
                _csv_cell(attempt.status),
                _csv_cell(attempt.started_at),
                _csv_cell(attempt.submitted_at),
                _csv_cell(submission.status if submission else "not_submitted"),
                _csv_cell(submission.score if submission else ""),
                _csv_cell(max_score),
                *[
                    _csv_cell(
                        scores_map.get(str(q.id), {}).get("score")
                        if isinstance(scores_map, dict)
                        else ""
                    )
                    for q in questions
                ],
            ]
        )

    slug = _safe_slug(assessment.title)
    return FastAPIResponse(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{slug}-results.csv"',
            "X-Content-Type-Options": "nosniff",
        },
    )


grading_router = APIRouter(prefix="/api/tenants/{tenant_id}/submissions", tags=["grading"])


@grading_router.put("/{submission_id}/grades")
async def grade(
    submission_id: UUID, body: GradeRequest, ctx: OrganizerCtx, db: DbSession
) -> dict[str, Any]:
    """Manual grading hook for descriptive / file-upload answers."""
    submission = await db.scalar(
        select(Submission).where(
            Submission.id == submission_id, Submission.tenant_id == ctx.tenant_id
        )
    )
    if submission is None:
        raise api_error(404, "NOT_FOUND", "Submission not found")
    question = await db.get(Question, body.question_id)
    entry = submission.scores_json.get(str(body.question_id))
    if question is None or entry is None or question.tenant_id != ctx.tenant_id:
        raise api_error(404, "NOT_FOUND", "Question not part of this submission")
    if entry["type"] == "coding":
        raise api_error(409, "AUTO_GRADED", "Coding answers are graded by the execution worker")
    if body.score > question.max_score:
        raise api_error(422, "SCORE_TOO_HIGH", f"Score cannot exceed {question.max_score}")
    attempt_svc.set_entry(
        submission,
        question.id,
        {**entry, "score": body.score, "status": "scored", "graded_by": str(ctx.user.id)},
    )
    attempt_svc.recompute_submission(submission)
    await audit.record(
        db,
        action="submission.grade",
        resource_type="submission",
        resource_id=str(submission.id),
        actor_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        metadata={"question_id": str(question.id), "score": body.score},
    )
    await db.commit()
    return {"submission_id": submission.id, "status": submission.status, "score": submission.score}


uploads_router = APIRouter(prefix="/api/tenants/{tenant_id}/uploads", tags=["uploads"])


@uploads_router.get("/{file_id}")
async def download_upload(
    file_id: UUID, ctx: OrganizerCtx, db: DbSession, settings: AppSettings
) -> FileResponse:
    """Download a candidate-uploaded file within the organizer's tenant."""
    record = await db.scalar(
        select(UploadedFile).where(
            UploadedFile.id == file_id, UploadedFile.tenant_id == ctx.tenant_id
        )
    )
    if record is None:
        raise api_error(404, "NOT_FOUND", "Uploaded file not found")
    path = uploads.resolve_upload_path(settings, record)
    await audit.record(
        db,
        action="upload.download",
        resource_type="uploaded_file",
        resource_id=str(record.id),
        actor_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        metadata={"attempt_id": str(record.attempt_id), "question_id": str(record.question_id)},
    )
    await db.commit()
    safe_name = re.sub(r'["\r\n\\]', "_", record.original_name)
    return FileResponse(
        path=path,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
