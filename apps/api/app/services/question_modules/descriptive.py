from typing import Any

from pydantic import Field

from app.services.question_modules.base import (
    EvalResult,
    QuestionValidationError,
    StrictModel,
    parse_model,
)


class DescriptivePrompt(StrictModel):
    text: str = Field(min_length=1, max_length=5000)
    max_length: int = Field(default=5000, ge=1, le=20000)


class DescriptiveHidden(StrictModel):
    rubric: str = Field(default="", max_length=5000)


class DescriptiveResponse(StrictModel):
    text: str


class DescriptiveModule:
    question_type = "descriptive"

    def validate_definition(
        self, prompt: dict[str, Any], hidden: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        p = parse_model(DescriptivePrompt, prompt, "prompt")
        h = parse_model(DescriptiveHidden, hidden, "hidden_eval")
        return p.model_dump(), h.model_dump()

    def sanitize_for_candidate(self, prompt: dict[str, Any]) -> dict[str, Any]:
        return DescriptivePrompt.model_validate(prompt).model_dump()

    def validate_response(self, prompt: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        r = parse_model(DescriptiveResponse, payload, "response")
        if "\x00" in r.text:
            raise QuestionValidationError("response.text contains invalid characters")
        if len(r.text) > prompt["max_length"]:
            raise QuestionValidationError(
                f"response.text exceeds the {prompt['max_length']} character limit"
            )
        return r.model_dump()

    def evaluate(
        self,
        prompt: dict[str, Any],
        hidden: dict[str, Any],
        payload: dict[str, Any],
        max_score: float,
    ) -> EvalResult:
        # Manual grading hook: organizers grade via the grades endpoint.
        return EvalResult(None, "pending")
