# LANCAST — Project Status and Phase Tracker

**Current phase:** Phase 3 — Infrastructure and Deployment  
**Status:** In progress | **Last updated:** 24 November 2026

## Confirmed decisions
- [x] Project name: LANCAST.
- [x] Central campus deployment over LAN/Wi-Fi.
- [x] Central deployment may attach separate execution workers.
- [x] Standalone is one physical/virtual server with all required services local.
- [x] Both deployment modes share application and orchestration code.
- [x] Both research contributions are in scope.
- [x] One developer owns the project.
- [x] Work is phase-based; no fixed two-week completion promise.
- [x] Reference repositories are not assumed to be the final implementation.
- [x] Gateway & app topology: Traefik front door -> React SPA (nginx) + FastAPI modular monolith pool -> Redis/bounded queue + adaptive dispatcher -> Judge0 (`isolate`) compiler pool.
- [x] Database & auth: Local PostgreSQL + local FastAPI authentication by default (zero Internet dependency); optional external PostgreSQL (e.g. Supabase `DATABASE_URL`) supported later as a DB connection string only, with auth remaining local.

## Phase tracker
| Phase | Name | Status | Exit condition |
|---|---|---|---|
| 0 | Research and requirements | Complete | Six planning documents reviewed; literature gap and testbed clarified |
| 1 | Architecture and foundation | Complete | Repo skeleton, ERD, API contracts, configuration and test foundation |
| 2 | Assessment platform | Complete | Multi-tenant assessment lifecycle and modules work |
| 3 | Infrastructure/deployment | In progress | Central and standalone profiles deploy reproducibly |
| 4 | Monitoring/telemetry | Not started | Required metrics collected and validated |
| 5 | Resource orchestration | Not started | Estimator, readiness, admission and scheduler tested |
| 6 | Security orchestration | Not started | Context policies, replay controls and audit integrity tested |
| 7 | Integration/control plane | Not started | Application and both engines operate together |
| 8 | Experimental evaluation | Not started | Baselines, workloads, scenarios and reproducible results complete |
| 9 | Research/finalization | Not started | Manuscript, docs and demonstration ready |

## Phase 0 checklist
- [x] Review/approve SRS.
- [x] Review/approve research specification.
- [x] Review architecture and deployment topologies.
- [x] Review threat model.
- [x] Review experiment plan.
- [x] Review technology decisions.
- [x] Conduct focused literature review with verified sources (`07_LITERATURE_REVIEW.md`; full-PDF verification of provisional papers tracked for manuscript phase).
- [x] Record actual development/test hardware and LAN topology (`08_TESTBED_MANIFEST.md`).
- [x] Resolve decisions blocking Phase 1 (`O-01`, `O-02`, `O-04`, `O-05`, `O-06`, `O-07`).
- [x] Freeze Phase 0 and record approval (24 November 2026).

## Open decisions
| ID | Decision | Status / Resolution |
|---|---|---|
| O-01 | Frontend framework | **Resolved:** React + Vite + TypeScript SPA served via nginx behind Traefik |
| O-02 | Local identity in standalone | **Resolved:** Local FastAPI authentication backed by PostgreSQL (same in central and standalone; optional external `DATABASE_URL` does not change local auth) |
| O-03 | Execution backend | Judge0 + `isolate` selected; audit and document isolation limits in Phase 1/3 |
| O-04 | Queue/broker | **Resolved (Phase 1–2):** Redis behind an explicit queue abstraction |
| O-05 | LAN TLS | **Resolved:** Traefik `:80` HTTP for local dev; `:443` HTTPS with local/private CA cert (`mkcert` or campus IT CA) via file provider for LAN deployments |
| O-06 | Audit key protection | **Resolved:** Ed25519 signing key mounted as read-only secret outside DB/app user + periodic signed checkpoints |
| O-07 | Test hardware | **Resolved (dev/standalone):** Recorded in `08_TESTBED_MANIFEST.md` (i7-11800H 8C/16T, 16 GB RAM, NVMe, Omarchy 4.5.0, Docker 29.9.2 / Compose 5.6.1) |
| O-08 | Numerical SLOs | Deferred to pilot measurements; do not invent |

## Change log
| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-11-23 | Initial Phase 0 package; project named LANCAST; standalone confirmed as single-machine deployment |
| 1.1 | 2026-11-23 | Locked in Traefik + React SPA (nginx) + FastAPI pool + Judge0 topology; confirmed local PostgreSQL + local FastAPI auth by default with optional external `DATABASE_URL` |
| 1.2 | 2026-11-24 | Added focused literature review and gap analysis (`07_LITERATURE_REVIEW.md`) integrating domain PDF papers with resource QoS, Zero Trust/context-aware access control, and tamper-evident logging literature |
| 1.3 | 2026-11-24 | Recorded local dev/standalone testbed manifest (`08_TESTBED_MANIFEST.md`), populated `docs/phase-0/README.md`, and resolved Phase 1 blocking decisions (`O-01`, `O-04`, `O-05`, `O-06`, `O-07`) |
| 1.4 | 2026-11-24 | Phase 0 approved and frozen; started Phase 1 (Architecture and Project Foundation) |
| 1.5 | 2026-11-24 | Scaffolded Phase 1 foundation: ERD, ADR-001..003, FastAPI modular monolith + 12-table Alembic schema + Pytest suite (7/7 passing), React/Vite SPA + nginx, Traefik gateway, and Docker Compose |
| 1.6 | 2026-11-24 | Added GitHub Actions CI workflow (`.github/workflows/ci.yml`) covering Ruff lint, Pytest, Alembic SQL check, Vite/TS build, and Compose validation |
| 1.7 | 2026-11-24 | Verified live Docker Compose stack (`/api/ready` green, `0001_initial_schema` migrated), renamed `docs/phase-0/` to `docs/specifications/`, froze Phase 1, and started Phase 2 |
| 2.0 | 2026-11-24 | Completed Phase 2 backend & execution worker (local Argon2/JWT auth + revocable sessions, tenant RBAC + cross-tenant audit denials, immutable assessment versions + SHA-256 digests, 5 pluggable question modules, idempotent autosave/submit, safe uploads, capsules, out-of-process Judge0 dispatcher, 68 API tests on SQLite & Postgres + 6 worker tests, zero Alembic drift, CI updated); Phase 2 frontend portals pending |
| 2.1 | 2026-11-24 | Completed Phase 2 React + Vite + Tailwind v4 frontend portals (Auth/Bootstrap, Platform & Tenant Admin, Organizer Dashboard + 5-type Question Editor + Capsules + Results/Grading, Candidate Home + Distraction-Free Exam Runner with monotonic autosave & idempotent submit, Neutral+Emerald Light/Dark themes, 5 Vitest tests, CI updated, live Docker/Traefik verified); froze Phase 2 and started Phase 3 |

## Working rule
A phase is not complete because code has been generated. It is complete only when acceptance criteria are demonstrated with tests, evidence and updated documentation.
