from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import api_error
from app.core.integrity import canonical_digest
from app.core.timeutil import utcnow
from app.db.models import (
    Assessment,
    AssessmentEnrollment,
    AssessmentVersion,
    Membership,
    Question,
    User,
)
from app.schemas.assessments import AssessmentConfig
from app.services import audit
from app.services.question_modules import QuestionValidationError, get_module

LIFECYCLE: dict[str, set[str]] = {
    "draft": {"published", "archived"},
    "published": {"active", "archived"},
    "active": {"closed"},
    "closed": {"archived"},
    "archived": set(),
}


def question_validation_http(exc: QuestionValidationError):
    return api_error(422, "INVALID_QUESTION", str(exc))


async def get_assessment(db: AsyncSession, tenant_id: UUID, assessment_id: UUID) -> Assessment:
    """Always scoped by tenant: an id from another tenant is simply not found."""
    assessment = await db.scalar(
        select(Assessment).where(Assessment.id == assessment_id, Assessment.tenant_id == tenant_id)
    )
    if assessment is None:
        raise api_error(404, "NOT_FOUND", "Assessment not found")
    return assessment


async def current_version(db: AsyncSession, assessment_id: UUID) -> AssessmentVersion:
    version = await db.scalar(
        select(AssessmentVersion)
        .where(AssessmentVersion.assessment_id == assessment_id)
        .order_by(AssessmentVersion.version_number.desc())
        .limit(1)
    )
    if version is None:  # pragma: no cover - created together with the assessment
        raise api_error(500, "NO_VERSION", "Assessment has no version")
    return version


async def list_questions(db: AsyncSession, version_id: UUID) -> list[Question]:
    return list(
        (
            await db.scalars(
                select(Question)
                .where(Question.assessment_version_id == version_id)
                .order_by(Question.position)
            )
        ).all()
    )


def version_digest(version: AssessmentVersion, questions: list[Question]) -> str:
    """Canonical digest over frozen configuration + questions (FR-SEC-09)."""
    payload = {
        "config": version.config_json,
        "questions": [
            {
                "type": q.question_type,
                "position": q.position,
                "prompt": q.prompt_json,
                "hidden": q.hidden_eval_json,
                "max_score": float(q.max_score),
            }
            for q in sorted(questions, key=lambda x: x.position)
        ],
    }
    return canonical_digest(payload)


async def verify_version_integrity(db: AsyncSession, version: AssessmentVersion) -> bool:
    questions = await list_questions(db, version.id)
    return version_digest(version, questions) == version.canonical_digest


def organizer_question(q: Question) -> dict[str, Any]:
    return {
        "id": q.id,
        "question_type": q.question_type,
        "position": q.position,
        "prompt": q.prompt_json,
        "hidden_eval": q.hidden_eval_json,
        "max_score": q.max_score,
    }


def candidate_question(q: Question) -> dict[str, Any]:
    """Candidate-safe projection: hidden answers/tests never leave the server (FR-MOD-05)."""
    module = get_module(q.question_type)
    return {
        "id": q.id,
        "question_type": q.question_type,
        "position": q.position,
        "prompt": module.sanitize_for_candidate(q.prompt_json),
        "max_score": q.max_score,
    }


def summary(
    assessment: Assessment, version: AssessmentVersion, question_count: int | None = None
) -> dict[str, Any]:
    return {
        "id": assessment.id,
        "tenant_id": assessment.tenant_id,
        "title": assessment.title,
        "description": assessment.description,
        "status": assessment.status,
        "created_at": assessment.created_at,
        "version_number": version.version_number,
        "is_frozen": version.is_frozen,
        "canonical_digest": version.canonical_digest or None,
        "config": version.config_json,
        "question_count": question_count,
    }


async def create_assessment(
    db: AsyncSession,
    actor: User,
    tenant_id: UUID,
    *,
    title: str,
    description: str,
    config: AssessmentConfig,
) -> tuple[Assessment, AssessmentVersion]:
    assessment = Assessment(
        id=uuid4(),
        tenant_id=tenant_id,
        title=title.strip(),
        description=description,
        status="draft",
        created_by=actor.id,
    )
    db.add(assessment)
    await db.flush()
    version = AssessmentVersion(
        id=uuid4(),
        tenant_id=tenant_id,
        assessment_id=assessment.id,
        version_number=1,
        config_json=config.model_dump(mode="json"),
        canonical_digest="",
        is_frozen=False,
    )
    db.add(version)
    await db.flush()
    await audit.record(
        db,
        action="assessment.create",
        resource_type="assessment",
        resource_id=str(assessment.id),
        actor_id=actor.id,
        tenant_id=tenant_id,
    )
    return assessment, version


def _require_editable(assessment: Assessment, version: AssessmentVersion) -> None:
    if version.is_frozen or assessment.status != "draft":
        raise api_error(
            409, "VERSION_FROZEN", "Published assessments are frozen and cannot be edited"
        )


async def update_assessment(
    db: AsyncSession,
    assessment: Assessment,
    version: AssessmentVersion,
    *,
    title: str | None,
    description: str | None,
    config: AssessmentConfig | None,
) -> None:
    _require_editable(assessment, version)
    if title is not None:
        assessment.title = title.strip()
    if description is not None:
        assessment.description = description
    if config is not None:
        version.config_json = config.model_dump(mode="json")
    await db.flush()


