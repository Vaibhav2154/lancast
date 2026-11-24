# 04 — LANCAST Threat Model

**Version:** 1.0 — Phase 0 draft

## 1. Assumptions
The campus LAN is not inherently trusted. Candidate devices may be unmanaged or compromised. Organizers can make mistakes. Candidate code/files are untrusted. Multiple tenants share infrastructure. Host/admin compromise is high impact. Standalone concentrates services and has a single-host failure domain.

## 2. Assets
A1 tenant records; A2 credentials/sessions/tokens; A3 questions/hidden tests; A4 responses/submissions; A5 scores/results; A6 assessment configuration; A7 workers/host resources; A8 database/files; A9 policies/signing keys; A10 audit records; A11 telemetry/capacity decisions; A12 deployment secrets.

## 3. Actors
Candidate; malicious candidate; compromised candidate device; organizer; compromised organizer; external LAN participant; malicious uploaded file/code; compromised worker; privileged administrator/host attacker.

## 4. Trust boundaries
1. Browser/reverse proxy.
2. Proxy/application API.
3. API/database/cache/storage.
4. API/orchestration modules.
5. Dispatcher/execution worker.
6. Worker/host/network.
7. Agent/monitoring-control plane.
8. Tenant/tenant.
9. Standalone host/host administrator.
10. Central server/separate worker machines.

## 5. Threat register
| ID | Threat | Impact | Mitigation |
|---|---|---|---|
| T01 | Cross-tenant object access (BOLA/IDOR) | Data disclosure/modification | Derive tenant scope from authenticated membership; authorize every object; negative tests |
| T02 | Session/credential theft | Account takeover | Secure session handling, TLS, expiry/revocation, CSRF controls and secret protection |
| T03 | Unauthorized admin action | Assessment/result tampering | Server-side RBAC, least privilege, reauthentication for sensitive actions, audit |
| T04 | Hidden question/test disclosure | Assessment compromise | Keep answers/hidden tests server-side; restrict responses/storage |
| T05 | Published configuration tampering | Invalid assessment | Versioned immutable attempt config, canonical digest and audit |
| T06 | Replay/duplicate submission | Duplicate or altered score | Idempotency, unique constraints and attempt state machine |
| T07 | Malicious code execution | Host/data compromise | Ephemeral isolated sandbox, non-root, limits, no secrets, restricted FS/network |
| T08 | Worker escape/lateral movement | Host/tenant compromise | No privileged mode/socket mounts, minimal capabilities, isolated network, patching |
| T09 | Resource exhaustion/DoS | Assessment outage | Rate limits, bounded queues, admission, quotas, body limits and overload behavior |
| T10 | Malicious upload/path traversal | Data/code compromise | Size/type/content checks, generated names, safe storage and archive validation |
| T11 | LAN service exposure | Unauthorized access | Firewall allowlists, expose gateway only, protect management endpoints |
| T12 | Telemetry spoofing/poisoning | Bad capacity decisions | Agent authentication, validation, stale-data detection and safe fallback |
| T13 | Scheduler starvation/manipulation | Unfair service | Server-side classification, bounded priorities, fairness and audit |
| T14 | Audit alteration/deletion | Loss of evidence | Append-oriented records, hash links, protected signed checkpoints and backups |
| T15 | Signing key compromise | Forged integrity evidence | Key separation, restricted access, rotation and recovery procedure |
| T16 | False-positive security response | Candidate disruption | Proportional action, thresholds, review, reason codes and false-positive tests |
| T17 | Service/dependency outage | Lost availability | Health checks, degraded mode, backups and recovery tests |
| T18 | Standalone host failure/compromise | All local services affected | Host hardening, physical controls, backups and explicit single-host risk |
| T19 | Worker lateral movement | Platform compromise | Separate worker network, narrow authenticated API, no DB credentials on workers |
| T20 | Sensitive data in logs/metrics | Privacy breach | Redaction, access control, retention limits; no tokens or answer bodies in logs |

## 6. Policy examples by assessment
- MCQ: attempt-scoped authorization, server deadline, idempotent saves, rate limits.
- Descriptive: input/output validation, safe rendering, durable autosave and content limits.
- File upload: size/type/content validation, generated names, quotas and isolated storage.
- Coding: isolated execution, CPU/RAM/time/process limits, no secrets and network disabled by default.
- Administration: strong authorization, frozen published versions and audit.
- Capsule import: strict schema, safe archive paths, decompression limits and integrity checks.

## 7. Risk rating
Use qualitative likelihood (Low/Medium/High) and impact (Low/Medium/High/Critical), with human review of priority. Do not present this as quantitative risk analysis.

## 8. Residual risks
- Browser controls cannot guarantee prevention of external-device use or all cheating.
- Privileged host/admin compromise can undermine application-level evidence.
- A hash chain alone cannot stop a privileged attacker rewriting the entire chain; protected signed checkpoints or external anchoring are needed.
- Containers share the host kernel and are not equivalent to separate physical machines.
- Standalone has a single-host failure domain.
- Detection covers only observable signals and tested scenarios.
- Weak signals must not automatically result in candidate punishment.

## 9. Verification evidence
For each control record threat ID, requirement ID, implementation location, positive test, abuse/negative test, evidence and limitation. Test only LANCAST environments or systems for which explicit authorization exists.
