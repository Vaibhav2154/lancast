# Phase 2 — Core Multi-Tenant Assessment Platform

**Status:** Complete | **Exit Condition:** Multi-tenant RBAC, assessment lifecycle, all 5 question modules, candidate attempt durability, out-of-process code execution, Assessment Capsules, organizer grading, and full React portals verified end-to-end.  
**Key Commits:** `28aaefe`, `7f9baf6`, `5d517af`, `87b88ff`, `a51dd1b`, `7bcf9ee`

---

## 1. Requirements Covered

- **Identity & Tenancy:** `FR-ID-01..04`, `FR-TEN-01..04`, `T01`, `T02`, `T03`
- **Assessments & Modules:** `FR-AS-01..05`, `FR-MOD-01..05`, `T04`, `T05`
- **Attempts & Code Execution:** `FR-ATT-01..06`, `FR-CODE-01..05`, `T06`, `T07`, `T08`, `T10`
- **Assessment Capsules:** `FR-CAP-01..05`, `T10`

---

## 2. Database Extensions (`0002_phase2_core_extensions.py`)

Implemented in [apps/api/app/db/models.py](../../apps/api/app/db/models.py) and migrated via [0002_phase2_core_extensions.py](../../apps/api/alembic/versions/0002_phase2_core_extensions.py):

- **`user_sessions`:** Server-side revocable JWT session store (`created_at`, `expires_at`, `revoked_at`).
- **`assessment_enrollments`:** Candidate allowlist per assessment with unique constraint `uq_enrollment_assessment_candidate`.
- **`uploaded_files`:** Metadata for validated uploads (`original_name`, UUID-generated `stored_name`, `content_type`, `size_bytes`, `sha256`).
- **Column & constraint additions:** `responses.client_seq` (`BigInteger` monotonic replay guard), `submissions.scores_json` (per-question status/score breakdown), `uq_submission_attempt` (exactly-once submission per attempt), and `execution_jobs.result_json`.
- Fixed redundant index/constraint drift on `tenants.slug` and `users.email` so `alembic check` passes cleanly.

---

## 3. Backend Services & Endpoints (`apps/api/app/`)

### 3.1 Local Authentication, Tenancy & Hash-Linked Audit
- **Security ([core/security.py](../../apps/api/app/core/security.py), [services/auth.py](../../apps/api/app/services/auth.py), [routers/auth.py](../../apps/api/app/routers/auth.py)):** Argon2 (`pwdlib`) password hashing with timing-safe dummy hash verification on unknown emails; PyJWT bearer tokens tied to revocable `user_sessions` (`POST /api/auth/register`, `/login`, `/logout`, `/me`). First registered user bootstraps `is_platform_admin=True`.
- **Multi-Tenant Authorization ([core/deps.py](../../apps/api/app/core/deps.py), [services/tenancy.py](../../apps/api/app/services/tenancy.py), [routers/tenants.py](../../apps/api/app/routers/tenants.py)):** `TenantManager`, `OrganizerCtx`, `CandidateCtx`, and `PlatformAdmin` dependencies derive scope strictly from authenticated `Membership` records (`FR-TEN-03`). Unauthorized/cross-tenant probes commit `authz.denied` audit entries and return `403`/`404` (`T01`).
- **Hash-Linked Audit ([services/audit.py](../../apps/api/app/services/audit.py)):** Append-oriented `audit_events` writer linking SHA-256 `prev_hash -> event_hash` over canonical payload metadata plus a `verify_chain()` helper.

### 3.2 Assessment Lifecycle, 5 Pluggable Question Modules & Grading
- **Question Module Contract ([services/question_modules/](../../apps/api/app/services/question_modules/)):** Registry pattern with `validate_definition`, `sanitize_for_candidate` (strips `hidden_eval_json`), `validate_response`, and `evaluate`:
  - `mcq.py` — single-choice exact match
  - `multiple_select.py` — exact and partial (`(correct - wrong) / total_correct`, floored at `0`) scoring
  - `descriptive.py` — max-length enforcement + `pending` manual grading hook
  - `file_upload.py` & [services/uploads.py](../../apps/api/app/services/uploads.py) — allowed-extension filtering, size limit, magic-byte/PDF/ZIP/image/UTF-8 content verification, sanitized display name + generated UUID filename on disk (path-traversal safe, `resolve_upload_path`), single-file replacement per question
  - `coding.py` — supports `python3`, `c`, `cpp`, `java`, `javascript`; 64 KB source limit, public `sample_cases` separated from `hidden_eval.test_cases`, asynchronous `pending` grading via execution queue
