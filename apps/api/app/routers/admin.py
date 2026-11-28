from collections.abc import Awaitable, Callable
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select

from app.core.deps import AppSettings, DbSession, PlatformAdmin
from app.core.timeutil import as_utc, utcnow
from app.db.models import WorkerNode
from app.routers.health import get_db_checker, get_redis_checker
from app.schemas.infrastructure import (
    InfrastructureStatusOut,
    TelemetryOverviewOut,
    WorkerNodeOut,
)
from app.services import telemetry as telemetry_svc
from app.services.execution_queue import QUEUE_KEY

DEAD_LETTER_KEY = "lancast:execution:dead"
WORKER_STALE_SECONDS = 45

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def check_judge0(judge0_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            res = await client.get(f"{judge0_url.rstrip('/')}/about")
            return res.status_code == 200
    except (httpx.HTTPError, OSError):
        return False


async def read_queue_stats(redis_url: str) -> tuple[int | None, int | None]:
    client: Redis | None = None
    try:
        client = Redis.from_url(redis_url, socket_connect_timeout=1.5, socket_timeout=1.5)
        q_depth = int(await client.llen(QUEUE_KEY))
        dl_depth = int(await client.llen(DEAD_LETTER_KEY))
        return q_depth, dl_depth
    except (RedisError, OSError):
        return None, None
    finally:
        if client is not None:
            await client.aclose()


def get_judge0_checker() -> Callable[[str], Awaitable[bool]]:
    return check_judge0


def get_queue_stats_getter() -> Callable[[str], Awaitable[tuple[int | None, int | None]]]:
    return read_queue_stats


@router.get("/infrastructure", response_model=InfrastructureStatusOut)
async def infrastructure_status(
    _admin: PlatformAdmin,
    db: DbSession,
    settings: AppSettings,
    db_check: Annotated[Callable[[], Awaitable[bool]], Depends(get_db_checker)],
    redis_check: Annotated[Callable[[], Awaitable[bool]], Depends(get_redis_checker)],
    judge0_check: Annotated[Callable[[str], Awaitable[bool]], Depends(get_judge0_checker)],
    queue_stats_fn: Annotated[
        Callable[[str], Awaitable[tuple[int | None, int | None]]],
        Depends(get_queue_stats_getter),
    ],
) -> InfrastructureStatusOut:
    """Return deployment profile, dependency health, queue depths, and registered workers."""
    postgres_ok = await db_check()
    redis_ok = await redis_check()
    judge0_ok = await judge0_check(settings.judge0_url)
    queue_depth, dead_letter_depth = await queue_stats_fn(settings.redis_url)

    now = utcnow()
    nodes = (await db.scalars(select(WorkerNode).order_by(WorkerNode.worker_id))).all()
    worker_rows: list[WorkerNodeOut] = []
    for node in nodes:
        age_sec = (now - as_utc(node.last_heartbeat_at)).total_seconds()
        stale = age_sec > WORKER_STALE_SECONDS
        effective_status = "offline" if stale else node.status
        worker_rows.append(
            WorkerNodeOut(
                worker_id=node.worker_id,
                hostname=node.hostname,
                deployment_mode=node.deployment_mode,
                status=effective_status,
                judge0_ok=node.judge0_ok,
                active_jobs=node.active_jobs,
                jobs_completed=node.jobs_completed,
                jobs_failed=node.jobs_failed,
                registered_at=node.registered_at,
                last_heartbeat_at=node.last_heartbeat_at,
                stale=stale,
            )
        )

    return InfrastructureStatusOut(
        deployment_profile=settings.deployment_profile,
        environment=settings.environment,
        app_version=settings.app_version,
        public_base_url=settings.public_base_url,
        dependencies={
            "postgres": "ok" if postgres_ok else "unreachable",
            "redis": "ok" if redis_ok else "unreachable",
            "judge0": "ok" if judge0_ok else "unreachable",
        },
        queue_depth=queue_depth,
        dead_letter_depth=dead_letter_depth,
        worker_stale_seconds=WORKER_STALE_SECONDS,
        workers=worker_rows,
    )


@router.get("/telemetry", response_model=TelemetryOverviewOut)
async def telemetry_overview(
    _admin: PlatformAdmin,
    db: DbSession,
    settings: AppSettings,
) -> TelemetryOverviewOut:
    """Return normalized host/worker telemetry snapshots, stale state, and rolling latencies."""
    return await telemetry_svc.get_normalized_snapshot(db, settings)
