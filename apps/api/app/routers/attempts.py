from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, Response, UploadFile
from sqlalchemy import select

from app.contracts.interfaces import ExecutionQueueContract
from app.core.deps import (
    ORGANIZER_ROLES,
    ROLE_CANDIDATE,
    AppSettings,
    CandidateCtx,
    CurrentPrincipal,
    DbSession,
    Principal,
    deny,
)
from app.core.errors import api_error
from app.db.models import Assessment, AssessmentEnrollment, Attempt, Membership
from app.schemas.attempts import (
    AttemptOut,
    MyAssessmentOut,
    ResponseSave,
    SavedResponseOut,
    SubmissionOut,
    UploadOut,
)
from app.services import assessments as assessment_svc
from app.services import attempts as svc
from app.services import uploads
from app.services.execution_queue import get_execution_queue

router = APIRouter(prefix="/api", tags=["attempts"])
QueueDep = Annotated[ExecutionQueueContract, Depends(get_execution_queue)]


async def _load_attempt(
    attempt_id: UUID, principal: Principal, db: DbSession, *, owner_only: bool
) -> Attempt:
    """Object-level access: owners always; organizers of the tenant may read. Else 404 + audit."""
    attempt = await db.get(Attempt, attempt_id)
    if attempt is None:
        raise api_error(404, "NOT_FOUND", "Attempt not found")
    membership = await db.scalar(
        select(Membership).where(
            Membership.tenant_id == attempt.tenant_id, Membership.user_id == principal.user.id
        )
    )
    is_owner = attempt.candidate_id == principal.user.id and (
        membership is not None and membership.role == ROLE_CANDIDATE
    )
    is_reader = not owner_only and membership is not None and membership.role in ORGANIZER_ROLES
    if not (is_owner or is_reader):
        await deny(
            db,
            user=principal.user,
            tenant_id=attempt.tenant_id,
            resource_type="attempt",
            resource_id=str(attempt.id),
            reason_code="NOT_OWNER" if membership else "NOT_MEMBER",
            status_code=404,
        )
    return attempt


async def _owned_attempt(attempt_id: UUID, principal: CurrentPrincipal, db: DbSession) -> Attempt:
    return await _load_attempt(attempt_id, principal, db, owner_only=True)


async def _viewable_attempt(
    attempt_id: UUID, principal: CurrentPrincipal, db: DbSession
) -> Attempt:
    return await _load_attempt(attempt_id, principal, db, owner_only=False)


OwnedAttempt = Annotated[Attempt, Depends(_owned_attempt)]
ViewableAttempt = Annotated[Attempt, Depends(_viewable_attempt)]


@router.get("/me/assessments", response_model=list[MyAssessmentOut])
async def my_assessments(principal: CurrentPrincipal, db: DbSession) -> list[dict]:
    rows = await db.execute(
        select(Assessment)
        .join(AssessmentEnrollment, AssessmentEnrollment.assessment_id == Assessment.id)
        .where(
            AssessmentEnrollment.candidate_id == principal.user.id, Assessment.status == "active"
        )
        .order_by(Assessment.title)
    )
    return [
        {
            "tenant_id": a.tenant_id,
            "assessment_id": a.id,
            "title": a.title,
            "description": a.description,
        }
        for a in rows.scalars().all()
    ]


@router.post(
    "/tenants/{tenant_id}/assessments/{assessment_id}/attempts",
    response_model=AttemptOut,
    status_code=201,
)
async def start_attempt(
    assessment_id: UUID,
    ctx: CandidateCtx,
    db: DbSession,
    queue: QueueDep,
    response: Response,
) -> dict:
    assessment = await assessment_svc.get_assessment(db, ctx.tenant_id, assessment_id)
    attempt, resumed, jobs = await svc.start_attempt(db, queue, ctx.user, assessment)
    await db.commit()
    await svc.dispatch_jobs(db, queue, jobs)
    if resumed:
        response.status_code = 200
    view = await svc.attempt_view(db, attempt)
    view["resumed"] = resumed
    return view


@router.get("/attempts/{attempt_id}", response_model=AttemptOut)
async def get_attempt(attempt: ViewableAttempt, db: DbSession) -> dict:
    return await svc.attempt_view(db, attempt)


@router.put("/attempts/{attempt_id}/responses/{question_id}", response_model=SavedResponseOut)
async def save_response(
    question_id: UUID,
    body: ResponseSave,
    attempt: OwnedAttempt,
    db: DbSession,
) -> SavedResponseOut:
    question = await svc.get_attempt_question(db, attempt, question_id)
    saved, applied = await svc.save_response(db, attempt, question, body.payload, body.client_seq)
    await db.commit()
    return SavedResponseOut(
        question_id=question_id,
        applied=applied,
        client_seq=saved.client_seq,
        saved_at=saved.saved_at,
    )


@router.post("/attempts/{attempt_id}/submit", response_model=SubmissionOut)
async def submit(
    attempt: OwnedAttempt,
    db: DbSession,
    queue: QueueDep,
    response: Response,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
) -> SubmissionOut:
    submission, created, jobs = await svc.submit_attempt(db, queue, attempt, idempotency_key)
    await db.commit()
    if created:
        await svc.dispatch_jobs(db, queue, jobs)
        await db.refresh(submission)
    response.status_code = 201 if created else 200
    return SubmissionOut(
        id=submission.id,
        attempt_id=submission.attempt_id,
        status=submission.status,
        score=submission.score,
        submitted_at=submission.submitted_at,
        replayed=not created,
    )


@router.post("/attempts/{attempt_id}/questions/{question_id}/upload", response_model=UploadOut)
async def upload_file(
    question_id: UUID,
    attempt: OwnedAttempt,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
) -> UploadOut:
    question = await svc.get_attempt_question(db, attempt, question_id)
    data = await file.read(settings.max_upload_bytes + 1)
    record = await uploads.store_upload(
        db, settings, attempt, question, filename=file.filename, data=data
    )
    seq = await uploads.next_seq(db, attempt.id, question.id)
    await svc.upsert_response(
        db,
        attempt,
        question,
        {
            "file_id": str(record.id),
            "original_name": record.original_name,
            "size_bytes": record.size_bytes,
            "sha256": record.sha256,
        },
        seq,
    )
    await db.commit()
    return UploadOut(
        file_id=record.id,
        original_name=record.original_name,
        size_bytes=record.size_bytes,
        sha256=record.sha256,
    )
