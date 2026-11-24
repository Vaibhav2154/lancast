# 07 — LANCAST Focused Literature Review and Gap Analysis

**Version:** 1.0 — Phase 0 draft  
**Date:** 24 November 2026  
**Scope:** Synthesizes nine verified sources across three pillars required by [02_RESEARCH_SPECIFICATION.md](02_RESEARCH_SPECIFICATION.md): (1) Campus e-exam resilience, LAN CBT security, and automated programming assessment; (2) Workload-aware scheduling, admission control, and tail-latency QoS; and (3) Zero Trust, context/risk-aware access control, and tamper-evident audit logging.

> **Research integrity note:** Sources marked **Provisional / full-text verification pending** rely on published abstracts or summaries and must be verified against the full PDF before final manuscript submission. Do not infer unverified author-acknowledged limitations without reading the full text.

---

## 1. Pillar 1 — Campus Assessment, LAN Security, and Coding Judges

### S1. Hillier, Grant, & Coleman (2018) — Resilient Networked e-Exams
- **Citation:** Hillier, M., Grant, S., & Coleman, M. (2018). *Towards authentic e-Exams at scale: Robust networked Moodle.* ASCILITE 2018, pp. 131–141. https://doi.org/10.14742/apubs.2018.1919
- **Method & assumptions:** Combines Moodle, Linux, Safe Exam Browser (SEB), and USB-provisioned Live Linux clients with a cached-online mode that downloads exam assets upfront, autosaves roughly every minute, stores encrypted responses locally on disconnect, and resynchronizes on reconnect.
- **Evidence & metrics:** Trialled in two undergraduate units at an Australian university; evaluated primarily via student completion, response preservation across network/software glitches, and perceived reliability.
- **Limitations:** Small single-university cohort (authors caution against broad generalization); relies on heavy client provisioning (USB/Live Linux) rather than a lightweight browser-only workflow; security assessed mainly via user perception rather than a LAN threat model; no multi-tenant club/department isolation or coding-judge resource governance.
- **Relevance to LANCAST:** Grounds LANCAST's local-first delivery, durable autosave, and disconnect recovery (`FR-ATT-03`, `FR-ATT-06`), while showing the gap for browser-only multi-tenant campus workflows.

### S2. Navin, De Zoysa, Karunaratna, & Harshanath (2025) — Disrupted-Environment CBT Protocol
- **Citation:** Navin, D., De Zoysa, K., Karunaratna, D. D., & Harshanath, B. (2025). *A Secure Protocol for Computer-Based Assessments in Disrupted Environments.* ICARC 2025. https://doi.org/10.1109/ICARC64760.2025.10963243
- **Verification status:** *Provisional (abstract-only; obtain full PDF before citing detailed methodology or claiming author-acknowledged limitations).*
- **Method & assumptions:** Uses Delay Tolerant Networking (DTN) concepts with physical, administrative, and technical controls; evolved from centralized Moodle to standalone local servers for offline resilience.
- **Evidence & metrics:** Repository abstract reports deployment across >180,000 candidates in Sri Lanka under power and Internet disruptions.
- **Gaps relative to LANCAST (provisional):** Abstract targets large-scale national disrupted-environment exams rather than multi-tenant campus events with mixed workloads (MCQ + uploads + coding); does not expose per-candidate resource profiling, workload-aware scheduling, or shared campus Wi-Fi threat evaluations.
- **Relevance to LANCAST:** Supports the operational viability of standalone local assessment servers (`DEP-02`, `DEP-04`) while highlighting the need for explicit capacity and latency measurements.

### S3. Maksakha & Vanijja (2026) — Vulnerability Analysis for CBT Exam Systems
- **Citation:** Maksakha, C., & Vanijja, V. (2026). *Vulnerability Analysis for CBT Exam System.* Proceedings of IAIT '26, Article 32, pp. 1–9. https://doi.org/10.1145/3816713.3818804
- **Verification status:** *Verify full experimental tables in PDF before final manuscript submission.*
- **Method & assumptions:** Evaluates Moodle + SEB and Testimate CBT using OWASP Top 10 (2021) for application-layer testing and NIST SP 800-115-oriented infrastructure testing. Threat model assumes an examinee with legitimate access to the test-site Wi-Fi/LAN.
- **Evidence & metrics:** Exploratory pilot (`n = 1` configured instance per system in a shared testbed) with qualitative single-rater severity ratings. Finds that application-layer controls alone miss high-severity campus Wi-Fi/LAN risks (e.g., missing client isolation and management-frame protection).
- **Limitations:** Exploratory pilot scope; single-rater qualitative scoring; excludes remote attackers, privileged administrators, supply-chain, and physical attacks; does not propose or evaluate a deployable adaptive security policy engine.
- **Relevance to LANCAST:** Directly motivates LANCAST's core security principle (`FR-SEC-01`, [04_THREAT_MODEL.md](04_THREAT_MODEL.md)): treat the campus LAN as an untrusted transport and pair network/transport controls with server-side tenant authorization and auditability (`RQ5`, `RQ6`).

