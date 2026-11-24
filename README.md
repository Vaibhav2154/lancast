# LANCAST
### An Adaptive Resource and Security Orchestration Framework for Multi-Tenant Campus Assessment Systems

LANCAST is a self-hosted, LAN-first assessment platform for colleges, departments, faculty groups, and student organizations. It combines multi-tenant assessment management with two research subsystems: **Capacity-Aware Adaptive Resource Orchestration** and **Assessment-Aware Security and Integrity Orchestration**.

> **Status:** Phase 3 — Infrastructure and Deployment (Phases 0–2 complete)  
> **Development:** Solo developer, phase-driven  
> **Deployment:** Centralized campus deployment and standalone single-machine deployment

---

## Table of Contents
1. [Overview](#1-overview)
2. [Problem Statement](#2-problem-statement)
3. [Objectives](#3-objectives)
4. [Research Contributions](#4-research-contributions)
5. [Features](#5-features)
6. [Deployment Models](#6-deployment-models)
7. [Architecture](#7-architecture)
8. [Technology Stack](#8-technology-stack)
9. [Repository Structure](#9-repository-structure)
10. [Development Roadmap](#10-development-roadmap)
11. [Research Evaluation](#11-research-evaluation)
12. [Security Principles](#12-security-principles)
13. [Getting Started](#13-getting-started)
14. [Configuration](#14-configuration)
15. [Testing](#15-testing)
16. [Documentation](#16-documentation)
17. [Development Workflow](#17-development-workflow)
18. [Current Status](#18-current-status)
19. [Limitations](#19-limitations)
20. [Future Work](#20-future-work)
21. [Contributing](#21-contributing)
22. [License](#22-license)

---

## 1. Overview

Campus assessment platforms may run several assessments simultaneously on limited local infrastructure. Their workloads differ:

- MCQ assessments generate frequent, latency-sensitive answer requests.
- Descriptive assessments generate larger text submissions and periodic saves.
- File-upload assessments consume storage and network bandwidth.
- Programming assessments generate CPU- and memory-intensive execution jobs.

Generic request scheduling and fixed worker limits can allow expensive operations to interfere with essential candidate interactions. Shared infrastructure also introduces risks involving tenant isolation, unauthorized access, malicious files and code, submission replay, assessment tampering, and audit integrity.

LANCAST aims to provide an assessment platform that understands these workload differences and coordinates infrastructure and security decisions accordingly.

### Principles
- **LAN-first:** designed for campus networks.
- **Self-hosted:** core services run on institution-controlled infrastructure.
- **Multi-tenant:** organizations share infrastructure without sharing unauthorized data.
- **Assessment-aware:** decisions consider assessment type, operation, and attempt context.
- **Observable:** decisions and system behavior are measurable and auditable.
- **Portable:** assessment definitions can be transferred using Assessment Capsules.
- **Evidence-driven:** performance and security claims require repeatable experiments.

## 2. Problem Statement

Campus assessment platforms may need to support concurrent assessments on limited local infrastructure. Heterogeneous workloads have different resource demands and service-quality requirements. Static resource limits and generic scheduling can allow code execution or uploads to interfere with latency-sensitive answer saving.

The platform must also protect tenant data, questions, submissions, execution infrastructure, and audit records against unauthorized access, replay, abuse, and tampering.

**Research problem:** How can a self-hosted assessment platform dynamically manage infrastructure resources and enforce context-aware security policies to provide reliable, secure, and fair assessment experiences across concurrent assessments in resource-constrained local-network environments?

## 3. Objectives

### Product objectives
- Provide browser-based organizer, candidate, and administrator interfaces.
- Support independent tenants such as departments, faculty groups, and clubs.
- Support MCQ, multiple-select, descriptive, file-upload, and programming assessments.
- Support concurrent assessments with separate configurations and candidate groups.
- Provide central deployment with optional separate execution workers.
- Provide standalone deployment with all required services on one machine.
- Provide portable, versioned assessment packages.
- Minimize infrastructure configuration required from assessment organizers.

### Research objectives
- Characterize assessment workloads and infrastructure capacity.
- Estimate whether planned assessments fit available infrastructure.
- Apply pre-event admission control.
- Adapt runtime scheduling and execution concurrency.
- Apply security policies based on assessment context and observed risk.
- Protect submissions and assessment records against defined replay and tampering scenarios.
- Compare proposed mechanisms against explicit baselines.

## 4. Research Contributions

### 4.1 Capacity-Aware Adaptive Resource Orchestration

This subsystem manages infrastructure based on assessment workload characteristics.

1. **Infrastructure profiling:** CPU, memory, disk, network, service health, and worker availability.
2. **Workload characterization:** expected candidates, assessment mix, autosave rates, upload volume, coding demand, and event duration.
3. **Pre-event capacity estimation:** compare expected demand with empirically measured operating envelopes; identify bottlenecks and uncertainty.
4. **Readiness and admission control:** accept, warn, defer, or reject proposed assessments with explanations.
5. **Runtime scheduling:** distinguish latency-sensitive operations from expensive/background jobs; use bounded queues and resource budgets.
6. **Adaptive concurrency:** adjust execution concurrency and dispatch decisions using measured system state.
7. **Fairness and feedback:** measure service quality across tenants or workload classes and compare predicted with observed demand.

The initial algorithm should be deterministic and explainable. Inputs, thresholds, decision intervals, safety margins, and fallback behavior must be documented. Machine learning is not required for novelty.

### 4.2 Assessment-Aware Security and Integrity Orchestration

This subsystem evaluates security policy using assessment and operation context.

1. **Context extraction:** tenant, actor, role, assessment type, attempt state, operation, and deployment context.
2. **Policy selection:** apply appropriate policies to MCQ, descriptive, file-upload, coding, and administrative operations.
3. **Risk signals:** repeated invalid requests, probing, replay attempts, unusual request bursts, unauthorized object access, and cross-tenant access attempts.
4. **Proportional enforcement:** allow and monitor, reject, throttle, reauthenticate, flag for review, or alert.
5. **Integrity protection:** versioned assessment configuration, canonical digests, replay-resistant submissions, and tamper-evident audit events with protected checkpoints.
6. **Execution security:** isolated, ephemeral, least-privilege execution with resource limits and network disabled by default.
7. **Auditability:** record decision reasons, relevant evidence metadata, and policy versions.

Weak client-side signals or temporary network failures must not automatically be treated as proof of candidate misconduct.

### 4.3 Novelty boundary

LAN exams, multi-tenancy, containers, monitoring, queues, load balancing, Zero Trust concepts, hashes, and sandboxing are established techniques. LANCAST does not claim these individually as novel. The intended contribution is the **assessment-specific decision and orchestration mechanism** connecting heterogeneous workloads, measured capacity, admission/runtime scheduling, and context-aware security/integrity policies, followed by comparative evaluation.

## 5. Features

### Assessment management
- Multi-tenant organizations and memberships.
- Role-based access control and tenant-scoped records.
- Assessment creation, editing, preview, publication, start, close, and archive.
- Candidate assignment or controlled joining.
- Attempt management, autosave, submission, evaluation, and results.
- Versioned published assessment configuration.

### Assessment modules

| Type | Capabilities |
|---|---|
| MCQ | Single-answer questions and scoring |
| Multiple-select | Multiple correct options and configurable scoring |
| Descriptive | Text responses and evaluation |
| File upload | Validated file submission with size/type limits |
| Programming | Language selection, isolated execution, test cases, evaluation |

Modules should implement a documented interface so new question types can be added without rewriting the assessment lifecycle.

### Assessment Capsule

A versioned portable package containing assessment metadata, questions, assets, evaluation configuration, and execution requirements. It must exclude candidate credentials, live candidate records, and active attempts. Import must validate the package and create a new assessment instance rather than silently overwriting an existing one.

### Organizer
Create/configure assessments, manage candidates, publish events, view readiness reports, monitor progress, review results, and import/export capsules.

### Candidate
Join authorized assessments, view instructions/questions, submit responses, receive save-status feedback, upload permitted files, and submit programming solutions.

## 6. Deployment Models

Both deployment modes use the same application and orchestration code. Only topology and configuration differ.

### 6.1 Centralized campus deployment

A central server (or gateway + app pool) hosts the Traefik reverse proxy, React SPA (nginx), FastAPI application pool, PostgreSQL, Redis, monitoring/control plane, and orchestration services. Separate Judge0 execution worker machines may be attached. Candidates and organizers connect over campus LAN/Wi-Fi with no Internet access required on candidate machines.

```text
Candidate / Organizer Browsers (LAN only, no Internet required)
        │   http(s)://<GATEWAY_LAN_IP>/
        ▼
┌──────────────────────────────────────────────────────────┐
│ GATEWAY (Traefik :80/:443 + React SPA via nginx)         │
└──────────────────────────┬───────────────────────────────┘
                           │ /api/*
                           ▼
┌──────────────────────────────────────────────────────────┐
│ APP POOL (FastAPI modular monolith: app-1 .. app-N)      │
│  • Local Auth/Tenancy, Assessments, Attempts, Capsules   │
│  • Security & Integrity Orchestrator + Audit             │
│  • Resource Orchestrator (Estimator, Admission, Policy)  │
└───┬──────────────────────┬───────────────────────┬───────┘
    │                      │                       │
    ▼                      ▼                       ▼
PostgreSQL             Redis / Bounded         Telemetry
(local default;        Execution Queue         (Prometheus +
 optional cloud DB)        │                    Exporters)
                           ▼
                Adaptive Execution Dispatcher
                 (baseline: round-robin/failover
                  vs. LANCAST: capacity-aware)
                           │
                           ▼
             COMPILER POOL (Judge0 + isolate)
              • Central: worker nodes 1..N
```

Adding workers does not automatically increase API, database, or network capacity; each layer must be measured.

### 6.2 Standalone single-machine deployment

All services required by enabled features run on **one physical or virtual machine/server** with zero Internet dependency during operation: Traefik, React SPA (nginx), a single FastAPI instance, local PostgreSQL (with local FastAPI auth), Redis, orchestration, monitoring, and a local Judge0 (`isolate`) execution container when coding assessments are enabled. A separate worker machine is not required.

```text
Browsers (Local LAN) -> Traefik (:80/:443) -> React SPA (nginx) / FastAPI API
                                                   |-> Local PostgreSQL (local auth)
                                                   |-> Local Redis / Bounded Queue
                                                   |-> Resource & Security Orchestrators
                                                   |-> Local Judge0 + isolate worker
                                                   |-> Local Prometheus / Exporters
```

Standalone has a single-machine resource and failure boundary. Capacity/admission controls must account for that constraint.

| Property | Centralized | Standalone |
|---|---|---|
| Application/API | Central server | Same machine |
| Database/queue | Central/configured | Same machine |
| Execution workers | May be remote machines | Same machine |
| Worker expansion | Separate machines possible | No separate worker machine |
| Typical use | Campus-wide | Small/local deployment |

## 7. Architecture

### Logical components
1. **Frontend:** organizer, candidate, and administration portals.
2. **Application API:** identity integration, tenant authorization, assessment lifecycle, attempts, submissions, and results.
3. **Assessment modules:** question types, evaluation, and capsules.
4. **Resource orchestrator:** telemetry, profiling, workload characterization, capacity estimation, admission, scheduling, worker management, and fairness.
5. **Security orchestrator:** context resolution, policy selection, risk evaluation, enforcement, integrity verification, and audit.
6. **Execution subsystem:** job dispatch and isolated code execution.
7. **Infrastructure/control plane:** deployment profiles, gateway, machine/worker registration, health checks, and telemetry agents.
8. **Data/observability:** persistent state, metrics, logs, and audit evidence.

### Architectural principles
- Start with a modular monolith for the core application.
- Keep untrusted code execution outside the API process.
- Keep both research engines independently testable.
- Use explicit interfaces and versioned contracts.
- Enforce tenant authorization at every protected server-side operation.
- Missing telemetry must not cause unsafe or unbounded scheduling.
- Internal management services must not be exposed to candidate clients.
- Both deployment profiles share application logic.

## 8. Technology Stack

Core stack choices are recorded in [06_TECHNOLOGY_DECISIONS.md](docs/specifications/06_TECHNOLOGY_DECISIONS.md) and formalized in [docs/architecture/decisions/](docs/architecture/decisions/).

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript (SPA served via nginx) |
| Backend | Python + FastAPI (modular monolith) |
| Authentication | Local FastAPI auth (PostgreSQL-backed; no external auth dependency) |
| Database | PostgreSQL (local container default; optional external `DATABASE_URL` such as Supabase Postgres) |
| Queue/cache | Redis initially, behind an abstraction |
| Workers | Separate Python dispatcher + execution workers |
| Code execution | Judge0 (`judge0-server` -> worker -> `isolate`) |
| Containers | Docker Engine + Docker Compose |
| Reverse proxy | Traefik (`:80` / `:443`) |
| Metrics | Prometheus |
| Dashboards | Grafana |
| Host metrics | Node Exporter |
| Container metrics | cAdvisor or equivalent |
| Load testing | Locust |
| Backend testing | Pytest |
| API contract | OpenAPI |

Avoid Kubernetes, unnecessary microservices, and custom sandboxing until a demonstrated requirement justifies them. Pin dependencies and container versions for reproducibility.

## 9. Repository Structure

Target layout; introduce directories as needed rather than creating everything at the start.

```text
lancast/
├── apps/
│   ├── web/
│   └── api/
├── modules/
│   ├── identity/
│   ├── tenancy/
│   ├── assessments/
│   │   ├── mcq/
│   │   ├── multiple_select/
│   │   ├── descriptive/
│   │   ├── file_upload/
│   │   ├── coding/
│   │   └── capsules/
│   └── submissions/
├── orchestration/
│   ├── resource/
│   │   ├── telemetry/
│   │   ├── profiling/
│   │   ├── workload/
│   │   ├── capacity/
│   │   ├── admission/
│   │   ├── scheduling/
│   │   └── fairness/
│   └── security/
│       ├── context/
│       ├── policies/
│       ├── risk/
│       ├── enforcement/
│       ├── integrity/
│       └── audit/
├── execution/
│   ├── dispatcher/
│   └── workers/
├── infrastructure/
│   ├── compose/
│   ├── gateway/
│   ├── monitoring/
│   ├── agents/
│   └── profiles/
│       ├── standalone/
│       └── central/
├── control_plane/
├── shared/
│   ├── schemas/
│   ├── events/
│   └── configuration/
├── experiments/
│   ├── workloads/
│   ├── baselines/
│   ├── resource/
│   └── security/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   ├── load/
│   └── resilience/
├── docs/
│   ├── specifications/
│   ├── architecture/
│   ├── research/
│   ├── security/
│   ├── deployment/
│   └── user-guides/
├── docker-compose.yml
├── .env.example
├── LICENSE
└── README.md
```

## 10. Development Roadmap

The project is developed by one person through phases with explicit exit criteria. There is no fixed two-week completion promise. Testing and documentation continue throughout.

### Phase 0 — Research and Requirements Finalization
**Objective:** Establish a defensible research scope and agreed product specification.

Activities:
- Define problem statement, research questions, hypotheses, and contributions.
- Review related work and identify research gaps.
- Finalize functional/non-functional requirements.
- Define centralized and standalone deployment.
- Prepare architecture, threat model, and experiment plan.
- Record provisional technology decisions.

Deliverables:
- Software Requirements Specification.
- Research specification and literature review.
- System architecture.
- Threat model.
- Experimental evaluation plan.
- Technology decisions and project tracker.

**Exit criteria:** scope and deployment modes are unambiguous; hypotheses are measurable; requirements and architecture are reviewed; evaluation methodology and blocking decisions are documented.

### Phase 1 — Architecture and Project Foundation
**Objective:** Establish repository, domain model, interfaces, development environment, and test foundation.

Activities:
- Initialize repository, coding conventions, frontend/backend foundations.
- Define configuration and environment management.
- Design database ERD and migrations.
- Define identity, tenancy, assessment, and submission boundaries.
- Define API, event, and queue contracts.
- Establish logging, health checks, tests, Compose development environment, and ADRs.

Deliverables: working development environment, repository structure, initial schema/migrations, API contracts, configuration templates, automated tests, and CI foundation.

**Exit criteria:** frontend/backend start reproducibly; migrations work from clean state; health/config validation works; tests run; interfaces are documented.

### Phase 2 — Core Assessment Platform
**Objective:** Build the functional multi-tenant assessment application.

Activities:
- Authentication, roles, tenant/membership management and tenant isolation.
- Assessment creation, lifecycle, and versioning.
- Candidate assignment/joining and attempt state.
- MCQ, multiple-select, descriptive, upload, and coding modules.
- Autosave, submission, evaluation, results, and organizer/candidate interfaces.
- Assessment Capsule export/import foundation.

Deliverables: working multi-tenant workflow, assessment modules, candidate lifecycle, organizer UI, Capsule format, and automated tests.

**Exit criteria:** organizer creates/publishes an assessment; authorized candidate completes it; responses persist; versioning works; cross-tenant tests pass; code runs outside API process.

### Phase 3 — Infrastructure and Deployment
**Objective:** Make both deployment modes reproducible.

Activities:
- Standalone Compose profile.
- Centralized deployment profile.
- Reverse proxy and LAN access.
- Local dependencies and local execution workers for standalone.
- Central worker registration/communication.
- Firewall/service exposure rules.
- Startup, shutdown, backup, recovery and dependency documentation.

Deliverables: standalone and central profiles, gateway config, worker procedure, backup/recovery procedure and deployment guide.

**Exit criteria:** standalone runs all required services on one machine; central can use separate workers; LAN access works; internal services are appropriately restricted; clean deployment is reproducible.

### Phase 4 — Monitoring and Telemetry
**Objective:** Establish reliable infrastructure and workload telemetry.

Activities:
- Host, container, API, database, queue and worker metrics.
- Normalized telemetry schemas.
- Machine/worker health reporting.
- Dashboards, alerts, stale/missing-data validation.
- Telemetry retention and privacy boundaries.

Deliverables: telemetry pipeline, health reporting, dashboards, normalized interfaces and tests.

**Exit criteria:** required metrics are collected and attributable; stale/missing telemetry is detected; monitoring overhead is measured; sensitive candidate data is excluded.

### Phase 5 — Capacity-Aware Resource Orchestration
**Objective:** Implement and evaluate research contribution A.

Activities:
- Define workload descriptors/classes.
- Build infrastructure profiling and capacity profiles.
- Establish empirical operating envelopes through pilot benchmarks.
- Implement capacity estimation, readiness, and admission.
- Classify latency-sensitive and resource-intensive operations.
- Implement bounded queues, budgets, adaptive concurrency and scheduling.
- Implement safe fallback, decision explanations and fairness metrics.

Deliverables: workload model, capacity estimator, readiness/admission controller, adaptive scheduler, decision records, tests and initial evaluation.

**Exit criteria:** estimates are compared with observations; admission is explainable; scheduler uses measured state and bounded rules; FIFO/static baselines exist; mixed workloads and telemetry failures are tested.

### Phase 6 — Security and Integrity Orchestration
**Objective:** Implement and evaluate research contribution B.

Activities:
- Define security context and policy schemas.
- Implement policy registry/versioning, context selection and risk signals.
- Implement proportional enforcement.
- Strengthen tenant/object authorization tests.
- Implement replay-resistant submissions.
- Implement assessment configuration integrity and tamper-evident audit checkpoints.
- Harden execution and file handling.
- Add review/audit interfaces and measure overhead/false positives.

Deliverables: context resolver, policy engine, risk processor, enforcement adapters, replay controls, integrity/audit mechanisms and evaluation.

**Exit criteria:** defined scenarios are detected/blocked; false positives are measured; decisions have reason codes and policy versions; replay/tamper scenarios pass; key protection and review paths are documented.

### Phase 7 — Integration and Unified Control Plane
**Objective:** Integrate assessment workflows, infrastructure and both orchestration engines.

Activities:
- Connect assessment events to workload characterization.
- Connect telemetry to capacity and scheduling.
- Connect security context to API operations.
- Integrate admission into assessment lifecycle.
- Integrate scheduler with execution dispatch.
- Add unified operations views.
- Test tenant isolation, degraded modes and both deployment profiles.

Deliverables: integrated control flow, operations views, end-to-end tests, failure/recovery tests and updated documentation.

**Exit criteria:** both engines operate on real workflows; decisions are enforced at authoritative boundaries; failures degrade safely; both deployment modes are verified.

### Phase 8 — Experimental Evaluation
**Objective:** Produce reproducible evidence for or against research hypotheses.

Activities:
- Freeze baselines and testbed manifests.
- Generate repeatable workloads.
- Compare FIFO, static and proposed scheduling.
- Evaluate capacity-estimation accuracy.
- Run multi-tenant/mixed workloads.
- Execute authorized security/integrity scenarios.
- Measure precision, recall, false positives and overhead.
- Run combined experiments and ablations.
- Analyze validity threats and preserve raw data.

Deliverables: workload scripts, manifests, raw data, analysis scripts, plots, comparative tables, security report and reproducibility notes.

**Exit criteria:** fair baseline comparisons; repeated runs and percentile metrics; false positives/overhead reported; hypotheses evaluated; limitations documented.

### Phase 9 — Research and Finalization
**Objective:** Prepare for demonstration, academic review and possible publication.

Activities:
- Consolidate literature review.
- Document final architecture and algorithms.
- Write methodology, implementation, results and limitations.
- Prepare project report and research manuscript.
- Prepare demonstration scenarios and user/operator guides.
- Review code quality, security findings and reproducibility.
- Tag a stable release.

Deliverables: project report, manuscript draft, architecture/algorithm docs, installation/user docs, demo environment, final evaluation and release.

**Exit criteria:** deployment/demo reproducible from docs; research claims supported by results; limitations disclosed; experiments reproducible; report and presentation complete.

## 11. Research Evaluation

### Resource baselines
- **FIFO:** arrival-order dispatch with fixed execution capacity.
- **Static concurrency:** fixed worker/concurrency and resource limits.
- **Proposed adaptive scheduler:** assessment-aware classes, bounded queues, admission, and runtime adaptation.

### Workload classes
Interactive MCQ, descriptive responses, file uploads, programming execution, and mixed multi-tenant workloads.

### Resource metrics
P50/P95/P99 latency, throughput, queue wait, deadline misses, errors, CPU/RAM/disk/network use, worker utilization, per-tenant service quality/fairness, estimation error, and false-safe capacity decisions.

### Security scenarios
Cross-tenant access, unauthorized question access, replayed submissions, probing, request bursts, malformed uploads, assessment tampering, audit modification in a test copy, sandbox abuse, and legitimate retries/network interruptions.

### Security metrics
True/false positives and negatives, precision, recall, F1, detection/containment time, replay rejection, integrity detection, added latency/resource overhead, and impact on legitimate operations.

### Reproducibility
Preserve hardware/network manifests, software versions, commit IDs, configs, workload definitions/seeds, raw CSV/JSON, analysis scripts, plots, failed runs, and limitations. Capacity claims apply only to tested configurations.

## 12. Security Principles

- Treat the campus LAN as transport, not proof of identity.
- Enforce authorization server-side for every protected operation.
- Derive tenant scope from authenticated membership.
- Keep hidden questions and test cases server-side.
- Make submissions idempotent and attempt-state-aware.
- Execute candidate code outside the application process.
- Use least privilege and resource limits.
- Disable execution network access by default.
- Never mount the Docker socket into candidate/execution containers.
- Keep secrets out of source control and logs.
- Validate uploaded files and imported archives.
- Protect audit checkpoint signing keys.
- Provide human review for consequential security flags.
- A hash chain alone does not stop a privileged attacker rewriting the entire chain.

## 13. Getting Started

### Prerequisites
- Git
- Docker Engine and Docker Compose plugin
- Python 3.12+ (for local backend development/tests)
- Node.js 22+ (for local frontend development/builds)

### Clone
```bash
git clone <LANCAST_REPOSITORY_URL>
cd lancast
```

### Configure
Copy the environment template and replace placeholder passwords/secrets:
```bash
cp .env.example .env
```
Never commit `.env`. Avoid unescaped `$` characters in `.env` passwords (or escape as `$$` for Docker Compose).

### Start (Standalone Docker Compose)
```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
```

Open:
- **Web UI:** `http://localhost/`
- **API Health:** `http://localhost/api/health`
- **API Readiness:** `http://localhost/api/ready`
- **OpenAPI Docs:** `http://localhost/api/docs`

### Run Tests & Lint Locally
```bash
# Backend (from apps/api)
ruff check app tests alembic
pytest -v

# Frontend (from apps/web)
npm install && npm run build
```

## 14. Configuration

Environment-specific configuration should cover:
- Application environment and public base URL.
- Database and queue/cache connections.
- Authentication/session secrets.
- Assessment defaults.
- Execution time, memory, process and output limits.
- Worker registration and communication.
- Resource thresholds and scheduling intervals.
- Security policies.
- Telemetry endpoints and retention.
- Deployment profile (`standalone` or `central`).

Never commit real secrets. Keep `.env.example` to placeholders and safe defaults. Document all external dependencies and protect signing keys and machine credentials.

## 15. Testing

Testing is continuous throughout development.

- **Unit:** domain logic, modules, estimator, admission, scheduler, policies, integrity and idempotency.
- **Integration:** authentication, tenant scoping, assessment lifecycle, submissions, queue/workers, migrations and capsules.
- **Security:** cross-tenant access, unauthorized objects, replay, upload validation, execution isolation, rate limits and audit integrity.
- **Load/resilience:** concurrent candidates, mixed workloads, worker saturation, resource pressure, queue buildup, telemetry loss and service interruption.

A feature is complete only when implementation, tests, authorization/failure behavior, operational evidence and documentation exist.

## 16. Documentation

### Specifications & Planning (`docs/specifications/`)
- [01_PROJECT_SRS.md](docs/specifications/01_PROJECT_SRS.md) — functional and non-functional requirements.
- [02_RESEARCH_SPECIFICATION.md](docs/specifications/02_RESEARCH_SPECIFICATION.md) — research questions, hypotheses, and contributions.
- [03_SYSTEM_ARCHITECTURE.md](docs/specifications/03_SYSTEM_ARCHITECTURE.md) — logical architecture and deployment models.
- [04_THREAT_MODEL.md](docs/specifications/04_THREAT_MODEL.md) — assets, trust boundaries, threats, and mitigations.
- [05_EXPERIMENT_PLAN.md](docs/specifications/05_EXPERIMENT_PLAN.md) — baselines, workloads, metrics, and analysis.
- [06_TECHNOLOGY_DECISIONS.md](docs/specifications/06_TECHNOLOGY_DECISIONS.md) — stack decisions and open ADRs.
- [07_LITERATURE_REVIEW.md](docs/specifications/07_LITERATURE_REVIEW.md) — focused literature review and gap analysis across all three research pillars.
- [08_TESTBED_MANIFEST.md](docs/specifications/08_TESTBED_MANIFEST.md) — local dev/standalone hardware manifest and central testbed template.
- [PROJECT_STATUS.md](docs/specifications/PROJECT_STATUS.md) — phase tracker, confirmed decisions, and open items.

### Architecture & ADRs (`docs/architecture/`)
- [data-model.md](docs/architecture/data-model.md) — core ERD, tables, and integrity invariants.
- [ADR-001-stack-and-topology.md](docs/architecture/decisions/ADR-001-stack-and-topology.md) — Traefik, React/Vite SPA, FastAPI modular monolith, Redis, and Judge0.
- [ADR-002-auth-and-database.md](docs/architecture/decisions/ADR-002-auth-and-database.md) — local PostgreSQL + local FastAPI auth, portable `DATABASE_URL`.
- [ADR-003-audit-signing-and-tls.md](docs/architecture/decisions/ADR-003-audit-signing-and-tls.md) — Traefik LAN TLS and Ed25519 signed audit checkpoints.

### Target Documentation Layout
Maintain documentation alongside implementation:

```text
docs/
├── research/
│   ├── literature-review.md
│   ├── research-questions.md
│   ├── methodology.md
│   └── results/
├── architecture/
│   ├── system-overview.md
│   ├── deployment-models.md
│   ├── data-model.md
│   └── decisions/
├── security/
│   ├── threat-model.md
│   ├── execution-isolation.md
│   └── audit-integrity.md
├── deployment/
│   ├── standalone.md
│   ├── centralized.md
│   └── backup-restore.md
└── user-guides/
    ├── administrator.md
    ├── organizer.md
    └── candidate.md
```

## 17. Development Workflow

For every phase:

1. **Plan:** define scope, boundaries, and acceptance criteria.
2. **Design:** finalize architecture, data model, interfaces, and flows.
3. **Implement:** break work into small verifiable tasks.
4. **Test:** add unit, integration, security, and failure tests.
5. **Review:** compare implementation against requirements and research goals.
6. **Document:** update architecture, decisions, setup, and status.
7. **Freeze:** complete the phase only after exit criteria are satisfied.

Rules:
- Maintain [docs/specifications/PROJECT_STATUS.md](docs/specifications/PROJECT_STATUS.md).
- Record significant decisions as Architecture Decision Records.
- Keep research algorithms independent from UI code.
- Avoid infrastructure dependencies without a clear need.
- Do not add ML just to appear novel.
- Do not claim capacity without benchmark evidence.
- Do not weaken essential security controls for favorable comparisons.
- Preserve raw experiment results and configurations.
- Document deviations from the approved specification.

## 18. Current Status

**Current phase: Phase 3 — Infrastructure and Deployment**

| Phase | Status |
|---|---|
| 0 — Research and requirements | Complete |
| 1 — Architecture and foundation | Complete |
| 2 — Core assessment platform | Complete |
| 3 — Infrastructure and deployment | In progress |
| 4 — Monitoring and telemetry | Not started |
| 5 — Resource orchestration | Not started |
| 6 — Security orchestration | Not started |
| 7 — Integration and control plane | Not started |
| 8 — Experimental evaluation | Not started |
| 9 — Research and finalization | Not started |

See [docs/specifications/PROJECT_STATUS.md](docs/specifications/PROJECT_STATUS.md) and [docs/specifications/](docs/specifications/) for detailed progress and open decisions.

## 19. Limitations

- No fixed candidate capacity can be guaranteed across arbitrary hardware and networks.
- Capacity depends on server specifications, access points, switches, client behavior, network conditions, workload mix and configuration.
- Standalone has a single-machine failure domain.
- Containers share the host kernel and require careful hardening.
- A finite security test suite does not prove universal security.
- Browser monitoring cannot prevent all forms of cheating.
- Hash chains alone do not protect against privileged rewriting.
- A local deployment is not automatically offline; required dependencies must also be local.
- Missing/stale telemetry must trigger safe fallback behavior.

## 20. Future Work

Potential extensions after validating the primary contributions:
- More advanced workload prediction if representative data exists.
- Additional scheduling and fairness strategies.
- Policy simulation and richer policy authoring.
- External anchoring of signed audit checkpoints.
- Additional assessment plugins.
- Expanded deployment automation and resilience testing.
- Evaluation across more hardware and campus network configurations.

Future work must not distract from validating the two primary research contributions.

## 21. Contributing

LANCAST is currently a solo-developed project. Proposed contributions should respect the architecture, include tests, preserve tenant isolation/security boundaries, document operational impact, avoid unnecessary dependencies, and provide benchmark evidence for performance claims.

## 22. License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for full terms.
