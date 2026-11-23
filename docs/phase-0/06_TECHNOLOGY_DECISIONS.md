# 06 — LANCAST Technology Decisions

**Version:** 1.0 — proposed, to validate during Phase 1

## 1. Principles
Prefer reproducible on-premises deployment, low solo-developer operational complexity, independently testable algorithms, explicit interfaces and pinned dependencies. Start with a modular monolith; isolate untrusted code execution.

## 2. Proposed stack
| Layer | Proposal | Rationale / validation |
|---|---|---|
| Frontend | React + TypeScript (SPA served via nginx) | Familiar component ecosystem; static bundle served cleanly behind Traefik with zero client Internet dependency |
| Backend | Python + FastAPI (modular monolith) | Typed API, async support, Python research ecosystem; hosts local auth, tenancy, assessments and orchestrators |
| Authentication | Local FastAPI auth (PostgreSQL-backed) | Zero external auth dependency; candidate browsers remain LAN-only even if an external DB URL is used later |
| Database | PostgreSQL (local container default; optional external `DATABASE_URL`) | Transactions, relational constraints and tenant data; local by default for offline reliability and clean benchmarks, portable to external Postgres (e.g., Supabase DB URL) via connection string |
| Cache/queue | Redis initially behind an abstraction | Reduce initial components; validate durability/retry semantics |
| Workers | Separate Python dispatcher + execution workers | Keep jobs out of API process; validate isolation and concurrency |
| Code execution | Judge0 (`judge0-server` -> worker -> `isolate`) | Mature sandbox service; supports round-robin/failover baseline and LANCAST capacity-aware dispatch; audit actual isolation |
| Containers | Docker Engine + Compose | Single-host and initial multi-host deployment |
| Reverse proxy | Traefik (`:80` / `:443`) | Single LAN front door routing static SPA and `/api/*` to the FastAPI pool with health checks |
| Metrics | Prometheus | Scrape-based metrics |
| Dashboards | Grafana | Operational and experiment visualization |
| Host metrics | Node Exporter | CPU/RAM/disk/network telemetry |
| Container metrics | cAdvisor or equivalent | Container resource visibility |
| Load testing | Locust | Python-based controlled workloads |
| Tests | Pytest + frontend test framework | Automated unit/integration tests |
| API contract | OpenAPI | Documented interfaces |
| Capsule | Versioned archive + manifest/digest | Portable assessment definitions; validate archive safety |

## 3. Proposed architectural decisions
- **TD-01 Modular monolith first:** identity, tenancy and assessment logic in a modular backend; execution separate. Extract services only when justified by measured scaling/failure needs.
- **TD-02 Docker Compose first:** suitable for standalone and initial central deployment. Compose is not a complete distributed orchestrator; remote worker placement/health must be designed explicitly.
- **TD-03 PostgreSQL authoritative:** store users, tenants, assessments, attempts, submissions, results and audit metadata transactionally.
- **TD-04 Queue abstraction:** define states, retries, idempotency, bounds and dead-letter behavior before binding scheduler to Redis.
- **TD-05 Deterministic algorithms first:** transparent rule-based scheduling/policy decisions before ML.
- **TD-06 Monitoring separate from decisions:** Prometheus/exporters collect telemetry; orchestration consumes normalized metrics and makes decisions.
- **TD-07 Security at authoritative boundaries:** API and execution boundary always enforce mandatory authorization/validation; policy engine cannot bypass access checks.
- **TD-08 Standalone is single-machine:** all required services, including local execution workers, run on one host; no remote worker dependency.

## 4. Alternatives not selected initially
- Kubernetes: adds cluster complexity before it is needed to validate the research.
- RabbitMQ/NATS: may be justified if Redis queue semantics prove insufficient.
- ML/RL scheduler: needs representative data and careful evaluation.
- Custom sandbox from scratch: high security risk.
- Full OpenTelemetry stack: consider later if Prometheus plus structured logs is insufficient.
- External policy engine such as OPA: evaluate if policy complexity warrants it.

## 5. Security/operations constraints
Never commit secrets; do not mount Docker socket into candidate or execution containers; do not run candidate code as root or in API container; disable worker network by default; restrict management interfaces; pin images/dependencies; test backup/restore; document Internet dependencies.

## 6. Open decisions
1. React build tool (Vite SPA confirmed in spirit; finalize exact SPA template/routing setup).
2. Whether Redis is sufficient or a dedicated broker is needed.
3. Judge0 + `isolate` hardening details and resource limit verification.
4. LAN TLS/certificate approach.
5. Audit signing key protection and checkpoint design.
6. Capacity estimator and scheduling algorithm.
7. Numerical SLOs and candidate capacity, established only through pilot measurements.

Resolve each through an ADR: context, alternatives, decision and consequences.