### S4. Mekterović, Brkić, & Horvat (2023) — Scaling Automated Programming Assessment (Edgar)
- **Citation:** Mekterović, I., Brkić, L., & Horvat, M. (2023). *Scaling Automated Programming Assessment Systems.* Electronics, 12(4), 942. https://doi.org/10.3390/electronics12040942
- **Method & assumptions:** Reports six years of operating Edgar, an automated programming assessment system using modular services, queues, worker pools, and separation of untrusted code execution from the main application.
- **Evidence & metrics:** Operational case study (~700 students over a 3-hour window) showing that two execution servers failed to sustain timely feedback under bursty arrivals, especially for Java workloads.
- **Limitations:** Focused on programming assessment at scalable web/server scale rather than a multi-tenant mixed-workload campus appliance (MCQ + descriptive + uploads + coding) on modest on-premises hardware; does not formulate pre-event capacity estimation, admission control, or cross-workload tail-latency isolation for interactive saves.
- **Relevance to LANCAST:** Directly motivates separating Judge0 execution workers from FastAPI behind a bounded queue (`FR-CODE-01`, `FR-RES-07`) and motivates evaluating bursty coding workloads alongside interactive MCQ saves (`RQ2`, `RQ3`, `H1`).

---

## 2. Pillar 2 — Workload-Aware Scheduling, Admission Control, and Tail-Latency QoS (Contribution A)

### S5. Delimitrou & Kozyrakis (2014) — Quasar: Resource-Efficient and QoS-Aware Cluster Management
- **Citation:** Delimitrou, C., & Kozyrakis, C. (2014). *Quasar: Resource-Efficient and QoS-Aware Cluster Management.* ASPLOS '14, pp. 127–144. https://doi.org/10.1145/2541940.2541941
- **Verification status:** *Full-text details to be verified against the ASPLOS '14 PDF during Phase 5/8 write-up.*
- **Method & assumptions:** Classifies incoming heterogeneous workloads (latency-critical interactive services and batch jobs) using lightweight profiling and collaborative filtering to estimate resource sensitivity and co-location interference, then performs QoS-aware placement and resource allocation.
- **Evidence & metrics:** Evaluated on multi-node datacenter clusters using tail latency, throughput, and cluster utilization across mixed interactive and batch workloads.
- **Limitations (relative to LANCAST):** Designed for large, multi-node datacenter clusters with hardware-level heterogeneity and continuous ML/collaborative-filtering classification; assumes datacenter-scale elasticity rather than a fixed, resource-constrained single-machine or small campus LAN deployment with assessment-specific semantics (deadlines, autosaves, pre-event organizer admission).
- **Relevance to LANCAST:** Provides the foundational principle of separating latency-critical interactive work from heavy batch compute via workload characterization (`RQ1`, `RQ2`, `H1`, `H2`), which LANCAST adapts into a transparent, deterministic pre-event estimator and runtime scheduler for campus assessments.

### S6. Chen, Delimitrou, & Martínez (2019) — PARTIES: QoS-Aware Resource Partitioning for Multiple Interactive Services
- **Citation:** Chen, S., Delimitrou, C., & Martínez, J. F. (2019). *PARTIES: QoS-Aware Resource Partitioning for Multiple Interactive Services.* ASPLOS '19, pp. 107–120. https://doi.org/10.1145/3297858.3304005
- **Verification status:** *Full-text details to be verified against the ASPLOS '19 PDF during Phase 5/8 write-up.*
- **Method & assumptions:** Uses closed-loop runtime feedback monitoring tail latency (e.g., P99) to dynamically partition shared hardware/software resources (CPU cores, cache, memory bandwidth, disk/network I/O) among co-located latency-critical services without requiring offline profiling of every combination.
- **Evidence & metrics:** Evaluated on shared servers co-locating multiple interactive microservices; measures P99 tail latency, SLO violations, and throughput under varying load.
- **Limitations (relative to LANCAST):** Focuses on low-level hardware partitioning (e.g., Intel CAT/MBA) for datacenter microservices rather than application-level queue/concurrency governance across heterogeneous campus exam operations (MCQ saves vs. file uploads vs. sandboxed Judge0 compilations) or pre-event admission control.
- **Relevance to LANCAST:** Validates closed-loop, telemetry-driven runtime adaptation to protect interactive tail latency (`FR-RES-06`, `FR-RES-08`, `RQ2`, `RQ3`) and informs LANCAST's safe-bounds feedback controller under container/worker constraints.

