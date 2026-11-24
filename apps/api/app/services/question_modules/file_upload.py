from typing import Any

from pydantic import Field

from app.services.question_modules.base import (
    EvalResult,
    QuestionValidationError,
    StrictModel,
    parse_model,
)

# Allowlist of extensions and the content check each must pass (T10).
ALLOWED_EXTENSIONS = {
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "zip",
    "txt",
    "md",
    "csv",
    "py",
    "c",
    "cpp",
    "java",
}
_MAGIC = {
    "pdf": (b"%PDF-",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "zip": (b"PK\x03\x04",),
}
_TEXT_EXTENSIONS = {"txt", "md", "csv", "py", "c", "cpp", "java"}
CONTENT_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "zip": "application/zip",
}


def content_type_for(extension: str) -> str:
    return CONTENT_TYPES.get(extension, "text/plain")


def check_file_content(extension: str, data: bytes) -> None:
    """Server-side content validation: extension must match the actual bytes."""
    if extension in _MAGIC:
        if not any(data.startswith(sig) for sig in _MAGIC[extension]):
            raise QuestionValidationError(f"file content does not match .{extension}")
    elif extension in _TEXT_EXTENSIONS:
        if b"\x00" in data:
            raise QuestionValidationError(f"file content does not look like .{extension} text")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise QuestionValidationError("text files must be valid UTF-8") from exc
    else:
        raise QuestionValidationError(f"extension .{extension} is not allowed")


class FileUploadPrompt(StrictModel):
    text: str = Field(min_length=1, max_length=5000)
    allowed_extensions: list[str] = Field(min_length=1, max_length=len(ALLOWED_EXTENSIONS))
    max_size_bytes: int = Field(default=1024 * 1024, ge=1, le=10 * 1024 * 1024)


class FileUploadHidden(StrictModel):
    pass


class FileUploadModule:
    question_type = "file_upload"

    def validate_definition(
        self, prompt: dict[str, Any], hidden: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        p = parse_model(FileUploadPrompt, prompt, "prompt")
        h = parse_model(FileUploadHidden, hidden, "hidden_eval")
        normalized = [e.lower().lstrip(".") for e in p.allowed_extensions]
        if not set(normalized) <= ALLOWED_EXTENSIONS:
            raise QuestionValidationError(
                f"prompt.allowed_extensions must be within {sorted(ALLOWED_EXTENSIONS)}"
            )
        data = p.model_dump()
        data["allowed_extensions"] = sorted(set(normalized))
        return data, h.model_dump()

    def sanitize_for_candidate(self, prompt: dict[str, Any]) -> dict[str, Any]:
        return FileUploadPrompt.model_validate(prompt).model_dump()

    def validate_response(self, prompt: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        raise QuestionValidationError("file answers must use the upload endpoint")

    def evaluate(
        self,
        prompt: dict[str, Any],
        hidden: dict[str, Any],
        payload: dict[str, Any],
        max_score: float,
    ) -> EvalResult:
        return EvalResult(None, "pending")
