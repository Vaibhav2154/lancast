# Phase 1 — Architecture and Project Foundation

**Status:** Complete | **Exit Condition:** Repo skeleton, ERD, API contracts, configuration, and test/CI foundation verified against live PostgreSQL, Redis, and Traefik.  
**Key Commits:** `6bf4243`, `8a0cde5`, `a7da783`, `9846d66`, `0c2259e`, `487c06c`

---

## 1. Objectives & Scope

Phase 1 translated the frozen Phase 0 specification (`docs/specifications/`) into a working, runnable software foundation:

- Lock architectural decisions via Architecture Decision Records (`ADR-001`..`ADR-003`).
- Establish the 12-table PostgreSQL core data model (`data-model.md`) with versioned Alembic migrations (`0001_initial_schema.py`).
- Define typed interface contracts decoupling FastAPI business logic from Redis queues and future Resource/Security orchestration engines (`Phase 5` / `Phase 6`).
- Scaffold the FastAPI modular monolith (`apps/api/`), React + Vite + TypeScript SPA (`apps/web/`), Traefik v3.2 reverse proxy (`infrastructure/gateway/`), Docker Compose stack, and GitHub Actions CI.

---

## 2. Locked Architecture Decisions (`docs/architecture/decisions/`)

| ADR | Decisions Covered | Summary |
|---|---|---|
| [ADR-001](../architecture/decisions/ADR-001-stack-and-topology.md) | `O-01`, `O-04` | Traefik front door -> React/Vite SPA (`nginx`) + FastAPI modular monolith pool -> Redis bounded queue -> Judge0 (`isolate`) workers; same code for standalone and central modes. |
| [ADR-002](../architecture/decisions/ADR-002-auth-and-database.md) | `O-02`, `DEP-02`, `DEP-06` | Local PostgreSQL + local FastAPI auth by default for zero runtime Internet dependency; optional external `DATABASE_URL` (e.g., managed Postgres) supported without delegating auth. |
| [ADR-003](../architecture/decisions/ADR-003-audit-signing-and-tls.md) | `O-05`, `O-06` | Traefik `:80` HTTP in dev, `:443` offline private-CA HTTPS in campus LAN; hash-linked `audit_events` anchored by external-key Ed25519 `signed_audit_checkpoints`. |

---

## 3. Core Data Model & Migration (`0001_initial_schema.py`)

Documented in [docs/architecture/data-model.md](../architecture/data-model.md) and implemented in [apps/api/app/db/models.py](../../apps/api/app/db/models.py) + [0001_initial_schema.py](../../apps/api/alembic/versions/0001_initial_schema.py):

| Table | Purpose | Key Invariants |
|---|---|---|
| `tenants` | Independent departments, labs, clubs | Unique `slug`, `is_active` |
| `users` | Local identities | Unique `email`, Argon2 `password_hash`, `is_platform_admin` |
| `memberships` | Tenant-scoped role bindings | `role` (`tenant_admin`, `organizer`, `candidate`), unique `(tenant_id, user_id)` |
| `assessments` | Top-level exam metadata & lifecycle state | `status` (`draft`..`archived`), tenant-scoped |
| `assessment_versions` | Frozen snapshots per publish | Unique `(assessment_id, version_number)`, SHA-256 `canonical_digest`, `is_frozen` |
| `questions` | Pluggable question definitions | `prompt_json` (candidate-safe) vs. `hidden_eval_json` (server-only) |
| `attempts` | Candidate exam instances | Server `started_at`, `deadline_at`, status machine |
| `responses` | Autosaved candidate answers | Unique `(attempt_id, question_id)` |
| `submissions` | Finalized scored submissions | Unique `(attempt_id, idempotency_key)` |
| `execution_jobs` | Async coding evaluation records | `priority_class`, `status`, `worker_id` |
| `audit_events` | Append-oriented security & lifecycle log | `sequence_num` PK, `prev_hash` -> `event_hash` chain |
| `signed_audit_checkpoints` | Cryptographic audit anchors | `up_to_sequence`, `root_hash`, `signature_ed25519`, `key_id` |

---

## 4. Typed Contracts & Configuration (`apps/api/`)

- **Configuration ([app/core/config.py](../../apps/api/app/core/config.py)):** Pydantic `BaseSettings` reading `.env` with validation that PostgreSQL URLs are enforced (`sync_database_url` converts `postgresql+asyncpg://` to `postgresql+psycopg://` for Alembic) and placeholder `auth_secret_key` / `worker_shared_secret` prefixes are rejected when `ENVIRONMENT=production`.
- **Orchestration & Queue Contracts ([app/contracts/interfaces.py](../../apps/api/app/contracts/interfaces.py)):** Pydantic contracts for `WorkloadDescriptor`, `TelemetrySample`, `CapacityEstimate`, `AdmissionDecision`, `ExecutionJobContract`, `CodeTestCase`, `ExecutionJobPayload`, `SchedulingDecision`, `SecurityContext`, `SecurityDecision`, and `ExecutionQueueContract` (`Protocol`).
- **API Skeleton & Observability:**
  - [app/main.py](../../apps/api/app/main.py): FastAPI factory with CORS configured around `PUBLIC_BASE_URL`.
  - [app/routers/health.py](../../apps/api/app/routers/health.py): `GET /api/health` (liveness + active `deployment_profile`) and `GET /api/ready` (injectable PostgreSQL + Redis checks, returning `503` when degraded).
  - [app/core/logging.py](../../apps/api/app/core/logging.py): Structured JSON logging (`NFR-OBS-01`) keeping candidate secrets/bodies out of ordinary logs.

---

## 5. Gateway, Container Stack & CI Foundation

- **Traefik Gateway ([infrastructure/gateway/](../../infrastructure/gateway/)):** Static configuration in `traefik.yml` (file provider, no Docker socket mount, Prometheus metrics enabled) and dynamic routing in `dynamic/routes.yml` (`/api` -> `api:8000`, `/` -> `web:80`, `/api/internal` blocked via `ipAllowList`).
- **Frontend Scaffold (`apps/web/`):** React 19 + Vite + TypeScript + `nginx:1.27-alpine` multi-stage `Dockerfile` and SPA fallback `nginx.conf`.
- **CI ([.github/workflows/ci.yml](../../.github/workflows/ci.yml)):** Automated pipeline running Ruff lint, Alembic `upgrade head` + `alembic check` + `downgrade base` round-trip, Pytest against live PostgreSQL 16 and SQLite, Vite/TypeScript build, and `docker compose config --quiet`.

---

## 6. Verification Evidence

- Backend foundation tests (`test_config_and_contracts.py`, `test_health_api.py`) passed on SQLite and live PostgreSQL 16 (`7/7` in Phase 1).
- Ruff lint and Alembic zero-drift checks passed.
- Live Docker Compose stack verified (`http://localhost/api/ready` returned `{"status":"ready","dependencies":{"postgres":"ok","redis":"ok"}}` after `0001_initial_schema` migration).
