export interface HealthInfo {
  status: string;
  service: string;
  version: string;
  deployment_profile: "standalone" | "central" | string;
  environment: string;
}

export interface ReadinessInfo {
  status: "ready" | "degraded" | string;
  deployment_profile: string;
  dependencies: {
    postgres: string;
    redis: string;
  };
}

export type TenantRole = "tenant_admin" | "organizer" | "candidate";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  is_platform_admin: boolean;
}

export interface AuthMembership {
  tenant_id: string;
  role: TenantRole;
}

export interface MeResponse {
  user: AuthUser;
  memberships: AuthMembership[];
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
}

export interface Tenant {
  id: string;
  slug: string;
  name: string;
  is_active: boolean;
}

export interface Member {
  user_id: string;
  email: string;
  full_name: string;
  role: TenantRole;
}

export type AssessmentStatus = "draft" | "published" | "active" | "closed" | "archived";
export type QuestionType = "mcq" | "multiple_select" | "descriptive" | "file_upload" | "coding";
export type CodingLanguage = "python3" | "c" | "cpp" | "java" | "javascript";

export interface AssessmentConfig {
  duration_minutes: number;
  max_attempts: number;
  closes_at: string | null;
}

export interface AssessmentSummary {
  id: string;
  tenant_id: string;
  title: string;
  description: string;
  status: AssessmentStatus;
  created_at: string;
  version_number: number;
  is_frozen: boolean;
  canonical_digest: string | null;
  config: AssessmentConfig;
  question_count: number | null;
}

export interface OrganizerQuestion {
  id: string;
  question_type: QuestionType;
  position: number;
  prompt: Record<string, unknown>;
  hidden_eval: Record<string, unknown>;
  max_score: number;
}

export interface CandidateQuestion {
  id: string;
  question_type: QuestionType;
  position: number;
  prompt: Record<string, unknown>;
  max_score: number;
}

export interface AssessmentDetail extends AssessmentSummary {
  questions: OrganizerQuestion[];
}

export interface PreviewResponse {
  assessment_id: string;
  title: string;
  questions: CandidateQuestion[];
}

export interface Enrollment {
  email: string;
  full_name: string;
}

export interface ResultScoreEntry {
  score: number | null;
  status: "scored" | "pending" | "error" | string;
  type: QuestionType;
  answered: boolean;
  passed?: number;
  total?: number;
  error?: string;
}

export interface ResultRow {
  attempt_id: string;
  candidate_email: string;
  attempt_status: "in_progress" | "submitted" | "expired" | "flagged" | string;
  started_at: string;
  submitted_at: string | null;
  submission_id: string | null;
  submission_status: "queued" | "evaluating" | "pending_review" | "scored" | "failed" | string | null;
  score: number | null;
  scores: Record<string, ResultScoreEntry>;
  responses: Record<string, Record<string, unknown>>;
}

export interface MyAssessment {
  tenant_id: string;
  assessment_id: string;
  title: string;
  description: string;
  duration_minutes: number;
  max_attempts: number;
  attempts_used: number;
  can_start: boolean;
  active_attempt_id: string | null;
  latest_attempt_id: string | null;
  latest_attempt_status: string | null;
  latest_submission_status: string | null;
  latest_score: number | null;
  max_score: number;
}

export interface MyAttempt {
  attempt_id: string;
  tenant_id: string;
  assessment_id: string;
  assessment_title: string;
  assessment_status: AssessmentStatus;
  attempt_status: string;
  started_at: string;
  submitted_at: string | null;
  submission_id: string | null;
  submission_status: string | null;
  score: number | null;
  max_score: number;
}

export interface SavedResponseView {
  payload: Record<string, unknown>;
  client_seq: number;
  saved_at: string;
}

export interface AttemptView {
  id: string;
  status: "in_progress" | "submitted" | "expired" | "flagged" | string;
  started_at: string;
  deadline_at: string;
  server_time: string;
  remaining_seconds: number;
  questions: CandidateQuestion[];
  responses: Record<string, SavedResponseView>;
  resumed: boolean | null;
  assessment_title?: string | null;
}

