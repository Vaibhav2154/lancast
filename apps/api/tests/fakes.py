from app.contracts.interfaces import ExecutionQueueContract
from app.services.code_runner import SandboxUnavailableError
from app.services.execution_queue import QueueFullError


class FakeQueue(ExecutionQueueContract):
    """In-memory bounded queue with the same semantics as the Redis implementation."""

    def __init__(self, max_depth: int = 5) -> None:
        self.max_depth = max_depth
        self.jobs: list = []

    async def enqueue(self, job) -> int:
        if len(self.jobs) >= self.max_depth:
            raise QueueFullError
        self.jobs.append(job)
        return len(self.jobs)

    async def depth(self) -> int:
        return len(self.jobs)

    async def has_capacity(self, count: int) -> bool:
        return len(self.jobs) + count <= self.max_depth

    async def health_check(self) -> bool:
        return True


class FakeCodeRunner:
    """In-memory sandbox runner for testing interactive /run requests."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.fail_with_unavailable = False

    async def run_case(
        self,
        *,
        language: str,
        source_code: str,
        stdin: str,
        expected_stdout: str | None,
        cpu_time_limit_sec: float,
        memory_limit_mb: int,
    ) -> dict:
        self.calls.append(
            {
                "language": language,
                "source_code": source_code,
                "stdin": stdin,
                "expected_stdout": expected_stdout,
                "cpu_time_limit_sec": cpu_time_limit_sec,
                "memory_limit_mb": memory_limit_mb,
            }
        )
        if self.fail_with_unavailable:
            raise SandboxUnavailableError("sandbox offline")
        stdout = stdin
        passed = (stdout == expected_stdout) if expected_stdout is not None else None
        verdict = "accepted" if passed in (True, None) else "wrong_answer"
        return {
            "stdin": stdin,
            "expected_stdout": expected_stdout,
            "stdout": stdout,
            "stderr": "",
            "compile_output": "",
            "verdict": verdict,
            "passed": passed,
            "time_sec": 0.01,
        }
