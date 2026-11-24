# 03 — LANCAST System Architecture

**Version:** 1.0 — Phase 0 logical architecture

## 1. Goals
Support central and standalone deployments with shared code; separate application logic from untrusted execution; make resource/security decisions observable and testable; avoid unnecessary microservices; preserve clear module boundaries.

## 2. Deployment topologies

### 2.1 Centralized campus deployment
A central server (or gateway + app pool) hosts the Traefik reverse proxy, React SPA (nginx), FastAPI application pool, PostgreSQL, Redis, monitoring/control plane and orchestration services. Separate Judge0 execution worker machines may be attached. Candidates and organizers connect over campus LAN/Wi-Fi with no Internet access required on candidate machines.

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

Adding workers does not automatically increase database, API or network capacity.

### 2.2 Standalone single-machine deployment
All required services for enabled features run on one physical or virtual machine/server with zero Internet dependency during operation. Local services include Traefik, React SPA (nginx), a single FastAPI instance, local PostgreSQL (with local FastAPI auth), Redis, monitoring and a local Judge0 execution container. No separate physical/virtual worker machine is required.

```text
Browsers (Local LAN) -> Traefik (:80/:443) -> React SPA (nginx) / FastAPI API
                                                   |-> Local PostgreSQL (local auth)
                                                   |-> Local Redis / Bounded Queue
                                                   |-> Resource & Security Orchestrators
                                                   |-> Local Judge0 + isolate worker
                                                   |-> Local Prometheus / Exporters
```

If the single machine cannot support the requested workload, readiness/admission must warn or reject rather than assume extra capacity.

### 2.3 Shared-code principle
Both profiles use the same application, assessment modules, resource algorithms, security engine and data model. Configuration changes service placement, addresses, replica/worker counts, resource budgets, telemetry targets and `DATABASE_URL` (local PostgreSQL by default, or an optional external PostgreSQL URL such as Supabase Postgres while keeping authentication strictly local in FastAPI).

## 3. Logical components
- **Web UI:** organizer, candidate and platform administration portals.
- **Application API:** identity integration, tenant authorization, assessment lifecycle, attempt state, response persistence, submission and results.
- **Assessment modules:** validation, response contract and evaluation for MCQ, multiple-select, descriptive, upload and coding.
- **Assessment Capsule:** versioned export/import of metadata, questions, assets and evaluation configuration; excludes candidates, secrets and attempts.
- **Resource orchestrator:** telemetry ingestion, profiling, workload characterization, capacity estimator, readiness/admission, scheduler, bounded queues, worker/concurrency manager and fairness feedback.
- **Security orchestrator:** context resolver, policy registry, risk signals, decision engine, enforcement adapter, replay/idempotency controls, integrity verifier and audit/checkpoint writer.
- **Execution subsystem:** isolated job dispatch, execution, result collection and cleanup.
- **Infrastructure/control plane:** deployment profiles, gateway, machine/worker registration, health checks and controlled operations.
- **Data/observability:** PostgreSQL authoritative state; Redis or equivalent for transient coordination; metrics/logs separated from answer content.

## 4. Key flows

### Event readiness
Organizer configures event -> API creates workload descriptor -> estimator combines workload and telemetry -> readiness/admission returns accept/warn/defer/reject with reasons -> organizer reviews result.

### Answer save
Candidate sends attempt/version/idempotency context -> API authenticates and checks tenant/attempt/deadline -> security policy evaluates context -> API validates and persists -> acknowledgement after defined durable commit -> metrics/audit event emitted without answer body in ordinary logs.

### Coding submission
API validates candidate/tenant/attempt -> security policy checks permissions/limits -> bounded queue -> scheduler selects eligible worker -> isolated execution -> result stored against attempt/version -> telemetry and audit updated.

### Runtime adaptation
Agents/exporters report metrics -> telemetry normalized -> scheduler evaluates workload and queue state -> bounded dispatch/concurrency decision -> outcome recorded for evaluation.

### Security event
Operation emits risk signal -> context resolver associates actor/tenant/assessment/operation -> policy engine decides -> enforcement adapter allows/rejects/throttles/flags -> reason and policy version audited.

## 5. Logical interface contracts
| Contract | Producer -> Consumer | Key fields |
|---|---|---|
| WorkloadDescriptor | API -> estimator | assessment mix, candidates, duration, jobs/uploads |
| TelemetrySample | agent -> collector | machine, timestamp, CPU/RAM/disk/network/health |
| CapacityEstimate | estimator -> admission/UI | demand, available envelope, bottleneck, uncertainty |
| AdmissionDecision | controller -> assessment lifecycle | decision, reasons, policy version |
| ExecutionJob | API -> queue | tenant, attempt, language, limits, priority class |
| SchedulingDecision | scheduler -> worker manager | worker, concurrency budget, rationale |
| SecurityContext | API -> policy engine | actor, tenant, operation, assessment type/state |
| SecurityDecision | engine -> enforcement | action, reasons, policy version |
| AuditEvent | modules -> audit writer | event ID, sequence, actor scope, action, digest metadata |

Exact schemas, authentication and versioning are Phase 1 outputs.

## 6. Constraints
- Browsers must not access databases, Redis, worker management or internal ports directly.
- Every tenant-scoped operation enforces server-side authorization.
- Candidate code cannot access application secrets.
- Decisions are bounded by configured safety limits.
- Missing telemetry must not cause unlimited dispatch or unsafe scale-up.
- Standalone must not silently depend on remote workers.
- External Internet dependencies must be listed and tested.

## 7. Target repository layout
```text
lancast/
  apps/{web,api}/
  modules/{identity,tenancy,assessments,submissions}/
  orchestration/
    resource/{telemetry,profiling,workload,capacity,admission,scheduling,fairness}/
    security/{context,policies,risk,enforcement,integrity,audit}/
  execution/{dispatcher,workers}/
  infrastructure/{compose,gateway,monitoring,agents,profiles/{standalone,central}}/
  control_plane/
  shared/{schemas,events,configuration}/
  experiments/{workloads,baselines,resource,security}/
  tests/
  docs/
```
This is a target layout, not a requirement to create all directories immediately. Begin with a modular monolith and separately managed execution workers.