- **Assessment & Grading Routes ([routers/assessments.py](../../apps/api/app/routers/assessments.py), [services/assessments.py](../../apps/api/app/services/assessments.py)):**
  - Lifecycle: `draft -> published -> active -> closed -> archived`. Publishing freezes `AssessmentVersion` and computes canonical SHA-256 `canonical_digest` (`T05`), which is re-verified before starting any attempt.
  - Endpoints: CRUD on `/api/tenants/{tenant_id}/assessments` & `/questions`, `/preview` (candidate-safe DTO), `/publish`, `/start`, `/close` (auto-finalizes `in_progress` attempts), `/archive`, `/enrollments`, `/results` (returns scores **and** saved `responses` for review), `/results/export` (RFC 4180 CSV export with `_csv_cell` formula-injection protection), `PUT /api/tenants/{tenant_id}/submissions/{submission_id}/grades`, and `GET /api/tenants/{tenant_id}/uploads/{file_id}` (tenant-scoped download with `X-Content-Type-Options: nosniff`).

### 3.3 Candidate Attempts, Idempotency & Interactive Code Runner
- **Queue & Runner ([services/execution_queue.py](../../apps/api/app/services/execution_queue.py), [services/code_runner.py](../../apps/api/app/services/code_runner.py)):**
  - `RedisExecutionQueue`: atomic Lua script bounding `lancast:execution:queue` by `EXECUTION_QUEUE_MAX_DEPTH` (`503 QUEUE_FULL` admission guard).
  - `Judge0CodeRunner`: synchronous interactive runs for candidate **Run Code** against public `sample_cases` or `custom_stdin` ONLY (never hidden tests), sending `base64_encoded=true` and enforcing per-language `RLIMIT_AS` virtual memory floors (`2048000` KB JS, `8388608` KB Java).
- **Attempt Endpoints ([routers/attempts.py](../../apps/api/app/routers/attempts.py), [services/attempts.py](../../apps/api/app/services/attempts.py)):**
  - `GET /api/me/assessments` (active enrolled assessments + duration, attempt counts, `can_start`, active/latest attempt status & score) and `GET /api/me/attempts` (full attempt history across active, closed, and archived exams).
  - `POST .../attempts` (enforces enrollment, digest integrity, `max_attempts`, closing window, and resumable open attempts).
  - `GET /api/attempts/{attempt_id}`, `PUT /api/attempts/{attempt_id}/responses/{question_id}` (monotonic `client_seq` rejects stale replays without clobbering newer saves), `POST .../upload`, `POST .../run`, `POST .../submit` (`Idempotency-Key` guarantees exactly one `Submission`), and `GET /api/attempts/{attempt_id}/submission` (live evaluation status & score).

### 3.4 Assessment Capsules & Internal Worker Callback
- **Capsules ([services/capsules.py](../../apps/api/app/services/capsules.py), [routers/capsules.py](../../apps/api/app/routers/capsules.py)):** `GET .../capsule` exports `manifest.json` + SHA-256 digest zip (strictly excluding candidate/attempt/secret records); `POST .../capsules/import` enforces zip-slip, entry count (`<=20`), compressed (`<=5 MB`), uncompressed (`<=20 MB`), schema, and digest checks and creates a fresh draft.
- **Internal Callback ([routers/internal.py](../../apps/api/app/routers/internal.py)):** `POST /api/internal/execution/jobs/{job_id}/result` guarded by Traefik `ipAllowList` and HMAC `X-Worker-Token`.

---

## 4. Out-of-Process Execution Worker (`execution/`)

Implemented in [execution/dispatcher/worker.py](../../execution/dispatcher/worker.py), [execution/dispatcher/sandbox.py](../../execution/dispatcher/sandbox.py), and [docker-compose.coding.yml](../../docker-compose.coding.yml):

- **Zero DB Credentials (`T19`):** `dispatcher` connects only to Redis (`lancast:execution:queue`, dead-letter `lancast:execution:dead`), Judge0 (`http://judge0-server:2358`), and the internal API callback.
- **Judge0 Sandbox (`Judge0Runner`):** Executes each hidden test case with `enable_network=False`, `base64_encoded=true`, and per-process CPU/RAM limits (`MAX_MEMORY_LIMIT: 8388608` virtual ceiling for OpenJDK/V8 on cgroup v2 Linux hosts). Never exposes expected outputs in results.