export interface SavedResponseResult {
  question_id: string;
  applied: boolean;
  client_seq: number;
  saved_at: string;
}

export interface UploadResult {
  file_id: string;
  original_name: string;
  size_bytes: number;
  sha256: string;
}

export interface SubmissionResult {
  id: string;
  attempt_id: string;
  status: string;
  score: number | null;
  submitted_at: string;
  replayed: boolean;
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function extractErrorMessage(data: unknown, fallback = "Request failed"): { code: string; message: string } {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (detail && typeof detail === "object" && !Array.isArray(detail)) {
      const d = detail as { code?: unknown; message?: unknown };
      if (typeof d.message === "string") {
        return {
          code: typeof d.code === "string" ? d.code : "API_ERROR",
          message: d.message,
        };
      }
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const msgs = detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            const loc = Array.isArray((item as { loc?: unknown[] }).loc)
              ? (item as { loc: unknown[] }).loc.slice(1).join(".")
              : "";
            const msg = String((item as { msg: unknown }).msg);
            return loc ? `${loc}: ${msg}` : msg;
          }
          return String(item);
        })
        .join("; ");
      return { code: "VALIDATION_ERROR", message: msgs || fallback };
    }
    if (typeof detail === "string") {
      return { code: "API_ERROR", message: detail };
    }
  }
  return { code: "API_ERROR", message: fallback };
}

const TOKEN_KEY = "lancast-token";

export function getStoredToken(): string | null {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) {
    window.localStorage.setItem(TOKEN_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_KEY);
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { token?: string | null } = {}
): Promise<T> {
  const { token, headers: customHeaders, body, ...rest } = options;
  const authToken = token !== undefined ? token : getStoredToken();
  const headers = new Headers(customHeaders);
  if (authToken) {
    headers.set("Authorization", `Bearer ${authToken}`);
  }
  if (body && !(body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(path, { ...rest, headers, body });
  if (res.status === 204) {
    return undefined as T;
  }

  const contentType = res.headers.get("content-type") ?? "";
  if (!res.ok) {
    const errData = contentType.includes("application/json")
      ? await res.json().catch(() => null)
      : null;
    const { code, message } = extractErrorMessage(errData, `Request failed (HTTP ${res.status})`);
    throw new ApiError(res.status, code, message);
  }

  if (contentType.includes("application/json")) {
    return (await res.json()) as T;
  }
  return (await res.text()) as unknown as T;
}

// Health & Readiness
export async function fetchHealth(): Promise<HealthInfo> {
  return request<HealthInfo>("/api/health", { token: null });
}

export async function fetchReadiness(): Promise<ReadinessInfo> {
  const res = await fetch("/api/ready");
  return (await res.json()) as ReadinessInfo;
}

// Auth
export async function registerUser(
  payload: { email: string; full_name: string; password: string },
  token?: string | null
): Promise<AuthUser> {
  return request<AuthUser>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
    token: token ?? null,
  });
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
    token: null,
  });
}

export async function fetchMe(token?: string): Promise<MeResponse> {
  return request<MeResponse>("/api/auth/me", { token });
}

export async function logout(token?: string): Promise<void> {
  await request<void>("/api/auth/logout", { method: "POST", token }).catch(() => {});
}

// Tenants & Memberships
export async function listTenants(): Promise<Tenant[]> {
  return request<Tenant[]>("/api/tenants");
}

export async function createTenant(slug: string, name: string): Promise<Tenant> {
  return request<Tenant>("/api/tenants", {
    method: "POST",
    body: JSON.stringify({ slug, name }),
  });
}

export async function listMembers(tenantId: string): Promise<Member[]> {
  return request<Member[]>(`/api/tenants/${tenantId}/memberships`);
}

