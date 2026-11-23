# LANCAST — Project Status and Phase Tracker

**Current phase:** Phase 0 — Research and Requirements Finalization  
**Status:** In progress | **Last updated:** 23 November 2026

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
| 0 | Research and requirements | In progress | Six planning documents reviewed; literature gap and testbed clarified |
| 1 | Architecture and foundation | Not started | Repo skeleton, ERD, API contracts, configuration and test foundation |
| 2 | Assessment platform | Not started | Multi-tenant assessment lifecycle and modules work |
| 3 | Infrastructure/deployment | Not started | Central and standalone profiles deploy reproducibly |
| 4 | Monitoring/telemetry | Not started | Required metrics collected and validated |
| 5 | Resource orchestration | Not started | Estimator, readiness, admission and scheduler tested |
| 6 | Security orchestration | Not started | Context policies, replay controls and audit integrity tested |
| 7 | Integration/control plane | Not started | Application and both engines operate together |
| 8 | Experimental evaluation | Not started | Baselines, workloads, scenarios and reproducible results complete |
| 9 | Research/finalization | Not started | Manuscript, docs and demonstration ready |

## Phase 0 checklist
- [ ] Review/approve SRS.
- [ ] Review/approve research specification.
- [ ] Review architecture and deployment topologies.
- [ ] Review threat model.
- [ ] Review experiment plan.
- [ ] Review technology decisions.
- [ ] Conduct focused literature review with verified sources.
- [ ] Record actual development/test hardware and LAN topology.
- [ ] Resolve decisions blocking Phase 1.
- [ ] Freeze Phase 0 and record approval.

## Open decisions
| ID | Decision | Proposed resolution |
|---|---|---|
| O-01 | Frontend framework | Choose simplest option meeting UI/routing needs |
| O-02 | Local identity in standalone | **Resolved:** Local FastAPI authentication backed by PostgreSQL (same in central and standalone; optional external `DATABASE_URL` does not change local auth) |
| O-03 | Execution backend | Judge0 + `isolate` selected; audit and document isolation limits in Phase 1/3 |
| O-04 | Queue/broker | Define queue contract, then select implementation |
| O-05 | LAN TLS | Decide based on campus certificate/private CA availability |
| O-06 | Audit key protection | Choose protected signing/checkpoint approach |
| O-07 | Test hardware | Record actual machine specifications and topology |
| O-08 | Numerical SLOs | Establish from pilot measurements; do not invent |

## Change log
| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-11-23 | Initial Phase 0 package; project named LANCAST; standalone confirmed as single-machine deployment |
| 1.1 | 2026-11-23 | Locked in Traefik + React SPA (nginx) + FastAPI pool + Judge0 topology; confirmed local PostgreSQL + local FastAPI auth by default with optional external `DATABASE_URL` |

## Working rule
A phase is not complete because code has been generated. It is complete only when acceptance criteria are demonstrated with tests, evidence and updated documentation.