---

## 3. Pillar 3 — Zero Trust, Context/Risk-Aware Access Control, and Tamper-Evident Audit (Contribution B)

### S7. Rose, Borchert, Mitchell, & Connelly (2020) — NIST SP 800-207: Zero Trust Architecture
- **Citation:** Rose, S., Borchert, O., Mitchell, S., & Connelly, S. (2020). *Zero Trust Architecture.* NIST Special Publication 800-207. https://doi.org/10.6028/NIST.SP.800-207
- **Method & assumptions:** Formalizes Zero Trust Architecture (ZTA) around the principle that network location (such as an internal corporate or campus LAN) grants no implicit trust. Separates the **Policy Engine (PE)**, **Policy Administrator (PA)**, and **Policy Enforcement Point (PEP)** so every request is authenticated, authorized, and evaluated per-session/per-request using dynamic context.
- **Evidence & metrics:** Standards/architectural specification (not an empirical benchmark paper).
- **Limitations (relative to LANCAST):** Enterprise-general reference architecture; does not define assessment-specific contexts (attempt state, frozen exam version, question type, organizer vs. candidate fairness) or proportional responses that avoid falsely punishing legitimate exam candidates during network glitches.
- **Relevance to LANCAST:** Directly anchors LANCAST's `FR-SEC-01` ("treat LAN as transport, not proof of identity") and the logical separation between the Security Orchestrator (context resolver + policy engine) and authoritative API/execution enforcement boundaries (`TD-07`, `RQ5`).

### S8. Xiao, Ye, Kanwal, Newe, & Lee (2022) — SoK: Context and Risk Aware Access Control for Zero Trust Systems
- **Citation:** Xiao, S., Ye, Y., Kanwal, N., Newe, T., & Lee, B. (2022). *SoK: Context and Risk Aware Access Control for Zero Trust Systems.* Security and Communication Networks, Vol. 2022, Article ID 7026779. https://doi.org/10.1155/2022/7026779
- **Verification status:** *Full-text details to be verified against the published PDF during Phase 6/8 write-up.*
- **Method & assumptions:** Systematization of Knowledge (SoK) reviewing how context-aware access control (CAAC) and risk-based access control (RAdAC) combine subject, resource, action, and environmental signals to drive dynamic, continuous authorization in Zero Trust environments.
- **Evidence & metrics:** Comparative survey and taxonomy of context attributes, risk-scoring models, and enforcement trade-offs across cloud/edge/enterprise ZTA systems.
- **Limitations (relative to LANCAST):** Surveys general enterprise/IoT/cloud access control rather than multi-tenant assessment lifecycles; does not address exam-specific false-positive harms (where aggressive automated blocking disrupts legitimate candidates experiencing Wi-Fi jitter or legitimate retries).
- **Relevance to LANCAST:** Grounds LANCAST's context extraction and risk-signal evaluation (`FR-SEC-02`, `FR-SEC-06`, `FR-SEC-07`, `RQ5`, `RQ6`, `H3`) and reinforces why LANCAST requires proportional enforcement, reason codes, and human review (`FR-SEC-13`).

