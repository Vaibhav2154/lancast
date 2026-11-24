import os
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-0123456789abcdef")

from fakes import FakeQueue
from helpers import World, build_world
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core import security
from app.core.config import Settings, get_settings
from app.db.models import Base
from app.db.session import get_db_session
from app.main import create_app
from app.services.execution_queue import get_execution_queue

# Production uses pwdlib's recommended Argon2 parameters; tests use cheap ones for speed only.
security._hasher = PasswordHash((Argon2Hasher(time_cost=1, memory_cost=1024, parallelism=1),))
security._dummy_hash = None


@pytest_asyncio.fixture
async def engine():
    """SQLite in-memory by default; set TEST_DATABASE_URL to run against real PostgreSQL."""
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        eng = create_async_engine(url)
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    else:
        eng = create_async_engine(
            "sqlite+aiosqlite://",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    if url:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
def ctx(engine, tmp_path):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    app = create_app()
    queue = FakeQueue(max_depth=5)
    settings = Settings(
        environment="test",
        upload_dir=str(tmp_path / "uploads"),
        auth_secret_key="test-secret-key-0123456789abcdef",
        worker_shared_secret="test-worker-secret-0123456789",
    )

    async def override_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_execution_queue] = lambda: queue
    return SimpleNamespace(app=app, factory=factory, queue=queue, settings=settings)


@pytest_asyncio.fixture
async def client(ctx):
    transport = httpx.ASGITransport(app=ctx.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def world(client) -> World:
    return await build_world(client)
