from typing import Any

from pydantic import Field

from app.services.question_modules.base import (
    EvalResult,
    QuestionValidationError,
    StrictModel,
    parse_model,
)

SUPPORTED_LANGUAGES = {"python3", "c", "cpp", "java", "javascript"}
MAX_SOURCE_BYTES = 64 * 1024


class SampleCase(StrictModel):
    stdin: str = Field(default="", max_length=10000)
    expected_stdout: str = Field(max_length=10000)


class CodingPrompt(StrictModel):
    text: str = Field(min_length=1, max_length=5000)
    languages: list[str] = Field(min_length=1)
    sample_cases: list[SampleCase] = Field(default_factory=list, max_length=5)


class CodingHidden(StrictModel):
    test_cases: list[SampleCase] = Field(min_length=1, max_length=50)
    cpu_time_limit_sec: float = Field(default=2.0, ge=0.5, le=10.0)
    memory_limit_mb: int = Field(default=256, ge=32, le=512)


class CodingResponse(StrictModel):
    language: str
    source_code: str = Field(min_length=1)


class CodingModule:
    question_type = "coding"

    def validate_definition(
        self, prompt: dict[str, Any], hidden: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        p = parse_model(CodingPrompt, prompt, "prompt")
        h = parse_model(CodingHidden, hidden, "hidden_eval")
        if not set(p.languages) <= SUPPORTED_LANGUAGES:
            raise QuestionValidationError(
                f"prompt.languages must be within {sorted(SUPPORTED_LANGUAGES)}"
            )
        return p.model_dump(), h.model_dump()

    def sanitize_for_candidate(self, prompt: dict[str, Any]) -> dict[str, Any]:
        # Hidden test cases live only in hidden_eval; sample_cases are intentionally public.
        return CodingPrompt.model_validate(prompt).model_dump()

    def validate_response(self, prompt: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        r = parse_model(CodingResponse, payload, "response")
        if r.language not in prompt["languages"]:
            raise QuestionValidationError("response.language is not allowed for this question")
        if len(r.source_code.encode("utf-8")) > MAX_SOURCE_BYTES:
            raise QuestionValidationError("response.source_code exceeds 64 KB")
        return r.model_dump()

    def evaluate(
        self,
        prompt: dict[str, Any],
        hidden: dict[str, Any],
        payload: dict[str, Any],
        max_score: float,
    ) -> EvalResult:
        # Scored asynchronously by the out-of-process execution worker (FR-CODE-01).
        return EvalResult(None, "pending")
