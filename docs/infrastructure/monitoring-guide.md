# LANCAST Monitoring & Telemetry Guide (Phase 4)

**Covers:** `FR-RES-01`, `FR-ADM-01..02`, `FR-OBS-01..03`, `FR-CODE-05`, `NFR-PERF-02`, `NFR-PRIV-01`, `TD-06`, `T12`, `T20`

LANCAST separates **telemetry collection** (Prometheus + exporters + normalized `telemetry_samples` ingestion) from **orchestration decisions** (Phase 5/6) so monitoring remains observable, auditable, and independently testable (`TD-06`).

---

## 1. Quick Start

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.coding.yml \
  -f docker-compose.monitoring.yml \
  up -d --build

docker compose exec -T api alembic upgrade head
./infrastructure/scripts/verify-monitoring.sh
```

- **Grafana (operator-only loopback default):** `http://127.0.0.1:3000` (`admin` / `GRAFANA_ADMIN_PASSWORD`)
  - Home dashboard: **LANCAST — Workload & Exam Latency Overview** (`lancast-overview`)
  - Secondary dashboard: **LANCAST — Host, Container, DB & Worker Telemetry** (`lancast-infrastructure`)
- **Prometheus (operator-only loopback default):** `http://127.0.0.1:9090`
- **Admin UI Telemetry Panel:** `http://localhost/admin` (`GET /api/admin/telemetry`)

> Grafana analytics reporting and update checks are explicitly disabled (`GF_ANALYTICS_REPORTING_ENABLED=false`, `GF_ANALYTICS_CHECK_FOR_UPDATES=false`) for zero runtime Internet dependency (`DEP-06`).

---

## 2. Metrics Catalog

### 2.1 FastAPI API (`http://api:8000/metrics` — blocked with `403` at Traefik)
| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `lancast_http_requests_total` | Counter | `method`, `workload_class`, `status_class` | Request volume & error rate per workload class |
| `lancast_http_request_duration_seconds` | Histogram | `workload_class` | P50/P95/P99 latency (`5ms`..`10s` buckets) |
| `lancast_http_in_progress_requests` | Gauge | `workload_class` | Concurrent in-flight requests |
| `lancast_execution_queue_depth` | Gauge | — | Bounded Redis queue depth (`LLEN`) |
| `lancast_execution_dead_letter_depth` | Gauge | — | Dead-letter queue depth |
| `lancast_execution_queue_rejections_total` | Counter | — | `503 QUEUE_FULL` admission shed events |
| `lancast_submissions_total` | Counter | `status` | Submission outcomes (`scored`, `evaluating`, `pending_review`, `replayed`) |
| `lancast_autosave_total` | Counter | `outcome` | Autosave outcomes (`applied`, `replayed`, `conflict`) |
| `lancast_code_run_total` | Counter | `language`, `verdict` | Interactive `/run` executions by language & verdict |
| `lancast_authz_denials_total` | Counter | `reason_code` | Server-side authorization denials (`NOT_MEMBER`, `ROLE_FORBIDDEN`, etc.) |

**Bounded Workload Classes (`apps/api/app/core/metrics.py`):** `interactive_autosave`, `interactive_read`, `submission`, `file_upload`, `code_run`, `auth`, `organizer_admin`, `internal_worker`, `health`, `other`.

### 2.2 Execution Dispatcher (`http://dispatcher:9108/metrics`)
| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `lancast_worker_jobs_total` | Counter | `language`, `status` | Graded coding jobs by language & status |
| `lancast_worker_job_duration_seconds` | Histogram | `language` | End-to-end hidden-test execution latency |
| `lancast_worker_active_jobs` | Gauge | — | Currently executing jobs on worker |
| `lancast_worker_judge0_up` | Gauge | — | `1` if Judge0 `/about` returns `200`, else `0` |
| `lancast_worker_host_{cpu,memory,disk}_percent` | Gauge | — | Worker node CPU / RAM / disk % |

### 2.3 Infrastructure Exporters (Internal `lancast_monitoring` Network)
- `node-exporter:9100` — Host CPU, RAM, disk, network.
- `cadvisor:8080` — Per-container CPU & working-set RAM (`--docker_only=true`, `15s` housekeeping).
- `postgres-exporter:9187` — PostgreSQL connections, transactions, locks.
- `redis-exporter:9121` — Redis memory, connected clients, ops/sec.
- `traefik:8082/metrics` — Gateway entrypoint & service metrics.