### S9. Crosby & Wallach (2009) — Efficient Data Structures for Tamper-Evident Logging
- **Citation:** Crosby, S. A., & Wallach, D. S. (2009). *Efficient Data Structures for Tamper-Evident Logging.* Proceedings of the 18th USENIX Security Symposium (USENIX Security '09), pp. 317–334.
- **Method & assumptions:** Analyzes the limitations of linear hash chains (`O(n)` verification/inclusion proofs and vulnerability to full-chain rewriting by a compromised host) and introduces Merkle **history trees** with periodic **signed checkpoints** enabling `O(log n)` inclusion and consistency proofs against an untrusted log server.
- **Evidence & metrics:** Implemented and benchmarked on large-scale log traces (demonstrating proof size reductions from ~800 MB with naive chains to ~3 KB for 80M events, with low runtime overhead).
- **Limitations (relative to LANCAST):** Focuses on cryptographic log data structures rather than application-level exam integrity workflows (canonical assessment-version digests, idempotent submission state machines, and operational key-separation on standalone/central campus servers).
- **Relevance to LANCAST:** Directly informs LANCAST's tamper-evident audit design (`FR-SEC-10`, `FR-SEC-11`, `T14`, `T15`, `RQ7`, `H4`), explicitly grounding the documented threat-model caveat that a hash chain alone cannot stop a privileged host attacker without protected signed checkpoints.

---

## 4. Cross-Paper Synthesis Matrix

| Source | Pillar | Primary Contribution | Gap Relative to LANCAST | LANCAST Mapping |
|---|---|---|---|---|
| **S1** Hillier et al. (2018) | Exam resilience | Cached-online Moodle/SEB autosave & recovery | Heavy USB/Live Linux setup; no multi-tenant coding/resource orchestration | `FR-ATT-03/06` |
| **S2** Navin et al. (2025)* | Standalone CBT | Disrupted-environment DTN/local CBT protocol | Abstract-only; no mixed-workload scheduling or LAN threat benchmarks | `DEP-02/04` |
| **S3** Maksakha & Vanijja (2026)* | LAN CBT security | Joint OWASP + NIST Wi-Fi/LAN CBT audit | Exploratory pilot; no adaptive policy engine or deployable platform | `FR-SEC-01`, `RQ5` |
| **S4** Mekterović et al. (2023) | Coding judge | Modular queue/worker architecture for Edgar | No pre-event capacity estimator or cross-workload MCQ tail-latency isolation | `FR-CODE-01`, `RQ2` |
| **S5** Delimitrou & Kozyrakis (2014)* | Resource QoS | Heterogeneity-aware cluster profiling & QoS (Quasar) | Datacenter-scale ML; no exam-specific admission or single-host campus mode | `RQ1`, `RQ2`, `H2` |
| **S6** Chen et al. (2019)* | Tail-latency QoS | Closed-loop resource partitioning (PARTIES) | Hardware-level microservice focus; no exam queue/concurrency governance | `FR-RES-08`, `RQ3`, `H1` |
| **S7** Rose et al. (2020) | Zero Trust | NIST SP 800-207 PE/PA/PEP architecture | Enterprise-general; lacks assessment-context & candidate-fairness semantics | `FR-SEC-01/02`, `TD-07` |
| **S8** Xiao et al. (2022)* | Context/Risk AC | SoK on context & risk-aware ZTA access control | General enterprise/edge; lacks exam-specific false-positive & retry controls | `FR-SEC-06/07`, `RQ6`, `H3` |
| **S9** Crosby & Wallach (2009) | Audit integrity | History trees & signed checkpoints (`O(log n)` proofs) | Cryptographic log primitive only; not integrated with exam version/replay state | `FR-SEC-10/11`, `RQ7`, `H4` |

*\*Full-text verification pending before final manuscript citation.*

---

## 5. Consolidated Research Gap Aligned to LANCAST

Existing work solves pieces of the campus assessment problem in isolation:
1. **Assessment platforms & coding judges (S1–S4)** demonstrate that local-first delivery is viable and that both shared campus Wi-Fi and bursty coding workloads create severe reliability/security risks — **but** they do not integrate pre-event capacity estimation, admission control, or runtime adaptive scheduling to protect interactive exam operations from co-located heavy workloads on constrained on-premises hardware.
2. **Cluster QoS & tail-latency systems (S5–S6)** show how workload profiling and closed-loop feedback protect interactive tail latency — **but** they target datacenter microservices and hardware partitioning rather than deterministic, explainable, assessment-aware admission and queue/concurrency governance across standalone and small-cluster campus servers.
3. **Zero Trust, context-aware access control, and tamper-evident logging (S7–S9)** establish principled security architectures and cryptographic audit structures — **but** they have not been unified into an assessment-aware security orchestrator that couples tenant/attempt/assessment context with proportional enforcement (minimizing false positives on legitimate candidate retries), replay-resistant submissions, and signed audit checkpoints.

**LANCAST's research position:** LANCAST does not claim novelty for containers, LAN hosting, RBAC, queues, or hash chains individually. Its intended contribution is the **assessment-aware orchestration layer** uniting (A) capacity-aware pre-event estimation, admission control, and adaptive runtime scheduling (`RQ1–RQ4`, `H1–H2`) with (B) context- and risk-aware security and integrity orchestration (`RQ5–RQ7`, `H3–H4`), evaluated comparatively against explicit baselines (`B1 FIFO`, `B2 Static`, `B-S`) on documented campus-scale hardware.

---

## 6. Pending Verification Actions (Before Final Manuscript)
1. Obtain and read the full PDF of **S2 (Navin et al., 2025)** to verify protocol mechanics and author-stated limitations.
2. Verify experimental tables and exact findings in the full PDF of **S3 (Maksakha & Vanijja, 2026)**.
3. Verify exact evaluation metrics/testbed details in the full PDFs of **S5 (Quasar)**, **S6 (PARTIES)**, and **S8 (Xiao et al., 2022)** before citing numerical results in the Phase 9 manuscript.
