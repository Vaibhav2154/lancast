"""Assessment Capsule export/import (FR-CAP-01..05, T10)."""

import io
import json
import zipfile
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any

from pydantic import Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import api_error
from app.core.integrity import canonical_digest
from app.core.timeutil import utcnow
from app.db.models import Assessment, AssessmentVersion, Question, User
from app.schemas.assessments import AssessmentConfig
from app.services import assessments as assessment_service
from app.services import audit
from app.services.question_modules import QuestionValidationError, get_module
from app.services.question_modules.base import StrictModel

CAPSULE_SCHEMA_VERSION = 1
MANIFEST_NAME = "manifest.json"


class CapsuleQuestion(StrictModel):
    question_type: str
    position: int = Field(ge=1)
    prompt: dict[str, Any]
    hidden_eval: dict[str, Any]
    max_score: float = Field(gt=0, le=1000)


class CapsuleAssessment(StrictModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10000)
    config: AssessmentConfig


class CapsuleManifest(StrictModel):
    capsule_schema_version: int
    exported_at: datetime
    assessment: CapsuleAssessment
    questions: list[CapsuleQuestion] = Field(max_length=500)
    digest: str


def _digest(assessment: dict[str, Any], questions: list[dict[str, Any]]) -> str:
    return canonical_digest({"assessment": assessment, "questions": questions})


async def export_capsule(
    db: AsyncSession, actor: User, assessment: Assessment, version: AssessmentVersion
) -> bytes:
    """Metadata, questions and evaluation config only: no candidates, attempts or secrets."""
    questions = await assessment_service.list_questions(db, version.id)
    assessment_part = {
        "title": assessment.title,
        "description": assessment.description,
        "config": version.config_json,
    }
    question_parts = [
        {
            "question_type": q.question_type,
            "position": q.position,
            "prompt": q.prompt_json,
            "hidden_eval": q.hidden_eval_json,
            "max_score": float(q.max_score),
        }
        for q in questions
    ]
    manifest = {
        "capsule_schema_version": CAPSULE_SCHEMA_VERSION,
        "exported_at": utcnow().isoformat(),
        "assessment": assessment_part,
        "questions": question_parts,
        "digest": _digest(assessment_part, question_parts),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2))
    await audit.record(
        db,
        action="capsule.export",
        resource_type="assessment",
        resource_id=str(assessment.id),
        actor_id=actor.id,
        tenant_id=assessment.tenant_id,
    )
    return buffer.getvalue()


def _bad(code: str, message: str, status: int = 422):
    return api_error(status, code, message)


def parse_capsule(data: bytes, settings: Settings) -> CapsuleManifest:
    """Strictly validate an untrusted capsule archive before anything is created."""
    if len(data) > settings.capsule_max_compressed_bytes:
        raise _bad("CAPSULE_TOO_LARGE", "Capsule archive is too large", 413)
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise _bad("CAPSULE_INVALID", "Not a valid capsule archive") from exc

    with zf:
        infos = zf.infolist()
        if len(infos) > settings.capsule_max_entries:
            raise _bad("CAPSULE_INVALID", "Capsule contains too many entries")
        total = 0
        for info in infos:
            name = info.filename
            path = PurePosixPath(name)
            if (
                name.startswith("/")
                or "\\" in name
                or ":" in name
                or ".." in path.parts
                or name != MANIFEST_NAME
            ):
                raise _bad("CAPSULE_INVALID", f"Unsupported or unsafe archive entry: {name!r}")
            total += info.file_size
        if total > settings.capsule_max_uncompressed_bytes:
            raise _bad("CAPSULE_TOO_LARGE", "Capsule expands beyond the allowed size", 413)
        if MANIFEST_NAME not in zf.namelist():
            raise _bad("CAPSULE_INVALID", "manifest.json is missing")
        # Bounded read guards against archives that lie about their declared size.
        with zf.open(MANIFEST_NAME) as fh:
            raw = fh.read(settings.capsule_max_uncompressed_bytes + 1)
        if len(raw) > settings.capsule_max_uncompressed_bytes:
            raise _bad("CAPSULE_TOO_LARGE", "Capsule expands beyond the allowed size", 413)

    try:
        manifest = CapsuleManifest.model_validate(json.loads(raw))
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
        raise _bad("CAPSULE_INVALID", "Capsule manifest is malformed") from exc

    if manifest.capsule_schema_version != CAPSULE_SCHEMA_VERSION:
        raise _bad("CAPSULE_VERSION", "Unsupported capsule schema version")
    expected = _digest(
        manifest.assessment.model_dump(mode="json"),
        [q.model_dump(mode="json") for q in manifest.questions],
    )
    if expected != manifest.digest:
        raise _bad("CAPSULE_INTEGRITY", "Capsule digest does not match its contents")
    return manifest


async def import_capsule(
    db: AsyncSession, actor: User, tenant_id, manifest: CapsuleManifest
) -> tuple[Assessment, AssessmentVersion]:
    """Always creates a NEW draft assessment; never overwrites (FR-CAP-05)."""
    normalized = []
    for q in manifest.questions:
        try:
            prompt, hidden = get_module(q.question_type).validate_definition(q.prompt, q.hidden_eval)
        except QuestionValidationError as exc:
            raise _bad("CAPSULE_INVALID", f"Question {q.position}: {exc}") from exc
        normalized.append((q, prompt, hidden))

    assessment, version = await assessment_service.create_assessment(
        db,
        actor,
        tenant_id,
        title=manifest.assessment.title,
        description=manifest.assessment.description,
        config=manifest.assessment.config,
    )
    for q, prompt, hidden in normalized:
        db.add(
            Question(
                tenant_id=tenant_id,
                assessment_version_id=version.id,
                question_type=q.question_type,
                position=q.position,
                prompt_json=prompt,
                hidden_eval_json=hidden,
                max_score=q.max_score,
            )
        )
    await db.flush()
    await audit.record(
        db,
        action="capsule.import",
        resource_type="assessment",
        resource_id=str(assessment.id),
        actor_id=actor.id,
        tenant_id=tenant_id,
        metadata={"questions": len(normalized)},
    )
    return assessment, version
