import httpx
import pytest

from app.main import create_app
from app.routers.health import get_db_checker, get_redis_checker


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["deployment_profile"] in {"standalone", "central"}


@pytest.mark.asyncio
async def test_ready_endpoint_healthy() -> None:
    app = create_app()

    async def ok() -> bool:
        return True

    app.dependency_overrides[get_db_checker] = lambda: ok
    app.dependency_overrides[get_redis_checker] = lambda: ok

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/ready")

    assert res.status_code == 200
    assert res.json()["status"] == "ready"
    assert res.json()["dependencies"] == {"postgres": "ok", "redis": "ok"}


@pytest.mark.asyncio
async def test_ready_endpoint_degraded_returns_503() -> None:
    app = create_app()

    async def ok() -> bool:
        return True

    async def fail() -> bool:
        return False

    app.dependency_overrides[get_db_checker] = lambda: ok
    app.dependency_overrides[get_redis_checker] = lambda: fail

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/ready")

    assert res.status_code == 503
    assert res.json()["status"] == "degraded"
    assert res.json()["dependencies"] == {"postgres": "ok", "redis": "unreachable"}
