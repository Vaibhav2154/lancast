from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.assessments import CandidateQuestionOut


class ResponseSave(BaseModel):
    payload: dict[str, Any]
    client_seq: int = Field(ge=1, description="Strictly increasing per question; guards replays")


class SavedResponseOut(BaseModel):
    question_id: UUID
    applied: bool
    client_seq: int
    saved_at: datetime


class SavedResponseView(BaseModel):
    payload: dict[str, Any]
    client_seq: int
    saved_at: datetime


class AttemptOut(BaseModel):
    id: UUID
    status: str
    started_at: datetime
    deadline_at: datetime
    server_time: datetime
    remaining_seconds: int
    questions: list[CandidateQuestionOut]
    responses: dict[str, SavedResponseView]
    resumed: bool | None = None
    assessment_title: str | None = None


class SubmissionOut(BaseModel):
    id: UUID
    attempt_id: UUID
    status: str
    score: float | None
    submitted_at: datetime
    replayed: bool


class UploadOut(BaseModel):
    file_id: UUID
    original_name: str
    size_bytes: int
    sha256: str


class MyAssessmentOut(BaseModel):
    tenant_id: UUID
    assessment_id: UUID
    title: str
    description: str
    duration_minutes: int = 60
    max_attempts: int = 1
    attempts_used: int = 0
    can_start: bool = True
    active_attempt_id: UUID | None = None
    latest_attempt_id: UUID | None = None
    latest_attempt_status: str | None = None
    latest_submission_status: str | None = None
    latest_score: float | None = None
    max_score: float = 0.0


class MyAttemptOut(BaseModel):
    attempt_id: UUID
    tenant_id: UUID
    assessment_id: UUID
    assessment_title: str
    assessment_status: str
    attempt_status: str
    started_at: datetime
    submitted_at: datetime | None
    submission_id: UUID | None
    submission_status: str | None
    score: float | None
    max_score: float


class ExecutionResultCase(BaseModel):
    passed: bool
    verdict: str = Field(max_length=64)


class ExecutionResultIn(BaseModel):
    status: Literal["completed", "failed", "timed_out"]
    test_results: list[ExecutionResultCase] = Field(default_factory=list, max_length=50)
    worker_id: str | None = Field(default=None, max_length=128)
    error: str | None = Field(default=None, max_length=500)


class CodeRunRequest(BaseModel):
    language: str
    source_code: str = Field(min_length=1)
    custom_stdin: str | None = Field(default=None, max_length=10000)


class CodeRunCaseOut(BaseModel):
    stdin: str
    expected_stdout: str | None
    stdout: str
    stderr: str
    compile_output: str
    verdict: str
    passed: bool | None
    time_sec: float | None


class CodeRunResponse(BaseModel):
    mode: Literal["sample_cases", "custom_input"]
    cases: list[CodeRunCaseOut]
