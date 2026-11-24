# 01 — LANCAST Software Requirements Specification

**Version:** 1.0 — Phase 0 draft

## 1. Purpose and scope
LANCAST is a self-hosted, multi-tenant campus assessment platform for departments, faculty groups and clubs. It supports heterogeneous assessment workloads and includes two research subsystems: adaptive resource orchestration and assessment-aware security/integrity orchestration.

In scope: tenant and user management; organizer/candidate portals; assessment authoring and lifecycle; MCQ, multiple-select, descriptive, file-upload and programming assessments; attempts, autosave, submission, evaluation and results; Assessment Capsule export/import; central and standalone deployment; monitoring; capacity estimation; admission control; adaptive scheduling; context-aware security; replay-resistant submissions; tamper-evident audit; reproducible evaluation.

Out of scope initially: general-purpose cloud platform; unlimited capacity guarantees; biometric/AI proctoring; automatic provisioning of physical machines; multi-region disaster recovery; mandatory Kubernetes; claims that browser monitoring prevents all cheating.

## 2. Users
- Platform administrator: installation, tenants, infrastructure, policies and health.
- Tenant administrator: users and settings within one organization.
- Organizer: assessment authoring, candidates, event monitoring and results.
- Candidate: authorized assessment participation.
- Infrastructure operator: machines, workers, telemetry and deployment.
- Research evaluator: controlled experiments and evidence review.

## 3. Deployment requirements
- **DEP-01:** MUST support centralized campus deployment through LAN/Wi-Fi, with optional separate execution workers.
- **DEP-02:** MUST support standalone deployment on one physical/virtual server. All services required by enabled features run on that machine; no separate worker machine is required.
- **DEP-03:** Both profiles MUST use the same application and orchestration code.
- **DEP-04:** Standalone MUST provide local database, queue/cache, monitoring and execution services when those features are enabled.
- **DEP-05:** Organizers and candidates MUST access the system through a configured local hostname/IP.
- **DEP-06:** External Internet dependencies MUST be documented; the system MUST NOT claim fully offline operation if required dependencies remain remote.
- **DEP-07:** Secrets MUST be external to source code and excluded from version control.

## 4. Functional requirements

### Identity and tenancy
- **FR-ID-01:** Authenticate administrators, organizers and candidates.
- **FR-ID-02:** Enforce role-based authorization server-side.
- **FR-TEN-01:** Support multiple independent tenants.
- **FR-TEN-02:** Scope tenant-owned users, assessments, attempts, files and results to their tenant.
- **FR-TEN-03:** Derive tenant scope from authenticated membership; never trust client-supplied tenant IDs as authorization.
- **FR-TEN-04:** Deny and record cross-tenant access attempts.
- **FR-ID-03:** Define session expiry, revocation and renewal.
- **FR-ID-04:** Audit privileged actions.

### Assessment lifecycle and modules
- **FR-AS-01:** Organizers can create, edit, preview, publish, start, close and archive assessments.
- **FR-AS-02:** Configure instructions, duration, availability, attempts, questions and scoring.
- **FR-AS-03:** Freeze/version published configuration for active attempts.
- **FR-AS-04:** Assign candidates or configure authorized joining.
- **FR-AS-05:** Support concurrent assessments across tenants.
- **FR-AS-06:** Provide pre-event readiness report.
- **FR-MOD-01:** Support single-answer MCQ and multiple-select.
- **FR-MOD-02:** Support descriptive responses and controlled file uploads.
- **FR-MOD-03:** Support programming questions, language selection, test cases and server-authoritative evaluation.
- **FR-MOD-04:** Use a documented module contract for adding question types.
- **FR-MOD-05:** Keep hidden answers and test cases server-side.

### Attempts and execution
- **FR-ATT-01:** Candidates join only authorized assessments.
- **FR-ATT-02:** Each attempt has a stable ID and assessment-version reference.
- **FR-ATT-03:** Autosave responses and communicate save status.
- **FR-ATT-04:** Make submission idempotent; retries must not create duplicate scored submissions.
- **FR-ATT-05:** Use server time for deadlines.
- **FR-ATT-06:** Preserve acknowledged responses across client/network interruptions.
- **FR-CODE-01:** Execute untrusted code outside the main API process.
- **FR-CODE-02:** Enforce time, memory, process and output limits.
- **FR-CODE-03:** Do not expose host privileges or application secrets to jobs.
- **FR-CODE-04:** Disable execution network access by default.
- **FR-CODE-05:** Keep hidden tests server-side and expose execution health/queue metrics.

