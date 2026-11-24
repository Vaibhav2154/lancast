"""Queue consumer: BLPOP job -> run in sandbox -> report result to the API.

This process holds no database credentials. It authenticates to the API's internal endpoint with
a shared secret (T19) and never returns hidden expected output, only pass/fail verdicts.
"""

import json
import logging
import os
import signal
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
    secret = os.environ["WORKER_SHARED_SECRET"]
    worker_id = os.environ.get("WORKER_ID", f"worker-{os.getpid()}")
    runner = Judge0Runner(os.environ.get("JUDGE0_URL", "http://judge0-server:2358"))

    r = redis.Redis.from_url(redis_url)
    http = httpx.Client(timeout=15.0)
    running = True

    def stop(*_: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    log.info("dispatcher %s started", worker_id)
    while running:
        item = r.blpop(QUEUE_KEY, timeout=5)
        if item is None:
            continue
        try:
            job = json.loads(item[1])
            job_id = str(job["job_id"])
        except (ValueError, KeyError):
            log.error("dropping malformed job message")
            r.rpush(DEAD_LETTER_KEY, item[1])
            continue
        result = process_job(job, runner, worker_id)
        if not report_result(http, api_url, secret, job_id, result):
            r.rpush(DEAD_LETTER_KEY, item[1])


if __name__ == "__main__":
    main()