---

## 5. Frontend Portals & Offline Code Editor (`apps/web/src/`)

Built with React 19, Vite 6, TypeScript, and Tailwind CSS v4 using unified **Neutral + Emerald** Light and Dark themes (`styles/globals.css`, `hooks/useTheme.ts`), **zero external CDN dependencies**:

- **Shared Shell & Clients:** [hooks/useAuth.tsx](../../apps/web/src/hooks/useAuth.tsx), [lib/api.ts](../../apps/web/src/lib/api.ts), [lib/autosave.ts](../../apps/web/src/lib/autosave.ts), [components/AppShell.tsx](../../apps/web/src/components/AppShell.tsx), [components/StatusBadge.tsx](../../apps/web/src/components/StatusBadge.tsx).
- **Portals & Workflows:**
  - [LandingPage.tsx](../../apps/web/src/pages/LandingPage.tsx) — Login + first-user Platform Admin bootstrap + system readiness indicator.
  - [AdminPage.tsx](../../apps/web/src/pages/AdminPage.tsx) & [TenantMembersPage.tsx](../../apps/web/src/pages/TenantMembersPage.tsx) + [TenantMembersPanel.tsx](../../apps/web/src/components/TenantMembersPanel.tsx).
  - [OrganizerDashboard.tsx](../../apps/web/src/pages/OrganizerDashboard.tsx), [AssessmentDetail.tsx](../../apps/web/src/pages/AssessmentDetail.tsx), [QuestionEditor.tsx](../../apps/web/src/components/QuestionEditor.tsx) (all 5 types, defaulting coding questions to all 5 supported languages), and [ResultsGradingPage.tsx](../../apps/web/src/pages/ResultsGradingPage.tsx) (candidate answer inspection, file download, manual grading, CSV export).
  - [CandidateHome.tsx](../../apps/web/src/pages/CandidateHome.tsx) (active exams with smart Start/Resume/View Result states + Past Attempts & Submissions table).
  - [ExamRunnerPage.tsx](../../apps/web/src/pages/ExamRunnerPage.tsx) + [CodeEditor.tsx](../../apps/web/src/components/CodeEditor.tsx) (offline CodeMirror 6 with syntax highlighting for Python 3, C, C++, Java, JavaScript and IntelliSense explicitly disabled, Run Code against sample/custom stdin, monotonic autosave, pending-save flush + automatic submission at `00:00`, and 1.5s evaluation status polling).

---

## 6. Key Issues Resolved During Phase 2

1. **Judge0 cgroup v2 compatibility:** Linux kernel `7.2.15` (cgroup v2) broke `isolate --cg` in Judge0 1.13.1 (`No such file or directory` in `/sys/fs/cgroup/memory/`). Resolved via `privileged: true` + `ENABLE_PER_PROCESS_AND_THREAD_TIME_LIMIT=true` and `ENABLE_PER_PROCESS_AND_THREAD_MEMORY_LIMIT=true`.
2. **GCC Unicode compile output & Java/JS `RLIMIT_AS`:** GCC curly quotes (`‘main’`) caused HTTP 201 `"use base64_encoded=true"` errors under `base64_encoded=false`; switching both runners to `base64_encoded=true` and raising virtual memory ceilings (`2048000` KB JS, `8388608` KB Java) enabled all 5 languages live.
3. **Post-submit candidate polling:** Added `GET /api/attempts/{attempt_id}/submission` and 1.5s polling so `ExamRunnerPage` transitions live from `Evaluating` to `Scored`.

---

## 7. Verification Evidence

- **Backend API (`apps/api`):** `uv run ruff check app tests alembic` (0 errors); `uv run pytest -q` (**74/74 passed** covering auth, tenancy isolation, lifecycle, modules, attempts/autosave/CSV/history, uploads/download, capsules, and coding execution); PostgreSQL `alembic check` zero drift.
- **Execution Worker (`execution`):** `uv run ruff check dispatcher tests` (0 errors); `uv run pytest -q` (**6/6 passed**); live Judge0 verification passed for Python 3, C, C++, Java, and JavaScript (`accepted` / `compile_error`).
- **Frontend (`apps/web`):** `npm test` (**5/5 Vitest passed**); `npm run build` (`tsc -b && vite build`) clean; verified live behind Traefik at `http://localhost/`.