async def add_question(
    db: AsyncSession,
    assessment: Assessment,
    version: AssessmentVersion,
    *,
    question_type: str,
    prompt: dict[str, Any],
    hidden: dict[str, Any],
    max_score: float,
    position: int | None,
) -> Question:
    _require_editable(assessment, version)
    try:
        module = get_module(question_type)
        prompt_n, hidden_n = module.validate_definition(prompt, hidden)
    except QuestionValidationError as exc:
        raise question_validation_http(exc) from exc
    if position is None:
        position = 1 + int(
            await db.scalar(
                select(func.coalesce(func.max(Question.position), 0)).where(
                    Question.assessment_version_id == version.id
                )
            )
            or 0
        )
    question = Question(
        id=uuid4(),
        tenant_id=assessment.tenant_id,
        assessment_version_id=version.id,
        question_type=question_type,
        position=position,
        prompt_json=prompt_n,
        hidden_eval_json=hidden_n,
        max_score=max_score,
    )
    db.add(question)
    await db.flush()
    return question


async def get_question(db: AsyncSession, version: AssessmentVersion, question_id: UUID) -> Question:
    question = await db.scalar(
        select(Question).where(
            Question.id == question_id, Question.assessment_version_id == version.id
        )
    )
    if question is None:
        raise api_error(404, "NOT_FOUND", "Question not found")
    return question


async def update_question(
    db: AsyncSession,
    assessment: Assessment,
    version: AssessmentVersion,
    question: Question,
    *,
    prompt: dict[str, Any] | None,
    hidden: dict[str, Any] | None,
    max_score: float | None,
) -> None:
    _require_editable(assessment, version)
    try:
        module = get_module(question.question_type)
        prompt_n, hidden_n = module.validate_definition(
            prompt if prompt is not None else question.prompt_json,
            hidden if hidden is not None else question.hidden_eval_json,
        )
    except QuestionValidationError as exc:
        raise question_validation_http(exc) from exc
    question.prompt_json = prompt_n
    question.hidden_eval_json = hidden_n
    if max_score is not None:
        question.max_score = max_score
    await db.flush()


async def delete_question(
    db: AsyncSession, assessment: Assessment, version: AssessmentVersion, question: Question
) -> None:
    _require_editable(assessment, version)
    await db.delete(question)
    await db.flush()


def _transition(assessment: Assessment, target: str) -> None:
    if target not in LIFECYCLE[assessment.status]:
        raise api_error(
            409,
            "INVALID_TRANSITION",
            f"Cannot move assessment from '{assessment.status}' to '{target}'",
        )
    assessment.status = target


async def publish(
    db: AsyncSession, actor: User, assessment: Assessment, version: AssessmentVersion
) -> None:
    """Freeze configuration, compute the canonical digest, publish (FR-AS-03)."""
    if assessment.status != "draft":
        _transition(assessment, "published")  # raises INVALID_TRANSITION
    questions = await list_questions(db, version.id)
    if not questions:
        raise api_error(422, "NO_QUESTIONS", "Add at least one question before publishing")
    _transition(assessment, "published")
    version.canonical_digest = version_digest(version, questions)
    version.is_frozen = True
    version.published_at = utcnow()
    await db.flush()
    await audit.record(
        db,
        action="assessment.publish",
        resource_type="assessment",
        resource_id=str(assessment.id),
        actor_id=actor.id,
        tenant_id=assessment.tenant_id,
        metadata={"digest": version.canonical_digest, "version": version.version_number},
    )


async def change_status(db: AsyncSession, actor: User, assessment: Assessment, target: str) -> None:
    _transition(assessment, target)
    await db.flush()
    await audit.record(
        db,
        action=f"assessment.{target}",
        resource_type="assessment",
        resource_id=str(assessment.id),
        actor_id=actor.id,
        tenant_id=assessment.tenant_id,
    )


async def enroll_candidates(
    db: AsyncSession, actor: User, assessment: Assessment, emails: list[str]
) -> list[str]:
    """All-or-nothing: every email must be a candidate member of this tenant."""
    normalized = sorted({e.strip().lower() for e in emails})
    rows = await db.execute(
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.tenant_id == assessment.tenant_id, User.email.in_(normalized))
    )
    by_email = {u.email: (u, m) for u, m in rows.all()}
    invalid = [e for e in normalized if e not in by_email or by_email[e][1].role != "candidate"]
    if invalid:
        raise api_error(
            422,
            "INVALID_CANDIDATES",
            "These emails are not candidate members of this tenant: " + ", ".join(invalid),
        )
    existing = set(
        (
            await db.scalars(
                select(AssessmentEnrollment.candidate_id).where(
                    AssessmentEnrollment.assessment_id == assessment.id
                )
            )
        ).all()
    )
    added = []
    for email in normalized:
        user = by_email[email][0]
        if user.id in existing:
            continue
        db.add(
            AssessmentEnrollment(
                id=uuid4(),
                tenant_id=assessment.tenant_id,
                assessment_id=assessment.id,
                candidate_id=user.id,
            )
        )
        added.append(email)
    await db.flush()
    await audit.record(
        db,
        action="assessment.enroll",
        resource_type="assessment",
        resource_id=str(assessment.id),
        actor_id=actor.id,
        tenant_id=assessment.tenant_id,
        metadata={"added": len(added)},
    )
    return added


async def list_enrollments(db: AsyncSession, assessment: Assessment) -> list[User]:
    rows = await db.scalars(
        select(User)
        .join(AssessmentEnrollment, AssessmentEnrollment.candidate_id == User.id)
        .where(AssessmentEnrollment.assessment_id == assessment.id)
        .order_by(User.email)
    )
    return list(rows.all())


def parse_config(version: AssessmentVersion) -> AssessmentConfig:
    return AssessmentConfig.model_validate(version.config_json)


def closes_at(version: AssessmentVersion) -> datetime | None:
    return parse_config(version).closes_at
