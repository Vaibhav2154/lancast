# ADR-001: Core Application Stack and Gateway Topology

- **Status:** Accepted (Phase 0/1)
- **Date:** 2026-11-24
- **Decisions covered:** `O-01`, `O-03`, `O-04`, `TD-01`, `TD-02`, `TD-08`

## Context
LANCAST must support both a **standalone single-machine deployment** (zero separate worker machines) and a **centralized campus deployment** (optional separate execution workers) using the exact same application and orchestration code, while keeping solo-developer operational complexity low.

## Decision
1. **Gateway:** **Traefik** on `:80` (dev) and `:443` (LAN TLS) as the single LAN front door, exposing only the web SPA and `/api/*` to candidate browsers and providing native Prometheus metrics and health-checked routing.
2. **Frontend (`O-01`):** **React + Vite + TypeScript** compiled to a static SPA served by **nginx** behind Traefik — zero client Internet/CDN dependencies during exams.
3. **Backend (`TD-01`):** **Python + FastAPI** modular monolith hosting identity, tenancy, assessments, attempts, capsules, and both orchestration engines behind clear module interfaces.
4. **Queue/Cache (`O-04`):** **Redis** behind an explicit queue abstraction (`ExecutionQueueContract`) for Phase 1–2.
5. **Code Execution (`O-03`):** **Judge0 (`judge0-server` -> worker -> `isolate`)** kept outside the FastAPI process, dispatched via a bounded queue and adaptive dispatcher (with round-robin/failover and FIFO/static modes as experimental baselines).

## Consequences
- **Positive:** Single codebase deploys identically in standalone and central Compose profiles; candidate browsers never touch internal DB/Redis/worker ports; clear separation between interactive API and untrusted code execution.
- **Trade-offs:** Judge0 + `isolate` container isolation must be audited and documented in Phase 1/3; Redis durability/retry semantics will be benchmarked before deciding if a dedicated broker is ever needed.
