"""Lightweight Linux host telemetry collector and Prometheus metrics for execution workers.

Uses /proc and shutil.disk_usage so slim containers require zero native C extensions (FR-RES-01).
"""

import shutil
import time
from pathlib import Path
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, start_http_server

WORKER_JOBS_TOTAL = Counter(
    "lancast_worker_jobs_total",
    "Total coding evaluation jobs processed by execution workers",
    ["language", "status"],
)

WORKER_JOB_DURATION_SECONDS = Histogram(
    "lancast_worker_job_duration_seconds",
    "End-to-end coding job evaluation time inside the execution worker",
    ["language"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0),
)

WORKER_ACTIVE_JOBS = Gauge(
    "lancast_worker_active_jobs",
    "Number of coding jobs currently running in this dispatcher",
)

WORKER_JUDGE0_UP = Gauge(
    "lancast_worker_judge0_up",
    "1 when Judge0 /about responds 200 OK, else 0",
)

WORKER_HOST_CPU_PERCENT = Gauge(
    "lancast_worker_host_cpu_percent",
    "Observed host CPU utilization percentage on the worker node",
)

WORKER_HOST_MEMORY_PERCENT = Gauge(
    "lancast_worker_host_memory_percent",
    "Observed host memory utilization percentage on the worker node",
)

WORKER_HOST_DISK_PERCENT = Gauge(
    "lancast_worker_host_disk_percent",
    "Observed root filesystem disk utilization percentage on the worker node",
)


def start_metrics_server(port: int) -> None:
    start_http_server(port)


class HostTelemetryCollector:
    """Computes delta-based CPU and network throughput plus RAM and disk percentages."""

    def __init__(self, proc_root: str = "/proc", disk_path: str = "/") -> None:
        self._proc = Path(proc_root)
        self._disk_path = disk_path
        self._prev_cpu: tuple[int, int] | None = self._read_cpu_totals()
        self._prev_net: tuple[float, int, int] | None = self._read_net_totals()

    def _read_cpu_totals(self) -> tuple[int, int] | None:
        try:
            line = (self._proc / "stat").read_text(encoding="utf-8").splitlines()[0]
            parts = [int(x) for x in line.split()[1:]]
            idle = parts[3] + (parts[4] if len(parts) > 4 else 0)
            total = sum(parts)
            return idle, total
        except (OSError, ValueError, IndexError):
            return None

    def _read_memory_percent(self) -> float:
        try:
            values: dict[str, int] = {}
            for line in (self._proc / "meminfo").read_text(encoding="utf-8").splitlines():
                key, rest = line.split(":", 1)
                values[key.strip()] = int(rest.strip().split()[0])
            total = values.get("MemTotal", 0)
            avail = values.get("MemAvailable", values.get("MemFree", 0))
            if total <= 0:
                return 0.0
            used = max(0, total - avail)
            return round(min(100.0, (used / total) * 100.0), 2)
        except (OSError, ValueError, IndexError):
            return 0.0

    def _read_disk_percent(self) -> float:
        try:
            usage = shutil.disk_usage(self._disk_path)
            if usage.total <= 0:
                return 0.0
            return round(min(100.0, (usage.used / usage.total) * 100.0), 2)
        except OSError:
            return 0.0

    def _read_net_totals(self) -> tuple[float, int, int] | None:
        try:
            rx_bytes = 0
            tx_bytes = 0
            for line in (self._proc / "net" / "dev").read_text(encoding="utf-8").splitlines()[2:]:
                if ":" not in line:
                    continue
                iface, rest = line.split(":", 1)
                if iface.strip() == "lo":
                    continue
                cols = rest.split()
                if len(cols) >= 9:
                    rx_bytes += int(cols[0])
                    tx_bytes += int(cols[8])
            return time.monotonic(), rx_bytes, tx_bytes
        except (OSError, ValueError, IndexError):
            return None

    def sample(self) -> dict[str, Any]:
        cpu_pct = 0.0
        cur_cpu = self._read_cpu_totals()
        if cur_cpu is not None and self._prev_cpu is not None:
            d_idle = cur_cpu[0] - self._prev_cpu[0]
            d_total = cur_cpu[1] - self._prev_cpu[1]
            if d_total > 0:
                cpu_pct = round(max(0.0, min(100.0, (1.0 - d_idle / d_total) * 100.0)), 2)
        if cur_cpu is not None:
            self._prev_cpu = cur_cpu

        mem_pct = self._read_memory_percent()
        disk_pct = self._read_disk_percent()

        rx_kbps = 0.0
        tx_kbps = 0.0
        cur_net = self._read_net_totals()
        if cur_net is not None and self._prev_net is not None:
            dt = cur_net[0] - self._prev_net[0]
            if dt > 0:
                rx_kbps = round(max(0.0, (cur_net[1] - self._prev_net[1]) / 1024.0 / dt), 2)
                tx_kbps = round(max(0.0, (cur_net[2] - self._prev_net[2]) / 1024.0 / dt), 2)
        if cur_net is not None:
            self._prev_net = cur_net

        WORKER_HOST_CPU_PERCENT.set(cpu_pct)
        WORKER_HOST_MEMORY_PERCENT.set(mem_pct)
        WORKER_HOST_DISK_PERCENT.set(disk_pct)

        return {
            "cpu_percent": cpu_pct,
            "memory_percent": mem_pct,
            "disk_percent": disk_pct,
            "network_rx_kbps": rx_kbps,
            "network_tx_kbps": tx_kbps,
        }
