"""Sandbox runners. The runner interface lets tests (and CI) run without privileged Judge0."""

from typing import Any, Protocol

import httpx

# Judge0 CE 1.13.x language ids.
JUDGE0_LANGUAGE_IDS = {
    "python3": 71,
    "c": 50,
    "cpp": 54,
    "java": 62,
    "javascript": 63,
}

# Judge0 status ids -> LANCAST verdicts.
_VERDICTS = {
    3: "accepted",
    4: "wrong_answer",
    5: "timed_out",
    6: "compile_error",
}


class SandboxError(Exception):
    """Infrastructure failure (sandbox unreachable/internal error); not the candidate's fault."""


class SandboxRunner(Protocol):
    def run_case(self, job: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
        """Run one test case. Return {"passed": bool, "verdict": str}."""
        ...


class Judge0Runner:
    """Runs one test case per Judge0 submission. Network access stays disabled (Judge0 default)."""

    def __init__(self, base_url: str, timeout: float = 30.0, client: httpx.Client | None = None):
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)

    def run_case(self, job: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
        language_id = JUDGE0_LANGUAGE_IDS.get(job["language"])
        if language_id is None:
            raise SandboxError(f"unsupported language {job['language']!r}")
        payload = {
            "source_code": job["source_code"],
            "language_id": language_id,
            "stdin": case.get("stdin", ""),
            "expected_output": case["expected_stdout"],
            "cpu_time_limit": job["cpu_time_limit_sec"],
            "memory_limit": int(job["memory_limit_mb"]) * 1024,  # Judge0 expects KB
            "enable_network": False,
        }
        try:
            res = self._client.post(
                f"{self._base}/submissions",
                params={"base64_encoded": "false", "wait": "true"},
                json=payload,
            )
            res.raise_for_status()
            status_id = int(res.json()["status"]["id"])
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise SandboxError(f"judge0 request failed: {exc}") from exc

        if status_id == 13:  # Judge0 internal error
            raise SandboxError("judge0 internal error")
        verdict = _VERDICTS.get(status_id, "runtime_error")
        return {"passed": status_id == 3, "verdict": verdict}
