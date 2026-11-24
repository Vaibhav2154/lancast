"""Bounded execution queue backed by Redis (FR-RES-07, TD-04).

The queue key holds fully-formed job messages; workers hold no database credentials and report
results back through an authenticated internal API (T19).
"""

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.contracts.interfaces import ExecutionJobContract, ExecutionQueueContract
from app.core.config import Settings, get_settings

QUEUE_KEY = "lancast:execution:queue"

# Atomic bounded push: refuse (-1) when the queue is at capacity.
_BOUNDED_PUSH = """
if redis.call('LLEN', KEYS[1]) >= tonumber(ARGV[1]) then
  return -1
end
return redis.call('RPUSH', KEYS[1], ARGV[2])
"""


class QueueFullError(Exception):
    """Raised when the bounded queue cannot accept more jobs."""


class RedisExecutionQueue:
    def __init__(self, client: Redis, max_depth: int) -> None:
        self._client = client
        self._max_depth = max_depth

    async def enqueue(self, job: ExecutionJobContract) -> int:
        result = await self._client.eval(
            _BOUNDED_PUSH, 1, QUEUE_KEY, self._max_depth, job.model_dump_json()
        )
        if int(result) == -1:
            raise QueueFullError
        return int(result)

    async def depth(self) -> int:
        return int(await self._client.llen(QUEUE_KEY))

    async def has_capacity(self, count: int) -> bool:
        return await self.depth() + count <= self._max_depth

    async def health_check(self) -> bool:
        return bool(await self._client.ping())


_client: Redis | None = None


def get_execution_queue(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ExecutionQueueContract:
    global _client
    if _client is None:
        _client = Redis.from_url(settings.redis_url)
    return RedisExecutionQueue(_client, settings.execution_queue_max_depth)
