from typing import Any, Literal

from pydantic import Field

from app.services.question_modules.base import (
    EvalResult,
    QuestionValidationError,
    StrictModel,
    parse_model,
)
from app.services.question_modules.mcq import McqPrompt


class MultiHidden(StrictModel):
    correct: list[str] = Field(min_length=1, max_length=10)
    scoring: Literal["exact", "partial"] = "exact"


class MultiResponse(StrictModel):
    selected: list[str] = Field(max_length=10)


class MultipleSelectModule:
    question_type = "multiple_select"

    def validate_definition(
        self, prompt: dict[str, Any], hidden: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        p = parse_model(McqPrompt, prompt, "prompt")
        h = parse_model(MultiHidden, hidden, "hidden_eval")
        ids = [o.id for o in p.options]
        if len(set(ids)) != len(ids):
            raise QuestionValidationError("prompt.options: option ids must be unique")
        if len(set(h.correct)) != len(h.correct) or not set(h.correct) <= set(ids):
            raise QuestionValidationError(
                "hidden_eval.correct must be unique option ids present in prompt.options"
            )
        return p.model_dump(), h.model_dump()

    def sanitize_for_candidate(self, prompt: dict[str, Any]) -> dict[str, Any]:
        return McqPrompt.model_validate(prompt).model_dump()

    def validate_response(self, prompt: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        r = parse_model(MultiResponse, payload, "response")
        valid = {o["id"] for o in prompt["options"]}
        if len(set(r.selected)) != len(r.selected) or not set(r.selected) <= valid:
            raise QuestionValidationError("response.selected must be unique, valid option ids")
        return r.model_dump()

    def evaluate(
        self,
        prompt: dict[str, Any],
        hidden: dict[str, Any],
        payload: dict[str, Any],
        max_score: float,
    ) -> EvalResult:
        correct = set(hidden["correct"])
        selected = set(payload.get("selected", []))
        if hidden.get("scoring", "exact") == "exact":
            return EvalResult(max_score if selected == correct else 0.0, "scored")
        # Partial: reward correct picks, penalize wrong picks, floor at zero.
        net = len(selected & correct) - len(selected - correct)
        fraction = max(0.0, net / len(correct))
        return EvalResult(round(max_score * fraction, 4), "scored")
