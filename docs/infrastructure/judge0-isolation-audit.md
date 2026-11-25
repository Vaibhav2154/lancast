# Judge0 + Isolate Sandbox Isolation Audit (`O-03`)

- **Date:** 2026-11-25
- **Scope:** Out-of-process code execution (`execution/`, `docker-compose.coding.yml`, `infrastructure/profiles/central/compose.worker.yml`)
- **Requirements Covered:** `FR-CODE-01..05`, `NFR-SEC-04`, `T07`, `T08`, `T18`, `T19`
- **Status:** Audited — approved with documented mitigations and residual risks (`O-03` closed).

---

## 1. Architecture Summary

Untrusted candidate source code never executes inside the FastAPI container (`FR-CODE-01`). Instead:

1. **Bounded Queue Boundary:** `apps/api` pushes self-contained JSON jobs (`ExecutionJobPayload`) to Redis key `lancast:execution:queue` bounded by `EXECUTION_QUEUE_MAX_DEPTH` (`RedisExecutionQueue` Lua guard). Interactive `Run Code` calls use `Judge0CodeRunner` over HTTP against `judge0-server:2358` with public `sample_cases` or `custom_stdin` only — never hidden tests.
2. **Credential-Free Dispatcher:** `execution/dispatcher/worker.py` pulls jobs via `BLPOP`, forwards each test case to `Judge0Runner`, and posts pass/fail verdicts plus periodic heartbeats (`POST /api/internal/workers/heartbeat`) to the API using `X-Worker-Token`. The dispatcher container holds **zero PostgreSQL credentials** (`T19`).
3. **Ephemeral Isolate Sandboxes:** `judge0-server` and `judge0-worker` (`judge0/judge0:1.13.1`) invoke `isolate` per compile/run step.

---

## 2. Implemented Controls

| Control | Implementation | Threat Mitigated |
|---|---|---|
| Out-of-process execution | Separate `dispatcher`, `judge0-server`, `judge0-worker` containers | T07, NFR-REL-01 |
| Network isolation (job runtime) | `ENABLE_NETWORK: "false"` in Judge0 + `enable_network: False` per request | T07, FR-CODE-04 |
| Docker network segmentation | `judge0-*` reside strictly on `lancast_execution` (cannot resolve/reach `postgres` or `traefik`) | T08, T19 |
| Non-privileged app/dispatcher services | `security_opt: [no-new-privileges:true]` + `pids_limit` + `mem_limit` + `cpus` on `traefik`, `web`, `api`, `postgres`, `redis`, `dispatcher` | T08, T09 |
| Physical host RAM caps on Judge0 | `mem_limit: 1536m`, `cpus: "2.0"` on `judge0-server` and `judge0-worker` | T09 |
| Per-process time & virtual memory bounds | `ENABLE_PER_PROCESS_AND_THREAD_TIME_LIMIT: "true"`, `ENABLE_PER_PROCESS_AND_THREAD_MEMORY_LIMIT: "true"`, `MAX_CPU_TIME_LIMIT: "10"` | T07, T09 |
| Base64 UTF-8 I/O safety | Both `Judge0CodeRunner` and `Judge0Runner` send `base64_encoded=true`, preventing binary/Unicode compiler output failures | T07 |
| Secret separation | Neither `judge0-*` nor `dispatcher` receives `DATABASE_URL`, `AUTH_SECRET_KEY`, or Postgres credentials; `/api/internal/*` is blocked at Traefik `:80`/`:443` | T11, T19 |

---

## 3. Why `privileged: true` and `MAX_MEMORY_LIMIT: "8388608"` Are Required

1. **`privileged: true` on `judge0-server` and `judge0-worker`:**
   - `isolate` creates per-submission mount/PID/network namespaces and `setuid` sandboxes (`box-N`) inside the container. Unprivileged Docker containers drop capabilities (`CAP_SYS_ADMIN`, `CAP_SYS_CHROOT`, `CAP_SETUID`) required by `isolate`, causing inline (`wait=true`) and background runs to fail.
   - Because `judge0-server` and `judge0-worker` run privileged, they MUST remain separated on `lancast_execution` (with no Postgres route and no application secrets) and, in **Central** deployments (`compose.worker.yml`), SHOULD run on dedicated worker hosts physically separated from the PostgreSQL primary (`T08`, `T18`).
2. **Linux cgroup v2 (`7.2.x`+) and `RLIMIT_AS` (`8388608` KB):**
   - `judge0/judge0:1.13.1` assumes cgroup v1 `/sys/fs/cgroup/memory/` hierarchies when `--cg` is active, failing on modern cgroup v2 Linux hosts (`Failed to create control group /sys/fs/cgroup/memory/box-1/`).
   - Enabling `ENABLE_PER_PROCESS_AND_THREAD_TIME_LIMIT: "true"` and `ENABLE_PER_PROCESS_AND_THREAD_MEMORY_LIMIT: "true"` switches `isolate` from `--cg-mem` to `-m` (`RLIMIT_AS`, virtual address space).
   - OpenJDK 13 and Node.js V8 reserve multi-gigabyte **virtual** address mappings upfront (observed live: OpenJDK requires `>4 GB` `RLIMIT_AS` for heap + compressed class space + code cache), so `MAX_MEMORY_LIMIT` is set to `"8388608"` KB (`8 GB` virtual address ceiling) with per-language virtual floors (`2048000` KB for JS, `8388608` KB for Java), while **actual physical RAM** usage is bounded at the container cgroup level via Docker `mem_limit: 1536m`.

---

## 4. Residual Risks & Operational Guidance

- **Shared Host Kernel (`T08`, `04_THREAT_MODEL.md §8`):** Containers share the Linux kernel with the host. For high-stakes multi-tenant or adversarial coding exams, deploy **Central profile** (`infrastructure/profiles/central/compose.worker.yml`) on dedicated lab/VM worker nodes rather than co-locating `privileged: true` Judge0 containers with PostgreSQL on the standalone host.
- **Single-Host Blast Radius (`T18`):** Standalone mode concentrates `postgres` and `judge0-*` on one OS; host compromise affects all local services.
- **Pre-event Capacity Testing:** Always keep `mem_limit` aligned with physical host RAM (observed `16 GB` on testbed) when running `judge0-server` + `judge0-worker` concurrently. Phase 5 adaptive scheduling will throttle concurrent dispatch using worker telemetry.