### Assessment Capsule
- **FR-CAP-01:** Support export/import of versioned assessment packages.
- **FR-CAP-02:** Include metadata, question definitions, assets and evaluation configuration.
- **FR-CAP-03:** Exclude candidate records, secrets and live attempts.
- **FR-CAP-04:** Validate schema, version, archive paths, sizes and integrity on import.
- **FR-CAP-05:** Import creates a new assessment instance; it must not silently overwrite an existing one.

### Resource orchestration
- **FR-RES-01:** Collect CPU, memory, disk, network, service and worker telemetry.
- **FR-RES-02:** Characterize candidate count, assessment mix, autosave, uploads and code execution demand.
- **FR-RES-03:** Estimate pre-event capacity against empirically validated operating envelopes.
- **FR-RES-04:** Report assumptions, uncertainty and bottlenecks.
- **FR-RES-05:** Support accept, warn, defer or reject admission decisions.
- **FR-RES-06:** Distinguish latency-sensitive operations from expensive/background work.
- **FR-RES-07:** Use bounded queues and configurable resource budgets.
- **FR-RES-08:** Adapt worker concurrency/dispatch using measured state.
- **FR-RES-09:** Log decisions, inputs and policy version.
- **FR-RES-10:** Fail safely when telemetry/orchestrator is unavailable.
- **FR-RES-11:** Measure fairness across tenants or workload classes.
- **FR-RES-12:** Never claim capacity beyond tested configurations.

### Security and integrity orchestration
- **FR-SEC-01:** Treat LAN as transport, not proof of identity or authorization.
- **FR-SEC-02:** Select/evaluate policies using tenant, assessment and operation context.
- **FR-SEC-03:** Enforce tenant-scoped authorization on every protected operation.
- **FR-SEC-04:** Validate upload type, size and content server-side.
- **FR-SEC-05:** Reject duplicate/replayed submissions using idempotency and attempt state.
- **FR-SEC-06:** Evaluate suspicious signals: invalid requests, probing, bursts, unauthorized access and cross-tenant attempts.
- **FR-SEC-07:** Apply proportional responses: reject, throttle, reauthenticate, flag or alert.
- **FR-SEC-08:** Log reason codes and policy versions.
- **FR-SEC-09:** Verify canonical assessment configuration digests.
- **FR-SEC-10:** Use tamper-evident audit events with protected signed checkpoints or equivalent.
- **FR-SEC-11:** Protect signing keys from ordinary application users.
- **FR-SEC-12:** Do not rely solely on client-side monitoring to establish misconduct.
- **FR-SEC-13:** Provide human review for consequential flags.

### Administration and observability
- **FR-ADM-01:** Show deployment mode and service health.
- **FR-ADM-02:** Show managed machine/worker health to authorized operators.
- **FR-OBS-01:** Expose structured logs and metrics.
- **FR-OBS-02:** Separate metrics by workload class and execution queue.
- **FR-OBS-03:** Do not log passwords, tokens or candidate answer bodies in ordinary logs.

## 5. Non-functional requirements
- **NFR-PERF-01:** Keep interactive operations responsive under the validated workload; numerical targets come from pilot measurements.
- **NFR-PERF-02:** Report P50/P95/P99, not only averages.
- **NFR-CAP-01:** Capacity claims identify hardware, software, topology, workload and duration.
- **NFR-REL-01:** Background worker failure should not take down basic answer saving.
- **NFR-REL-02:** Acknowledged responses are durable according to documented commit behavior.
- **NFR-REL-03:** Provide health checks and recovery instructions.
- **NFR-SEC-01:** Protect secrets and use least privilege.
- **NFR-SEC-02:** Expose only required ports.
- **NFR-SEC-03:** Restrict management interfaces.
- **NFR-SEC-04:** Isolate and resource-limit code execution.
- **NFR-PRIV-01:** Collect only necessary telemetry.
- **NFR-PRIV-02:** Pseudonymize candidate data in research artifacts where feasible.
- **NFR-MAINT-01:** Document module interfaces and automate tests.
- **NFR-PORT-01:** Make both deployment profiles reproducible.
- **NFR-TEST-01:** Test research algorithms independently of the UI.
- **NFR-TEST-02:** Record software/configuration versions for experiments.

## 6. Initial data entities
Tenant, User, Membership, Role, Assessment, AssessmentVersion, Question, QuestionAsset, AssessmentCapsule, Attempt, Response, Submission, ExecutionJob, Machine, Worker, TelemetrySample, WorkloadProfile, CapacityEstimate, AdmissionDecision, SchedulingDecision, SecurityPolicy, RiskSignal, SecurityDecision, AuditEvent and SignedAuditCheckpoint.

Detailed schema and API contracts are Phase 1 deliverables.

## 7. Completion rule
A requirement is complete only when implementation, automated tests, authorization/failure tests where relevant, operational evidence and documentation exist. A UI control or README claim alone is insufficient.