---

## 3. Normalized Telemetry Ingestion & Stale Detection (`T12`, `FR-RES-10`)

Workers post normalized `TelemetrySample` payloads every 15s to `POST /api/internal/telemetry/samples` using `X-Worker-Token`:
- **Anti-spoofing validation (`T12`):** Rejects unauthenticated requests (`401`), out-of-range percentages (`422`), and timestamps more than `TELEMETRY_MAX_CLOCK_SKEW_SECONDS` (`60s`) in the future (`422 CLOCK_SKEW`).
- **Stale/missing detection (`GET /api/admin/telemetry`):** Any machine whose latest sample is older than `TELEMETRY_STALE_SECONDS` (`45s`) is marked `stale: true`. When no fresh samples exist (`telemetry_state: "missing"`) or any node is stale/unhealthy (`telemetry_state: "degraded"`), `safe_fallback_active` flips to `true` so Phase 5 orchestration refuses unsafe scale-up.
- **Retention bounds (`T20`):** PostgreSQL `telemetry_samples` auto-prunes rows older than `TELEMETRY_RETENTION_HOURS` (`24h`), while Prometheus TSDB caps retention at `15d` / `2GB`.

---

## 4. Central Remote Worker Scraping

Prometheus watches `infrastructure/monitoring/prometheus/targets/workers.json` via `file_sd_configs` (reloads every 30s with zero restart). To monitor remote lab worker nodes in Central mode, bind `WORKER_METRICS_BIND_IP` on each worker node and append its `<worker_ip>:9108` entry to `workers.json`.

---

## 5. Alert Rules (`infrastructure/monitoring/prometheus/alerts.yml`)

Ten validated alert rules cover availability (`LancastApiDown`, `LancastWorkerOffline`, `LancastJudge0Unhealthy`, `LancastTelemetryStale`) and capacity (`LancastQueueHigh`, `LancastQueueRejections`, `LancastAutosaveLatencyHigh`, `LancastHostCpuHigh`, `LancastHostMemoryHigh`, `LancastDiskSpaceLow`).

> Note (`O-08`): Latency thresholds (e.g., `500 ms` autosave P95) are provisional operational warnings; formal research SLOs will be calibrated from Phase 8 pilot measurements.

---

## 6. Privacy & Measured Monitoring Overhead (`T20`, Phase 4 Exit Evidence)

- **Privacy verification:** Automated tests (`apps/api/tests/test_metrics.py`) and `verify-monitoring.sh` confirm candidate emails, passwords, JWTs, attempt UUIDs, and answer payloads never appear in `/metrics` labels or structured logs. `/metrics` returns `403` at Traefik on `:80` and `:443`.
- **Measured overhead on recorded testbed** (Intel i7-11800H 8C/16T, 16 GB RAM, Linux 7.2.15, Docker 29.9.2):
  - **Container footprint (`docker stats --no-stream`):**
    | Container | Idle CPU % | Memory Usage / Limit |
    |---|---|---|
    | `lancast-prometheus-1` | `0.17%` | `57.09 MiB / 512 MiB` |
    | `lancast-grafana-1` | `0.05%` | `77.39 MiB / 384 MiB` |
    | `lancast-cadvisor-1` | `0.58%` | `47.54 MiB / 192 MiB` |
    | `lancast-postgres-exporter-1` | `0.00%` | `22.47 MiB / 96 MiB` |
    | `lancast-node-exporter-1` | `0.00%` | `22.00 MiB / 64 MiB` |
    | `lancast-redis-exporter-1` | `0.00%` | `19.47 MiB / 64 MiB` |
    | **Total Monitoring Stack** | **~0.80%** | **~246 MiB** |
  - **FastAPI ASGI instrumentation delta (`n = 2000`):** `plain = 0.45 µs`, `instrumented = 12.25 µs`, **delta = `+11.80 µs/req`** (~0.012 ms/req).
  - **Live `/api/health` with instrumentation (`n = 100`):** `P50 = 0.39 ms`, `P95 = 0.58 ms`, `P99 = 0.86 ms`.
