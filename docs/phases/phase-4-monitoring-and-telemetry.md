# Phase 4 — Monitoring and Telemetry

**Status:** Complete | **Exit Condition:** Host, container, API (workload-classified P50/P95/P99), database, queue, and worker metrics collected and attributable; normalized telemetry schema with stale/missing detection tested; Grafana dashboards and Prometheus alerts provisioned; monitoring overhead measured; sensitive candidate data excluded.

---

## 1. Requirements & Threat Coverage

- **Observability & Telemetry:** `FR-RES-01`, `FR-ADM-01..02`, `FR-OBS-01..03`, `FR-CODE-05`, `NFR-PERF-02`, `NFR-PRIV-01`
- **Architecture & Security:** `TD-06` (monitoring separated from orchestration decisions), `T11`, `T12` (telemetry spoofing/clock-skew/stale detection), `T20` (no PII/secrets in metrics, loopback operator ports, bounded retention)

---

## 2. Workload-Aware API Instrumentation (`apps/api/`)

- **[app/core/metrics.py](../../apps/api/app/core/metrics.py):**
  - Pure ASGI `PrometheusMiddleware` measuring request counts, in-progress concurrency, and P50/P95/P99 latency histograms (`5 ms`..`10 s` buckets) grouped strictly by bounded `workload_class` (`interactive_autosave`, `interactive_read`, `submission`, `file_upload`, `code_run`, `auth`, `organizer_admin`, `internal_worker`, `health`, `other`).
  - Domain counters wired into [core/deps.py](../../apps/api/app/core/deps.py), [services/attempts.py](../../apps/api/app/services/attempts.py), and [routers/attempts.py](../../apps/api/app/routers/attempts.py): `lancast_autosave_total`, `lancast_submissions_total`, `lancast_code_run_total`, `lancast_execution_queue_rejections_total`, and `lancast_authz_denials_total`.
  - Bounded in-memory sliding window (`deque(maxlen=1000)`) per workload class powers fast rolling P50/P95/P99 summaries in `GET /api/admin/telemetry`.
- **Internal `/metrics` Exposure & Gateway Block:**
  - Exposed at `GET /metrics` in [app/routers/health.py](../../apps/api/app/routers/health.py) (refreshes `lancast_execution_queue_depth` and `lancast_execution_dead_letter_depth` on scrape).
  - Blocked with `403` at Traefik on `:80` and `:443` ([routes.yml](../../infrastructure/gateway/dynamic/routes.yml), [tls-routes.yml](../../infrastructure/gateway/tls-dynamic/tls-routes.yml)); added dedicated internal Traefik `:8082` metrics entrypoint in [traefik.yml](../../infrastructure/gateway/traefik.yml).

---

## 3. Normalized Telemetry Pipeline & Worker Metrics

- **Database & Migration:** Added `TelemetrySampleRecord` in [models.py](../../apps/api/app/db/models.py) and Alembic migration [0004_telemetry_samples.py](../../apps/api/alembic/versions/0004_telemetry_samples.py) (`telemetry_samples` indexed on `machine_id` and `collected_at`).
- **Ingestion & Stale Detection ([services/telemetry.py](../../apps/api/app/services/telemetry.py), [routers/internal.py](../../apps/api/app/routers/internal.py), [routers/admin.py](../../apps/api/app/routers/admin.py)):**
  - `POST /api/internal/telemetry/samples` (`X-Worker-Token`): validates `0..100%` ranges, rejects future timestamps exceeding `TELEMETRY_MAX_CLOCK_SKEW_SECONDS` (`422 CLOCK_SKEW`), persists samples, and prunes rows older than `TELEMETRY_RETENTION_HOURS` (`24h`).
  - `GET /api/admin/telemetry` (`PlatformAdmin`): computes per-machine staleness (`age_seconds > 45s`) and derives `telemetry_state` (`healthy` | `degraded` | `missing`) plus `safe_fallback_active` for Phase 5 orchestration.
