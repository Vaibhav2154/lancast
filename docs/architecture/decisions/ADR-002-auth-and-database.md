# ADR-002: Local PostgreSQL and Local FastAPI Authentication

- **Status:** Accepted (Phase 0/1)
- **Date:** 2026-11-24
- **Decisions covered:** `O-02`, `DEP-04`, `DEP-06`, `TD-03`

## Context
An earlier proof-of-concept relied on cloud Supabase for both PostgreSQL and authentication. During campus exams, relying on external cloud services introduces campus ISP failure risk, WAN jitter in latency benchmarks, and breaks offline lab networks if client browsers attempt to reach cloud auth endpoints.

## Decision
1. **Local PostgreSQL by default:** Both standalone and central profiles run a local PostgreSQL container configured via `DATABASE_URL`, ensuring zero Internet dependency during exams and clean, reproducible latency measurements.
2. **Local FastAPI authentication:** User credentials (salted Argon2/bcrypt hashes), revocable sessions/tokens, and role/tenant memberships are managed exclusively inside FastAPI + PostgreSQL.
3. **Optional external PostgreSQL portability:** Operators may point `DATABASE_URL` to an external PostgreSQL instance (such as Supabase Postgres) later if desired, **without** changing the local FastAPI authentication flow or introducing browser-side Internet dependencies.

## Consequences
- **Positive:** Satisfies `DEP-04` (fully local standalone dependencies); immune to ISP outages; eliminates WAN variance from P50/P95/P99 research experiments.
- **Trade-offs:** LANCAST owns password hashing, session expiry/revocation, and database backup/restore procedures (documented and tested in Phase 2–3).
