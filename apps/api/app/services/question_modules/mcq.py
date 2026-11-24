from typing import Any

from pydantic import Field

from app.services.question_modules.base import (
    EvalResult,
    QuestionValidationError,
    StrictModel,
    parse_model,
)


class Option(StrictModel):
    id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=1000)


class McqPrompt(StrictModel):
    text: str = Field(min_length=1, max_length=5000)
    options: list[Option] = Field(min_length=2, max_length=10)


class McqHidden(StrictModel):
    correct: str


class McqResponse(StrictModel):
    selected: str


class McqModule:
    question_type = "mcq"

    def validate_definition(
        self, prompt: dict[str, Any], hidden: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        p = parse_model(McqPrompt, prompt, "prompt")
        h = parse_model(McqHidden, hidden, "hidden_eval")
        ids = [o.id for o in p.options]
        if len(set(ids)) != len(ids):
            raise QuestionValidationError("prompt.options: option ids must be unique")
        if h.correct not in ids:
            raise QuestionValidationError("hidden_eval.correct must be one of the option ids")
        return p.model_dump(), h.model_dump()

    def sanitize_for_candidate(self, prompt: dict[str, Any]) -> dict[str, Any]:
        return McqPrompt.model_validate(prompt).model_dump()

    def validate_response(self, prompt: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        r = parse_model(McqResponse, payload, "response")
        if r.selected not in {o["id"] for o in prompt["options"]}:
            raise QuestionValidationError("response.selected is not a valid option")
        return r.model_dump()

    def evaluate(
        self,
        prompt: dict[str, Any],
        hidden: dict[str, Any],
        payload: dict[str, Any],
        max_score: float,
    ) -> EvalResult:
        correct = payload.get("selected") == hidden["correct"]
        return EvalResult(max_score if correct else 0.0, "scored")
