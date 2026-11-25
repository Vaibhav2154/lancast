import asyncio
import re
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import api_error
from app.core.integrity import sha256_hex
from app.db.models import Attempt, Question, Response, UploadedFile
from app.services import attempts as attempt_service
from app.services.question_modules import QuestionValidationError
from app.services.question_modules.file_upload import (
    ALLOWED_EXTENSIONS,
    check_file_content,
    content_type_for,
)

_UNSAFE = re.compile(r"[^A-Za-z0-9._ -]")


def safe_display_name(filename: str | None) -> str:
    """Display-only name; never used to build filesystem paths (T10)."""
    base = (filename or "upload").replace("\\", "/").split("/")[-1]
    cleaned = _UNSAFE.sub("_", base).strip(" .") or "upload"
    return cleaned[:255]


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


async def store_upload(
    db: AsyncSession,
    settings: Settings,
    attempt: Attempt,
    question: Question,
    *,
    filename: str | None,
    data: bytes,
) -> UploadedFile:
    attempt_service.ensure_open(attempt)
    if question.question_type != "file_upload":
        raise api_error(422, "NOT_UPLOAD_QUESTION", "This question does not accept file uploads")

    prompt = question.prompt_json
    display = safe_display_name(filename)
    ext = _extension(display)
    if ext not in ALLOWED_EXTENSIONS or ext not in prompt["allowed_extensions"]:
        raise api_error(422, "FILE_TYPE_NOT_ALLOWED", f"Files of type .{ext or '?'} are not allowed")
    limit = min(prompt["max_size_bytes"], settings.max_upload_bytes)
    if len(data) > limit:
        raise api_error(413, "FILE_TOO_LARGE", f"File exceeds the {limit} byte limit")
    if not data:
        raise api_error(422, "EMPTY_FILE", "File is empty")
    try:
        check_file_content(ext, data)
    except QuestionValidationError as exc:
        raise api_error(422, "FILE_CONTENT_INVALID", str(exc)) from exc

    stored_name = f"{uuid4().hex}.{ext}"
    directory = Path(settings.upload_dir) / str(attempt.tenant_id) / str(attempt.id)

    def _write() -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / stored_name).write_bytes(data)

    await asyncio.to_thread(_write)

    # One file per question: replace (and remove) the previous upload.
    previous = (
        await db.scalars(
            select(UploadedFile).where(
                UploadedFile.attempt_id == attempt.id, UploadedFile.question_id == question.id
            )
        )
    ).all()
    for old in previous:
        await asyncio.to_thread(
            lambda name=old.stored_name: (directory / name).unlink(missing_ok=True)
        )
        await db.delete(old)

    record = UploadedFile(
        id=uuid4(),
        tenant_id=attempt.tenant_id,
        attempt_id=attempt.id,
        question_id=question.id,
        original_name=display,
        stored_name=stored_name,
        content_type=content_type_for(ext),
        size_bytes=len(data),
        sha256=sha256_hex(data),
    )
    db.add(record)
    await db.flush()
    return record


async def next_seq(db: AsyncSession, attempt_id: UUID, question_id: UUID) -> int:
    existing = await db.scalar(
        select(Response.client_seq).where(
            Response.attempt_id == attempt_id, Response.question_id == question_id
        )
    )
    return (existing or 0) + 1


def resolve_upload_path(settings: Settings, record: UploadedFile) -> Path:
    """Resolve and verify an uploaded file path inside settings.upload_dir."""
    root = Path(settings.upload_dir).resolve()
    path = (root / str(record.tenant_id) / str(record.attempt_id) / record.stored_name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise api_error(404, "FILE_MISSING", "Uploaded file is no longer available on disk")
    return path
