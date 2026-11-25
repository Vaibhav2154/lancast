# LANCAST Deployment & Operations Guide (Phase 3)

**Covers:** `DEP-01..07`, `ADR-001..003`, `FR-ADM-01..02`, `NFR-PORT-01`, `NFR-REL-03`, `NFR-SEC-01..03`

Both **Standalone** and **Central** deployments run the exact same `apps/api`, `apps/web`, and `execution` images (`DEP-03`) with zero Internet connectivity required at runtime (`DEP-06`).

---

## 1. Prerequisites
- Linux host(s) with Docker Engine (`24+`) and Docker Compose v2 (`docker compose`).
- OpenSSL (only needed once when generating offline LAN TLS certificates).

---

## 2. Deployment Profiles

### 2.1 Standalone Single-Server Profile (`DEP-02`, `DEP-04`)
Runs Traefik, React SPA (`web`), FastAPI (`api`), local PostgreSQL, local Redis, and (when `docker-compose.coding.yml` is included) `dispatcher` + `Judge0` on one machine.

```bash
cp infrastructure/profiles/standalone/.env.standalone.example infrastructure/profiles/standalone/.env.standalone
# Edit infrastructure/profiles/standalone/.env.standalone and set real secrets & PUBLIC_BASE_URL

docker compose \
  --env-file infrastructure/profiles/standalone/.env.standalone \
  -f docker-compose.yml \
  -f docker-compose.coding.yml \
  -f infrastructure/profiles/standalone/compose.standalone.yml \
  up -d --build

docker compose exec -T api alembic upgrade head
./infrastructure/scripts/smoke-test.sh
```

> If an event does not have coding questions, omit `-f docker-compose.coding.yml` to reduce RAM usage.

### 2.2 Central Campus Profile (`DEP-01`)
Splits control/data services from heavy untrusted code execution across campus LAN hosts. A single `nginx` `web` container is kept (static SPA assets are gzip-compressed and browser-cached with `Cache-Control: immutable`), while `api` runs as a pool (`API_REPLICAS`, default `2`) behind Traefik.

#### Step A — Central Server (Machine 1)
```bash
cp infrastructure/profiles/central/.env.server.example infrastructure/profiles/central/.env.server
# Set WORKER_BIND_IP to the internal/management LAN IP of this server (e.g. 10.10.0.10)
# Generate strong AUTH_SECRET_KEY and WORKER_SHARED_SECRET

docker compose \
  --env-file infrastructure/profiles/central/.env.server \
  -f docker-compose.yml \
  -f infrastructure/profiles/central/compose.server.yml \
  up -d --build

docker compose exec -T api alembic upgrade head
```

#### Step B — Execution Worker Node(s) (Machines 2..N)
Worker machines run **only** `dispatcher` + local `Judge0` and hold **zero PostgreSQL credentials (`T19`)**:

```bash
cp infrastructure/profiles/central/.env.worker.example infrastructure/profiles/central/.env.worker
# Set REDIS_URL=redis://<WORKER_BIND_IP>:6379/0
# Set API_BASE_URL=http://<WORKER_BIND_IP>:8081
# Set WORKER_SHARED_SECRET to match the central server and give each node a unique WORKER_ID

docker compose \
  --env-file infrastructure/profiles/central/.env.worker \
  -f infrastructure/profiles/central/compose.worker.yml \
  up -d --build
```

Verify workers register as **Online** in **Platform Admin -> Tenants & Infrastructure** (`/admin`, backed by `GET /api/admin/infrastructure`). Workers missing heartbeats for >45 seconds automatically show **Offline (`stale: true`)**.

---

## 3. Offline LAN HTTPS (`O-05`, `ADR-003`)
Public ACME (Let's Encrypt) does not work in offline campus LANs. Generate a local private CA and SAN server certificate instead:

```bash
./infrastructure/scripts/generate-lan-certs.sh 192.168.1.50 lancast.local
```

Then include `-f infrastructure/gateway/compose.tls.yml` when starting Compose, set `PUBLIC_BASE_URL=https://lancast.local` (or `https://192.168.1.50`) in `.env`, and distribute `infrastructure/gateway/certs/lancast-ca.crt` to candidate/organizer lab browsers (or test with `./infrastructure/scripts/smoke-test.sh --url https://localhost --cacert infrastructure/gateway/certs/lancast-ca.crt`).

Never commit `infrastructure/gateway/certs/` or `.env*` files (covered by `.gitignore`, `DEP-07`).

---

## 4. Network Segmentation & Host Firewall (`T11`, `NFR-SEC-02..03`)

Docker Compose enforces three internal bridge networks:
- `lancast_edge`: `traefik` ↔ `web`, `api`
- `lancast_internal`: `api` ↔ `postgres`, `redis` (`dispatcher` only joins `lancast_internal` + `lancast_execution` in Standalone)
- `lancast_execution`: `api`, `dispatcher` ↔ `judge0-server`, `judge0-worker`, `judge0-db`, `judge0-redis` (cannot reach `postgres` or `traefik`)

On the **host firewall** (`ufw` / `nftables`):
- **Standalone / Central candidate interface:** Allow ONLY TCP `80` and `443` from campus candidate/organizer subnets. Never expose `5432` (PostgreSQL), `2358` (Judge0), or `8000` (API directly). `/api/internal/*` is blocked with `403` at Traefik on both `:80` and `:443`.
- **Central worker-management interface (`WORKER_BIND_IP`):** Allow TCP `8081` (Traefik `worker` entrypoint) and TCP `6379` (Redis queue) **strictly from known worker node IPs**.

---

## 5. Optional External PostgreSQL (`ADR-002`)
LANCAST uses local PostgreSQL by default. To point to an external PostgreSQL instance (e.g., an institutional Postgres cluster or Supabase DB URL), set `DATABASE_URL=postgresql+asyncpg://...` in `.env` and run `alembic upgrade head`. Authentication, sessions, RBAC, and authorization stay strictly local inside FastAPI.

---

## 6. External Internet Dependency Audit (`DEP-06`)

| Lifecycle Stage | External Network Access Required? | Details |
|---|---|---|
| **Runtime (Exams active)** | **Zero** | All React/Vite JS/CSS/CodeMirror/Lucide assets are bundled into `web`; local auth, PostgreSQL, Redis, Traefik TLS, and Judge0 execute 100% on campus LAN. |
| **Image Build / Initial Setup** | Build host only | Pulling base Docker images (`python:3.12-slim`, `node:22-alpine`, `nginx:1.27-alpine`, `postgres:16-alpine`, `redis:7-alpine`, `traefik:v3.2`, `judge0/judge0:1.13.1`) and installing `pip`/`npm` packages during `docker compose build`. Pre-build or save images (`docker save`) before moving to an air-gapped exam network. |

---

## 7. Backup & Recovery Runbook (`NFR-REL-03`, `T17`)

- **Backup:**
  ```bash
  ./infrastructure/scripts/backup.sh
  # Creates backups/lancast-backup-<UTC>/ with postgres.dump, uploads.tar.gz, metadata.txt, SHA256SUMS
  ```
- **Non-destructive backup verification (recommended before an exam):**
  ```bash
  ./infrastructure/scripts/restore.sh backups/lancast-backup-<UTC> --target-db lancast_restore_test --yes
  ```
- **Full restore:**
  ```bash
  ./infrastructure/scripts/restore.sh backups/lancast-backup-<UTC> --yes
  ```
