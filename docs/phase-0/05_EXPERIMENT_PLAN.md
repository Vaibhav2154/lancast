# 05 — LANCAST Experimental Evaluation Plan

**Version:** 1.0 — Phase 0 draft

## 1. Principles
Compare against explicit baselines; use repeatable workloads; retain raw data; report percentile latency and failures; evaluate standalone and central-plus-worker modes separately; do not extrapolate beyond tested hardware/network; report negative and inconclusive outcomes.

## 2. Testbed manifest
Every run records CPU/model/cores, RAM, disk, OS/kernel, container runtime, database/cache/execution versions, LAN topology/link speed, machines/workers, LANCAST commit/configuration, monitoring settings, workload generator version and seed.

Test both:
1. Standalone single-machine.
2. Central server plus separate worker(s), where hardware is available.

## 3. Resource experiments

### Baselines
- **B1 FIFO:** arrival-order dispatch with fixed execution capacity.
- **B2 Static:** fixed worker/concurrency and resource limits, no adaptive decisions.
- **P1 Proposed:** assessment-aware classes, bounded queues, admission policy and runtime adaptive dispatch/concurrency.

Use comparable hardware, limits and workload inputs.

### Workload classes
- Interactive MCQ: frequent small reads/writes/saves.
- Descriptive: larger text payloads and periodic saves.
- File upload: bounded larger payloads.
- Coding: CPU/memory/time-intensive execution.
- Mixed: concurrent combination across tenants.

### Scenarios
R1 increase concurrent MCQ candidates; R2 add coding load while measuring MCQ saves; R3 multiple tenants with different mixes; R4 uploads plus code execution; R5 CPU saturation; R6 memory pressure; R7 delayed/missing telemetry; R8 compare predicted readiness with observed outcome; R9 compare deployment modes; R10 unequal tenant demand/fairness.

Choose candidate/request levels after pilot tests on actual hardware. Do not invent a maximum capacity in advance.

### Metrics
P50/P95/P99 latency by operation; throughput; error rate; deadline misses; queue wait; job completion time; CPU/RAM/disk/network; worker busy/idle; per-tenant latency and waiting distributions; fairness (e.g. Jain index only where values are comparable); estimator error and false-safe/false-unsafe classifications.

### Capacity estimator
Compare estimates with observed demand and readiness outcomes. Report prediction error, false-safe decisions, false-unsafe decisions, uncertainty and out-of-distribution cases. Compare with a simple candidate-count-only estimate.

## 4. Security experiments

### Baselines
- **B-S:** documented baseline authentication/authorization, validation and fixed rate limits.
- **P-S:** proposed context-aware policy selection, risk signals, proportional enforcement and integrity checks.

Do not disable essential controls just to weaken the baseline.

### Authorized scenarios
S1 cross-tenant object access; S2 unauthorized assessment/question access; S3 duplicate/replayed submission; S4 repeated invalid requests/probing; S5 request burst; S6 malformed/oversized upload; S7 post-publication config alteration; S8 audit modification simulation in a test copy; S9 sandbox resource/filesystem/network abuse; S10 legitimate retries, refreshes and network delay to measure false positives.

### Metrics
TP, FP, FN; precision; recall; F1; detection and containment time; replay rejection; integrity detection; added latency/CPU/RAM; legitimate request failures/delays.

## 5. Combined experiments
With both engines enabled, measure security overhead on answer-save latency, effects of resource pressure on security decisions, safe behavior under telemetry loss, queue consumption by abusive traffic and auditability of enforcement.

## 6. Procedure
1. Record testbed manifest and commit.
2. Restore known initial state.
3. Verify monitoring.
4. Warm up using documented method.
5. Run fixed workload/duration.
6. Repeat with recorded seeds.
7. Export raw metrics/logs/results.
8. Check anomalies.
9. Analyze using versioned scripts.
10. Record conclusions and limitations.

Set repetition count and duration during pilot and document before final comparisons.

## 7. Statistical reporting
Report median and spread across runs; use paired comparisons when runs can be matched; choose tests after inspecting sample size/distribution; report effect size and uncertainty; do not equate statistical significance with practical importance; explain excluded/failed runs.

## 8. Ablations
Where feasible remove workload characterization, admission control, adaptive concurrency, fairness, context-aware policy selection, risk signals or signed checkpoints one at a time.

## 9. Reproducibility artifacts
Store workload definitions/generators, testbed manifests, baseline/proposed configs, raw CSV/JSON, analysis scripts, plots, commit IDs, security scenarios and failed-run notes under `experiments/`.

## 10. Exit criteria
Both deployment modes tested to available-hardware extent; resource baselines compared; capacity estimator validated; security scenarios executed; false positives and overhead reported; raw results reproducible; limitations documented.
