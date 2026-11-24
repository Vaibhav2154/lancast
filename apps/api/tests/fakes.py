from app.contracts.interfaces import ExecutionQueueContract
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
