"""Workload-aware Prometheus metrics and low-overhead ASGI middleware (FR-OBS-01..03, NFR-PERF-02).

Strictly excludes candidate emails, JWTs, answer payloads, and raw resource UUIDs from all metric
labels to uphold T20 privacy guarantees and prevent cardinality blowup.
"""

import math
import time
from collections import deque
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.types import ASGIApp, Message, Receive, Scope, Send

LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

HTTP_REQUESTS_TOTAL = Counter(
    "lancast_http_requests_total",
    "Total HTTP requests by method, workload class, and HTTP status class",
    ["method", "workload_class", "status_class"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "lancast_http_request_duration_seconds",
    "HTTP request duration in seconds by workload class (supports P50/P95/P99)",
    ["workload_class"],
    buckets=LATENCY_BUCKETS,
)

HTTP_IN_PROGRESS_REQUESTS = Gauge(
    "lancast_http_in_progress_requests",
    "In-flight HTTP requests by workload class",
    ["workload_class"],
)

EXECUTION_QUEUE_DEPTH = Gauge(
    "lancast_execution_queue_depth",
    "Current depth of the bounded Redis execution queue",
)

EXECUTION_DEAD_LETTER_DEPTH = Gauge(
    "lancast_execution_dead_letter_depth",
    "Current depth of the execution dead-letter queue",
)

EXECUTION_QUEUE_REJECTIONS_TOTAL = Counter(
    "lancast_execution_queue_rejections_total",
    "Total coding job enqueues rejected due to bounded queue saturation (503 QUEUE_FULL)",
)

SUBMISSIONS_TOTAL = Counter(
    "lancast_submissions_total",
    "Total assessment submissions by resulting status",
    ["status"],
)

AUTOSAVE_TOTAL = Counter(
    "lancast_autosave_total",
    "Total candidate autosave requests by outcome (applied, replayed, conflict)",
    ["outcome"],
)

CODE_RUN_TOTAL = Counter(
    "lancast_code_run_total",
    "Total interactive candidate code runs by language and verdict",
    ["language", "verdict"],
)

AUTHZ_DENIALS_TOTAL = Counter(
    "lancast_authz_denials_total",
    "Total server-side authorization denials by reason code",
    ["reason_code"],
)

# Bounded in-memory sliding window per workload class for quick Admin UI percentile summaries.
_ROLLING_LATENCIES_MS: dict[str, deque[float]] = {}
_ROLLING_WINDOW_SIZE = 1000


def classify_workload(method: str, path: str) -> str:
    """Map an API path and HTTP method into a bounded LANCAST workload class."""
    m = method.upper()
    if path in ("/metrics", "/api/health", "/api/ready"):
        return "health"
    if path.startswith("/api/auth"):
        return "auth"
    if path.startswith("/api/internal"):
        return "internal_worker"
    if path.startswith("/api/attempts/"):
        if m == "PUT" and "/responses/" in path:
            return "interactive_autosave"
        if m == "POST" and path.endswith("/submit"):
            return "submission"
        if m == "POST" and path.endswith("/upload"):
            return "file_upload"
        if m == "POST" and path.endswith("/run"):
            return "code_run"
        return "interactive_read"
    if path.startswith("/api/me"):
        return "interactive_read"
    if path.startswith("/api/tenants/"):
        if "/uploads/" in path:
            return "file_upload"
        if m == "POST" and path.endswith("/attempts"):
            return "interactive_read"
        return "organizer_admin"
    if path.startswith("/api/admin"):
        return "organizer_admin"
    return "other"


def record_latency_sample(workload_class: str, duration_sec: float) -> None:
    if workload_class == "health":
        return
    buf = _ROLLING_LATENCIES_MS.get(workload_class)
    if buf is None:
        buf = deque(maxlen=_ROLLING_WINDOW_SIZE)
        _ROLLING_LATENCIES_MS[workload_class] = buf
    buf.append(round(duration_sec * 1000.0, 3))


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, math.ceil((pct / 100.0) * len(sorted_vals)) - 1))
    return round(sorted_vals[idx], 2)


def get_latency_summary() -> dict[str, dict[str, Any]]:
    """Return rolling P50/P95/P99 latency (ms) and sample count per workload class."""
    summary: dict[str, dict[str, Any]] = {}
    for wclass, samples in sorted(_ROLLING_LATENCIES_MS.items()):
        if not samples:
            continue
        ordered = sorted(samples)
        summary[wclass] = {
            "count": len(ordered),
            "p50_ms": _percentile(ordered, 50),
            "p95_ms": _percentile(ordered, 95),
            "p99_ms": _percentile(ordered, 99),
        }
    return summary


def render_prometheus_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


class PrometheusMiddleware:
    """Pure ASGI middleware for low-overhead per-workload latency and status tracking."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "GET")).upper()
        path = str(scope.get("path", "/"))
        workload_class = classify_workload(method, path)
        status_code = 500
        start = time.perf_counter()

        HTTP_IN_PROGRESS_REQUESTS.labels(workload_class=workload_class).inc()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = max(0.0, time.perf_counter() - start)
            status_class = f"{status_code // 100}xx"
            HTTP_IN_PROGRESS_REQUESTS.labels(workload_class=workload_class).dec()
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                workload_class=workload_class,
                status_class=status_class,
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(workload_class=workload_class).observe(duration)
            record_latency_sample(workload_class, duration)
