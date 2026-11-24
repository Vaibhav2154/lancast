from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings, get_settings
from app.db.session import get_engine

router = APIRouter(prefix="/api", tags=["health"])


async def check_postgres() -> bool:
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def check_redis() -> bool:
    settings = get_settings()
    client: Redis | None = None
    try:
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=1.5, socket_timeout=1.5)
        return bool(await client.ping())
    except (RedisError, OSError):
        return False
    finally:
        if client is not None:
            await client.aclose()


def get_db_checker() -> Callable[[], Awaitable[bool]]:
    return check_postgres


def get_redis_checker() -> Callable[[], Awaitable[bool]]:
    return check_redis


@router.get("/health")
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
    """Liveness check: confirms the FastAPI process is responsive."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "deployment_profile": settings.deployment_profile,
        "environment": settings.environment,
    }


@router.get("/ready")
async def readiness(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    db_check: Annotated[Callable[[], Awaitable[bool]], Depends(get_db_checker)],
    redis_check: Annotated[Callable[[], Awaitable[bool]], Depends(get_redis_checker)],
) -> dict[str, Any]:
    """Readiness check: verifies PostgreSQL and Redis connectivity."""
    postgres_ok = await db_check()
    redis_ok = await redis_check()
    ready = postgres_ok and redis_ok

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready else "degraded",
        "deployment_profile": settings.deployment_profile,
        "dependencies": {
            "postgres": "ok" if postgres_ok else "unreachable",
            "redis": "ok" if redis_ok else "unreachable",
        },
    }