export async function addMember(
  tenantId: string,
  payload: { email: string; role: TenantRole; full_name?: string; password?: string }
): Promise<Member> {
  return request<Member>(`/api/tenants/${tenantId}/memberships`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// Assessments (Organizer)
export async function listAssessments(tenantId: string): Promise<AssessmentSummary[]> {
  return request<AssessmentSummary[]>(`/api/tenants/${tenantId}/assessments`);
}

export async function createAssessment(
  tenantId: string,
  payload: { title: string; description: string; config: Partial<AssessmentConfig> }
): Promise<AssessmentSummary> {
  return request<AssessmentSummary>(`/api/tenants/${tenantId}/assessments`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAssessmentDetail(
  tenantId: string,
  assessmentId: string
): Promise<AssessmentDetail> {
  return request<AssessmentDetail>(`/api/tenants/${tenantId}/assessments/${assessmentId}`);
}

export async function updateAssessment(
  tenantId: string,
  assessmentId: string,
  payload: { title?: string; description?: string; config?: AssessmentConfig }
): Promise<AssessmentSummary> {
  return request<AssessmentSummary>(`/api/tenants/${tenantId}/assessments/${assessmentId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function addQuestion(
  tenantId: string,
  assessmentId: string,
  payload: {
    question_type: QuestionType;
    prompt: Record<string, unknown>;
    hidden_eval: Record<string, unknown>;
    max_score: number;
    position?: number;
  }
): Promise<OrganizerQuestion> {
  return request<OrganizerQuestion>(
    `/api/tenants/${tenantId}/assessments/${assessmentId}/questions`,
    { method: "POST", body: JSON.stringify(payload) }
  );
}

export async function updateQuestion(
  tenantId: string,
  assessmentId: string,
  questionId: string,
  payload: {
    prompt?: Record<string, unknown>;
    hidden_eval?: Record<string, unknown>;
    max_score?: number;
  }
): Promise<OrganizerQuestion> {
  return request<OrganizerQuestion>(
    `/api/tenants/${tenantId}/assessments/${assessmentId}/questions/${questionId}`,
    { method: "PUT", body: JSON.stringify(payload) }
  );
}

export async function deleteQuestion(
  tenantId: string,
  assessmentId: string,
  questionId: string
): Promise<void> {
  return request<void>(
    `/api/tenants/${tenantId}/assessments/${assessmentId}/questions/${questionId}`,
    { method: "DELETE" }
  );
}

export async function previewAssessment(
  tenantId: string,
  assessmentId: string
): Promise<PreviewResponse> {
  return request<PreviewResponse>(
    `/api/tenants/${tenantId}/assessments/${assessmentId}/preview`
  );
}

export async function transitionAssessment(
  tenantId: string,
  assessmentId: string,
  action: "publish" | "start" | "close" | "archive"
): Promise<AssessmentSummary> {
  return request<AssessmentSummary>(
    `/api/tenants/${tenantId}/assessments/${assessmentId}/${action}`,
    { method: "POST" }
  );
}

export async function listEnrollments(
  tenantId: string,
  assessmentId: string
): Promise<Enrollment[]> {
  return request<Enrollment[]>(
    `/api/tenants/${tenantId}/assessments/${assessmentId}/enrollments`
  );
}

export async function enrollCandidates(
  tenantId: string,
  assessmentId: string,
  emails: string[]
): Promise<{ added: string[] }> {
  return request<{ added: string[] }>(
    `/api/tenants/${tenantId}/assessments/${assessmentId}/enrollments`,
    { method: "POST", body: JSON.stringify({ emails }) }
  );
}

export async function getAssessmentResults(
  tenantId: string,
  assessmentId: string
): Promise<ResultRow[]> {
  return request<ResultRow[]>(
    `/api/tenants/${tenantId}/assessments/${assessmentId}/results`
  );
}

export async function exportAssessmentResultsCsv(
  tenantId: string,
  assessmentId: string
): Promise<Blob> {
  const token = getStoredToken();
  const res = await fetch(
    `/api/tenants/${tenantId}/assessments/${assessmentId}/results/export`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }
  );
  if (!res.ok) {
    const errData = await res.json().catch(() => null);
    const { code, message } = extractErrorMessage(errData, `Export failed (HTTP ${res.status})`);
    throw new ApiError(res.status, code, message);
  }
  return res.blob();
}

export async function downloadUploadedFile(
  tenantId: string,
  fileId: string
): Promise<Blob> {
  const token = getStoredToken();
  const res = await fetch(`/api/tenants/${tenantId}/uploads/${fileId}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => null);
    const { code, message } = extractErrorMessage(
      errData,
      `Download failed (HTTP ${res.status})`
    );
    throw new ApiError(res.status, code, message);
  }
  return res.blob();
}

export async function gradeSubmissionQuestion(
  tenantId: string,
  submissionId: string,
  questionId: string,
  score: number
): Promise<{ submission_id: string; status: string; score: number }> {
  return request<{ submission_id: string; status: string; score: number }>(
    `/api/tenants/${tenantId}/submissions/${submissionId}/grades`,
    { method: "PUT", body: JSON.stringify({ question_id: questionId, score }) }
  );
}

// Assessment Capsules
export async function exportCapsule(
  tenantId: string,
  assessmentId: string
): Promise<Blob> {
  const token = getStoredToken();
  const res = await fetch(`/api/tenants/${tenantId}/assessments/${assessmentId}/capsule`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => null);
    const { code, message } = extractErrorMessage(errData, `Export failed (HTTP ${res.status})`);
    throw new ApiError(res.status, code, message);
  }
  return res.blob();
}

export async function importCapsule(
  tenantId: string,
  file: File
): Promise<AssessmentSummary> {
  const form = new FormData();
  form.append("file", file);
  return request<AssessmentSummary>(`/api/tenants/${tenantId}/capsules/import`, {
    method: "POST",
    body: form,
  });
}

// Candidate Attempts
export async function getMyAssessments(): Promise<MyAssessment[]> {
  return request<MyAssessment[]>("/api/me/assessments");
}

export async function getMyAttempts(): Promise<MyAttempt[]> {
  return request<MyAttempt[]>("/api/me/attempts");
}

export async function startOrResumeAttempt(
  tenantId: string,
  assessmentId: string
): Promise<AttemptView> {
  return request<AttemptView>(
    `/api/tenants/${tenantId}/assessments/${assessmentId}/attempts`,
    { method: "POST" }
  );
}

export async function getAttempt(attemptId: string): Promise<AttemptView> {
  return request<AttemptView>(`/api/attempts/${attemptId}`);
}

export async function saveAttemptResponse(
  attemptId: string,
  questionId: string,
  payload: Record<string, unknown>,
  clientSeq: number
): Promise<SavedResponseResult> {
  return request<SavedResponseResult>(
    `/api/attempts/${attemptId}/responses/${questionId}`,
    {
      method: "PUT",
      body: JSON.stringify({ payload, client_seq: clientSeq }),
    }
  );
}

export async function uploadAttemptFile(
  attemptId: string,
  questionId: string,
  file: File
): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResult>(
    `/api/attempts/${attemptId}/questions/${questionId}/upload`,
    {
      method: "POST",
      body: form,
    }
  );
}

export async function submitAttempt(
  attemptId: string,
  idempotencyKey: string
): Promise<SubmissionResult> {
  return request<SubmissionResult>(`/api/attempts/${attemptId}/submit`, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
  });
}

export async function getAttemptSubmission(attemptId: string): Promise<SubmissionResult> {
  return request<SubmissionResult>(`/api/attempts/${attemptId}/submission`);
}

export interface CodeRunCaseResult {
  stdin: string;
  expected_stdout: string | null;
  stdout: string;
  stderr: string;
  compile_output: string;
  verdict: string;
  passed: boolean | null;
  time_sec: number | null;
}

export interface CodeRunResponse {
  mode: "sample_cases" | "custom_input";
  cases: CodeRunCaseResult[];
}

export async function runAttemptCode(
  attemptId: string,
  questionId: string,
  payload: { language: string; source_code: string; custom_stdin?: string | null }
): Promise<CodeRunResponse> {
  return request<CodeRunResponse>(
    `/api/attempts/${attemptId}/questions/${questionId}/run`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}