- **Execution Dispatcher ([execution/dispatcher/telemetry.py](../../execution/dispatcher/telemetry.py), [worker.py](../../execution/dispatcher/worker.py)):**
  - Pure-Python `/proc` + `shutil.disk_usage` collector (zero C-extension overhead) sampling host CPU %, RAM %, disk %, and network RX/TX KB/s.
  - Exposes Prometheus metrics on `:9108/metrics` (`lancast_worker_jobs_total`, `lancast_worker_job_duration_seconds`, `lancast_worker_active_jobs`, `lancast_worker_judge0_up`, `lancast_worker_host_*`) and posts normalized samples alongside 15s heartbeats.

---

## 4. Prometheus, Exporters, Grafana & Admin UI

- **Monitoring Overlay ([docker-compose.monitoring.yml](../../docker-compose.monitoring.yml)):**
  - `prometheus:v2.55.1` (`15d`/`2GB` TSDB retention, loopback `127.0.0.1:9090`), `grafana:11.3.1` (loopback `127.0.0.1:3000`, analytics/update checks disabled), `node-exporter:v1.8.2`, `cadvisor:v0.49.1` (`--docker_only=true`, 15s housekeeping), `postgres-exporter:v0.16.0`, and `redis-exporter:v1.66.0`.
  - Dynamic worker scrape targets via `file_sd_configs` ([workers.json](../../infrastructure/monitoring/prometheus/targets/workers.json)) and 10 alert rules ([alerts.yml](../../infrastructure/monitoring/prometheus/alerts.yml)).
  - Two auto-provisioned Grafana dashboards: [lancast-overview.json](../../infrastructure/monitoring/grafana/dashboards/lancast-overview.json) and [lancast-infrastructure.json](../../infrastructure/monitoring/grafana/dashboards/lancast-infrastructure.json).
- **Admin UI ([AdminPage.tsx](../../apps/web/src/pages/AdminPage.tsx), [api.ts](../../apps/web/src/lib/api.ts), [StatusBadge.tsx](../../apps/web/src/components/StatusBadge.tsx)):** Added **Host Telemetry & Workload Latency** section displaying `telemetry_state` / Safe Fallback badge, live per-machine CPU/RAM/Disk/Net + staleness age, and rolling P50/P95/P99 latency chips.

---

## 5. Verification Evidence

- **Automated Tests & Lint:**
  - `apps/api`: `uv run ruff check app tests alembic` (0 errors); `uv run pytest -q` (**80/80 passed**, including [test_metrics.py](../../apps/api/tests/test_metrics.py) and [test_telemetry.py](../../apps/api/tests/test_telemetry.py)).
  - `execution`: `uv run ruff check dispatcher tests` (0 errors); `uv run pytest -q` (**8/8 passed**).
  - `apps/web`: `npm test` (**5/5 Vitest passed**); `npm run build` (`tsc -b && vite build`) clean.
- **Database Migration Round-Trip (PostgreSQL 16):** `0004_telemetry_samples` verified across `upgrade head -> downgrade base -> upgrade head -> alembic check` with zero schema drift.
- **Live Stack & Privacy Audit ([verify-monitoring.sh](../../infrastructure/scripts/verify-monitoring.sh)):**
  - `promtool check config` & `promtool check rules` (10 rules valid).
  - All **8/8** Prometheus targets `UP`, both Grafana dashboards provisioned, `/metrics` blocked with `403` through Traefik, and zero candidate emails/passwords/JWTs/answers present in `/metrics`.
- **Measured Overhead:** Total 6-container monitoring footprint `~0.80% CPU` and `~246 MiB RAM`; `PrometheusMiddleware` ASGI delta `+11.80 µs/req` (`n = 2000`); live `/api/health` `P50 = 0.39 ms`, `P95 = 0.58 ms`, `P99 = 0.86 ms` (`n = 100`).
