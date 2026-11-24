"""Interactive code execution runner for candidate sample/custom-input runs (FR-CODE-01..04)."""

from typing import Annotated, Any, Protocol

import httpx
from fastapi import Depends

from app.core.config import Settings, get_settings

JUDGE0_LANGUAGE_IDS: dict[str, int] = {
    "python3": 71,
    "c": 50,
    "cpp": 54,
    "java": 62,
    "javascript": 63,
}

_VERDICTS: dict[int, str] = {
    3: "accepted",
    4: "wrong_answer",
    5: "timed_out",
    6: "compile_error",
}


class SandboxUnavailableError(Exception):
    """Raised when Judge0 cannot be reached or returns an internal sandbox error."""


class CodeRunner(Protocol):
    async def run_case(
        self,
        *,
        language: str,
        source_code: str,
        stdin: str,
        expected_stdout: str | None,
        cpu_time_limit_sec: float,
        memory_limit_mb: int,
    ) -> dict[str, Any]:
        """Execute a single test case synchronously against an isolated sandbox."""
        ...


class Judge0CodeRunner:
    """Runs interactive candidate test runs on Judge0 with network disabled."""

    def __init__(self, base_url: str, timeout: float = 25.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    async def run_case(
        self,
        *,
        language: str,
        source_code: str,
        stdin: str,
        expected_stdout: str | None,
        cpu_time_limit_sec: float,
        memory_limit_mb: int,
    ) -> dict[str, Any]:
        language_id = JUDGE0_LANGUAGE_IDS.get(language)
        if language_id is None:
            raise SandboxUnavailableError(f"Unsupported language {language!r}")

        payload: dict[str, Any] = {
            "source_code": source_code,
            "language_id": language_id,
            "stdin": stdin,
            "cpu_time_limit": cpu_time_limit_sec,
            "memory_limit": int(memory_limit_mb) * 1024,
            "enable_network": False,
        }
        if expected_stdout is not None:
            payload["expected_output"] = expected_stdout

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.post(
                    f"{self._base}/submissions",
                    params={"base64_encoded": "false", "wait": "true"},
                    json=payload,
                )
                res.raise_for_status()
                body = res.json()
                status_id = int(body["status"]["id"])
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
            raise SandboxUnavailableError(f"Judge0 request failed: {exc}") from exc

        if status_id == 13:
            raise SandboxUnavailableError("Judge0 internal error")

        verdict = _VERDICTS.get(status_id, "runtime_error")
        passed: bool | None = (status_id == 3) if expected_stdout is not None else None
        raw_time = body.get("time")
        try:
            time_sec = float(raw_time) if raw_time is not None else None
        except (TypeError, ValueError):
            time_sec = None

        return {
            "stdin": stdin,
            "expected_stdout": expected_stdout,
            "stdout": body.get("stdout") or "",
            "stderr": body.get("stderr") or "",
            "compile_output": body.get("compile_output") or "",
            "verdict": verdict,
            "passed": passed,
            "time_sec": time_sec,
        }


def get_code_runner(settings: Annotated[Settings, Depends(get_settings)]) -> CodeRunner:
    return Judge0CodeRunner(settings.judge0_url)
