# 08 — LANCAST Development and Testbed Manifest

**Version:** 1.0 — Phase 0 baseline  
**Date:** 24 November 2026  
**Purpose:** Records the verified local development and standalone testbed hardware/software configuration (`O-07`) required by [01_PROJECT_SRS.md](01_PROJECT_SRS.md) (`NFR-CAP-01`, `NFR-TEST-02`) and [05_EXPERIMENT_PLAN.md](05_EXPERIMENT_PLAN.md).

---

## 1. Primary Local Development & Standalone Testbed (`node-dev-01`)

| Property | Recorded Value |
|---|---|
| **Role** | Primary development machine & standalone single-machine testbed |
| **Architecture** | `x86_64` |
| **CPU** | 11th Gen Intel Core i7-11800H @ 2.30 GHz (8 physical cores / 16 threads, 1 socket) |
| **Memory (RAM)** | 16 GB (15 GiB usable) + 5.0 GiB swap |
| **Storage** | 476.9 GB NVMe SSD (`SAMSUNG MZVL4512HBLU-00BTW`); root partition 207 GB |
| **OS** | Omarchy 4.5.0 (Linux) |
| **Kernel** | `7.2.15-1-omarchy` |
| **Docker Engine** | `29.9.2` (build `a82e528901`) |
| **Docker Compose** | `5.6.1` |
| **Host Python** | `3.14.8` *(container images will pin exact Python version in Phase 1)* |
| **Host Node.js** | `v26.13.0` *(container images will pin exact Node LTS version in Phase 1)* |
| **Network Interfaces** | Gigabit Ethernet (`enp47s0`), Wi-Fi (`wlan0`), USB network interface (`enp0s20f0u4`) |

### Operational Notes
- **Disk headroom:** Root partition `/` had ~12 GB free (95% used) at baseline inspection. Ensure adequate free disk space before pulling Judge0, PostgreSQL, Redis, Prometheus, and Grafana images or storing experiment logs.
- **Reproducibility:** Containerized services MUST pin explicit image digests/versions in Phase 1 so experiments do not drift with host OS updates.

---

## 2. Centralized Multi-Node Testbed (To Be Populated When Available)

| Node | Role | CPU / RAM / Disk | OS / Docker | LAN Link Speed | Status |
|---|---|---|---|---|---|
| `central-gateway` | Traefik + Web + FastAPI + DB/Redis + Monitoring | *TBD (campus lab / VM)* | *TBD* | *TBD* | Pending hardware allocation |
| `worker-01` | Remote Judge0 (`isolate`) execution worker | *TBD* | *TBD* | *TBD* | Pending hardware allocation |

### LAN Topology Checklist (Record Before Pilot / Phase 8 Runs)
- [ ] Switch / Access Point model and Wi-Fi band/channel (if wireless clients are tested).
- [ ] Dedicated test VLAN/SSID and client-isolation setting.
- [ ] Measured baseline LAN RTT and bandwidth between client load generator and gateway.
- [ ] Firewall rules verifying only Traefik (`:80`/`:443`) is reachable from candidate subnet.
