# 02 — LANCAST Research Specification

**Version:** 1.0 — Phase 0 draft

## 1. Research problem
Campus assessment platforms may run multiple concurrent assessments on limited local infrastructure. These assessments have heterogeneous resource demands and different service-quality needs. Static limits or generic scheduling can allow expensive code execution to interfere with latency-sensitive answer saves. At the same time, the platform must protect tenant data, questions, submissions, execution infrastructure and audit records against unauthorized access, replay, abuse and tampering.

LANCAST investigates an assessment-aware framework that coordinates resource decisions and security/integrity policies while preserving responsive, fair and trustworthy operation in centralized and single-machine campus deployments.

## 2. Primary research question
**RQ0:** How can a self-hosted assessment platform dynamically manage infrastructure resources and enforce context-aware security policies to provide reliable, secure and fair examination experiences across multiple concurrent assessments in resource-constrained local-network environments?

## 3. Sub-questions
**Resource**
- RQ1: How can assessment composition and candidate workload characteristics be translated into a pre-event estimate of infrastructure demand and readiness?
- RQ2: Can assessment-aware scheduling and adaptive execution concurrency reduce interference between expensive jobs and latency-sensitive operations compared with FIFO and static baselines?
- RQ3: How does the scheduler affect throughput, tail latency, deadline misses, queue wait and service fairness?
- RQ4: How robust are estimates and decisions when workload estimates are inaccurate or telemetry is delayed/missing?

**Security**
- RQ5: How can policies be selected using assessment type, operation, tenant and observed risk?
- RQ6: Can proportional enforcement contain defined misuse while maintaining a low false-positive rate for legitimate candidates?
- RQ7: What integrity guarantees are provided for assessment versions, submissions and audit records, and what remains out of scope?

## 4. Contributions

### A — Capacity-Aware Adaptive Resource Orchestration
1. Infrastructure profiling: CPU, memory, disk, network, service health and worker availability.
2. Workload characterization: candidate count, assessment mix, autosave frequency, upload size, code-execution demand and duration.
3. Pre-event capacity estimation against empirically measured operating envelopes.
4. Readiness and admission: accept, warn, defer or reject with reasons.
5. Runtime scheduling that distinguishes interactive operations from expensive/background work.
6. Adaptive execution concurrency within safe resource budgets.
7. Fairness measurement across tenants or workload classes.
8. Feedback comparing predicted and observed performance.

Start with a transparent deterministic algorithm. Specify inputs, thresholds, weights, decision interval, safety margins and fallback. ML is optional and must demonstrate measurable benefit before adoption.

### B — Assessment-Aware Security and Integrity Orchestration
1. Context extraction: tenant, role, assessment type, attempt state and operation.
2. Context-specific policy selection.
3. Risk signals: repeated invalid requests, probing, replay, unusual bursts, unauthorized object access and cross-tenant access attempts.
4. Proportional enforcement: reject, throttle, reauthenticate, flag or alert.
5. Assessment version digests, replay-resistant submission state and tamper-evident audit.
6. Isolated, ephemeral, least-privilege execution with resource/network restrictions.
7. Auditable decisions with policy version and reason codes.

Do not infer misconduct solely from weak client-side signals or network instability. Consequential flags need review.

## 5. Hypotheses
- **H1:** Under defined heterogeneous concurrent workloads, the proposed scheduler improves at least one pre-registered service outcome (e.g. P95 answer-save latency or deadline misses) over FIFO and static-concurrency baselines without unacceptable throughput/fairness degradation.
- **H2:** A workload-aware capacity estimator classifies tested operating-envelope violations more accurately than a candidate-count-only estimate.
- **H3:** Context-aware policies detect/block more events in a defined authorized attack suite while maintaining an acceptable false-positive rate on legitimate traffic.
- **H4:** Versioned configuration, idempotent submissions and protected tamper-evident checkpoints detect the defined tampering/replay scenarios.

These are hypotheses, not results.

## 6. Novelty boundary
Do not claim novelty merely for LAN exams, multi-tenancy, containers, monitoring, load balancing, queues, generic autoscaling, Zero Trust, RBAC, hashes, rate limiting or sandboxing. The potential contribution is the assessment-specific model and coordinated decision process linking workload classes, measured capacity, admission/runtime scheduling and context-aware security policies, evaluated comparatively.

A literature review is still required. Investigate online/computer-based examinations, programming assessment systems, multi-tenant QoS, workload-aware scheduling, admission control, edge/on-prem resource management, exam security, context-aware access control and tamper-evident logging. For each source record method, assumptions, testbed, metrics, results, limitations and relevance. Do not infer limitations without reading the paper.

## 7. Variables and metrics
**Independent variables:** scheduler type; workload mix; candidate/request concurrency; deployment topology; security policy; attack scenario/intensity.

**Dependent variables:** P50/P95/P99 latency, throughput, queue wait, error/deadline-miss rates, CPU/RAM/disk/network utilization, worker utilization, fairness, capacity-estimation error, precision, recall, false-positive rate, detection/containment time, replay rejection, integrity detection and security overhead.

**Controlled variables:** hardware, OS, versions, network, database state, workload seed, test duration, warm-up and monitoring configuration.

## 8. Validity threats
- Internal: other bottlenecks may explain changes; monitor relevant resources.
- Construct: infrastructure metrics may not represent candidate experience; measure end-to-end operations.
- External: one testbed may not generalize; state hardware/topology.
- Conclusion: avoid single-run conclusions; repeat and report spread.
- Estimator: report uncertainty and false-safe decisions.
- Security: a finite attack suite cannot prove universal security.

## 9. Expected research artifacts
Algorithm specification/version, workload generator, testbed manifest, raw results, analysis scripts, plots, security scenarios, commit IDs, configuration, failed/inconclusive runs and limitations.
