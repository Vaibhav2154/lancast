from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError


class QuestionValidationError(ValueError):
    """Raised when a question definition or candidate response is invalid."""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class EvalResult:
    score: float | None
    status: Literal["scored", "pending"]


def parse_model[M: BaseModel](model: type[M], data: Any, label: str) -> M:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        details = "; ".join(
            f"{label}.{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise QuestionValidationError(details) from exc


class QuestionModule(Protocol):
    """Documented module contract for adding question types (FR-MOD-04)."""

    question_type: str

    def validate_definition(
        self, prompt: dict[str, Any], hidden: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Validate/normalize organizer input; return (prompt, hidden_eval)."""
        ...

    def sanitize_for_candidate(self, prompt: dict[str, Any]) -> dict[str, Any]:
        """Return only candidate-safe fields (never hidden answers/tests; FR-MOD-05)."""
        ...

    def validate_response(self, prompt: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        """Validate/normalize a candidate response."""
        ...

    def evaluate(
        self,
        prompt: dict[str, Any],
        hidden: dict[str, Any],
        payload: dict[str, Any],
        max_score: float,
    ) -> EvalResult:
        """Score a response server-side (FR-MOD-03)."""
        ...
