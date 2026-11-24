from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Response, UploadFile

from app.core.deps import AppSettings, DbSession, OrganizerCtx
from app.schemas.assessments import AssessmentOut
from app.services import assessments as assessment_svc
from app.services import capsules

router = APIRouter(prefix="/api/tenants/{tenant_id}", tags=["capsules"])


@router.get("/assessments/{assessment_id}/capsule")
async def export_capsule(assessment_id: UUID, ctx: OrganizerCtx, db: DbSession) -> Response:
    assessment = await assessment_svc.get_assessment(db, ctx.tenant_id, assessment_id)
    version = await assessment_svc.current_version(db, assessment.id)
    content = await capsules.export_capsule(db, ctx.user, assessment, version)
    await db.commit()
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="capsule-{assessment.id}.zip"'},
    )


@router.post("/capsules/import", response_model=AssessmentOut, status_code=201)
async def import_capsule(
    ctx: OrganizerCtx,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
) -> dict:
    data = await file.read(settings.capsule_max_compressed_bytes + 1)
    manifest = capsules.parse_capsule(data, settings)
    assessment, version = await capsules.import_capsule(db, ctx.user, ctx.tenant_id, manifest)
    await db.commit()
    return assessment_svc.summary(assessment, version, len(manifest.questions))
