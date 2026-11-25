from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AssessmentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration_minutes: int = Field(default=60, ge=1, le=1440)
    max_attempts: int = Field(default=1, ge=1, le=10)
    closes_at: datetime | None = None


class AssessmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10000)
    config: AssessmentConfig = Field(default_factory=AssessmentConfig)


class AssessmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    config: AssessmentConfig | None = None


class AssessmentOut(BaseModel):
    id: UUID
    tenant_id: UUID
    title: str
    description: str
    status: str
    created_at: datetime
    version_number: int
    is_frozen: bool
    canonical_digest: str | None
    config: dict[str, Any]
    question_count: int | None = None


class QuestionCreate(BaseModel):
    question_type: str
    prompt: dict[str, Any]
    hidden_eval: dict[str, Any] = Field(default_factory=dict)
    max_score: float = Field(default=1.0, gt=0, le=1000)
    position: int | None = Field(default=None, ge=1)


class QuestionUpdate(BaseModel):
    prompt: dict[str, Any] | None = None
    hidden_eval: dict[str, Any] | None = None
    max_score: float | None = Field(default=None, gt=0, le=1000)


class OrganizerQuestionOut(BaseModel):
    id: UUID
    question_type: str
    position: int
    prompt: dict[str, Any]
    hidden_eval: dict[str, Any]
    max_score: float


class CandidateQuestionOut(BaseModel):
    id: UUID
    question_type: str
    position: int
    prompt: dict[str, Any]
    max_score: float


class AssessmentDetailOut(AssessmentOut):
    questions: list[OrganizerQuestionOut]


class PreviewOut(BaseModel):
    assessment_id: UUID
    title: str
    questions: list[CandidateQuestionOut]


class EnrollRequest(BaseModel):
    emails: list[EmailStr] = Field(min_length=1, max_length=500)


class EnrollmentOut(BaseModel):
    email: str
    full_name: str


class EnrollResult(BaseModel):
    added: list[str]


class GradeRequest(BaseModel):
    question_id: UUID
    score: float = Field(ge=0)


class ResultRow(BaseModel):
    attempt_id: UUID
    candidate_email: str
    attempt_status: str
    started_at: datetime
    submitted_at: datetime | None
    submission_id: UUID | None
    submission_status: str | None
    score: float | None
    scores: dict[str, Any]
    responses: dict[str, dict[str, Any]] = Field(default_factory=dict)
