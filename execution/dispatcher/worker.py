"""Queue consumer: BLPOP job -> run in sandbox -> report result to the API.

This process holds no database credentials. It authenticates to the API's internal endpoint with
a shared secret (T19) and never returns hidden expected output, only pass/fail verdicts.
"""

import json
import logging
import os
import signal
import socket
import time
from typing import Any

import httpx
import redis

from dispatcher.sandbox import Judge0Runner, SandboxError, SandboxRunner

QUEUE_KEY = "lancast:execution:queue"
DEAD_LETTER_KEY = "lancast:execution:dead"
log = logging.getLogger("lancast.dispatcher")


def process_job(job: dict[str, Any], runner: SandboxRunner, worker_id: str) -> dict[str, Any]:
    """Pure function: run every test case, return the result message for the API."""
    results: list[dict[str, Any]] = []
    try:
        for case in job["test_cases"]:
            results.append(runner.run_case(job, case))
    except SandboxError as exc:
        return {"status": "failed", "test_results": [], "worker_id": worker_id, "error": str(exc)[:500]}
    status = "timed_out" if any(r["verdict"] == "timed_out" for r in results) else "completed"
    return {"status": status, "test_results": results, "worker_id": worker_id}


def check_judge0_health(client: httpx.Client, judge0_url: str) -> bool:
    """Probe Judge0 /about; returns False if unreachable or unhealthy."""
    try:
        res = client.get(f"{judge0_url.rstrip('/')}/about")
        return res.status_code == 200
    except httpx.HTTPError:
        return False


def send_heartbeat(
    client: httpx.Client, api_url: str, secret: str, payload: dict[str, Any]
) -> bool:
    """POST worker heartbeat to API; never raises so transient outages don't crash jobs."""
    url = f"{api_url.rstrip('/')}/api/internal/workers/heartbeat"
    try:
        res = client.post(url, json=payload, headers={"X-Worker-Token": secret})
        if res.status_code == 200:
            return True
        log.warning("heartbeat rejected for %s: HTTP %s", payload.get("worker_id"), res.status_code)
    except httpx.HTTPError as exc:
        log.warning("heartbeat failed for %s: %s", payload.get("worker_id"), exc)
    return False


def report_result(
    client: httpx.Client, api_url: str, secret: str, job_id: str, result: dict[str, Any]
) -> bool:
    """POST the result with retries. Returns True on success."""
    url = f"{api_url.rstrip('/')}/api/internal/execution/jobs/{job_id}/result"
    for attempt in range(1, 4):
        try:
            res = client.post(url, json=result, headers={"X-Worker-Token": secret})
            if res.status_code == 200:
                return True
            if res.status_code in (401, 404):  # permanent: retrying will not help
                log.error("result rejected for %s: HTTP %s", job_id, res.status_code)
                return False
        except httpx.HTTPError as exc:
            log.warning("result post failed for %s (attempt %d): %s", job_id, attempt, exc)
        time.sleep(min(2**attempt, 8))
    return False


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    api_url = os.environ.get("API_BASE_URL", "http://api:8000")
    judge0_url = os.environ.get("JUDGE0_URL", "http://judge0-server:2358")
    secret = os.environ["WORKER_SHARED_SECRET"]
    worker_id = os.environ.get("WORKER_ID", f"worker-{os.getpid()}")
    deployment_mode = os.environ.get("DEPLOYMENT_PROFILE", "standalone")
    hostname = socket.gethostname()
    hb_interval = float(os.environ.get("HEARTBEAT_INTERVAL_SEC", "15"))

    runner = Judge0Runner(judge0_url)
    r = redis.Redis.from_url(redis_url)
    http = httpx.Client(timeout=15.0)
    probe_http = httpx.Client(timeout=2.0)
    running = True
    jobs_completed = 0
    jobs_failed = 0

    def stop(*_: object) -> None:
        nonlocal running
        running = False

    def emit_heartbeat(active_jobs: int = 0) -> None:
        send_heartbeat(
            http,
            api_url,
            secret,
            {
                "worker_id": worker_id,
                "hostname": hostname,
                "deployment_mode": deployment_mode,
                "judge0_ok": check_judge0_health(probe_http, judge0_url),
                "active_jobs": active_jobs,
                "jobs_completed": jobs_completed,
                "jobs_failed": jobs_failed,
            },
        )

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    log.info("dispatcher %s started (%s mode)", worker_id, deployment_mode)
    emit_heartbeat(0)
    last_hb = time.monotonic()

    while running:
        now_mono = time.monotonic()
        if now_mono - last_hb >= hb_interval:
            emit_heartbeat(0)
            last_hb = time.monotonic()

        item = r.blpop(QUEUE_KEY, timeout=5)
        if item is None:
            continue
        try:
            job = json.loads(item[1])
            job_id = str(job["job_id"])
        except (ValueError, KeyError):
            log.error("dropping malformed job message")
            r.rpush(DEAD_LETTER_KEY, item[1])
            jobs_failed += 1
            continue

        result = process_job(job, runner, worker_id)
        reported = report_result(http, api_url, secret, job_id, result)
        if not reported:
            r.rpush(DEAD_LETTER_KEY, item[1])
        if result["status"] == "failed" or not reported:
            jobs_failed += 1
        else:
            jobs_completed += 1
        emit_heartbeat(0)
        last_hb = time.monotonic()


if __name__ == "__main__":
    main()
