from datetime import timedelta

from app.core.timeutil import utcnow
from app.db.models import WorkerNode
from app.routers.admin import get_judge0_checker, get_queue_stats_getter
from app.routers.health import get_db_checker, get_redis_checker

SECRET = {"X-Worker-Token": "test-worker-secret-0123456789"}


async def test_worker_heartbeat_auth_and_upsert(client, world):
    payload = {
        "worker_id": "worker-lab-1",
        "hostname": "lab-node-01",
        "deployment_mode": "central",
        "judge0_ok": True,
        "active_jobs": 1,
        "jobs_completed": 4,
        "jobs_failed": 0,
    }

    assert (await client.post("/api/internal/workers/heartbeat", json=payload)).status_code == 401
    assert (
        await client.post(
            "/api/internal/workers/heartbeat", json=payload, headers={"X-Worker-Token": "wrong"}
        )
    ).status_code == 401

    ok = await client.post("/api/internal/workers/heartbeat", json=payload, headers=SECRET)
    assert ok.status_code == 200
    assert ok.json()["worker_id"] == "worker-lab-1"
    assert ok.json()["status"] == "online"

    # Subsequent heartbeat with judge0 down transitions status to degraded.
    degraded = await client.post(
        "/api/internal/workers/heartbeat",
        json={**payload, "judge0_ok": False, "jobs_failed": 1},
        headers=SECRET,
    )
    assert degraded.status_code == 200
    assert degraded.json()["status"] == "degraded"


async def test_admin_infrastructure_rbac_and_stale_worker_detection(client, ctx, world):
    async def ok_bool(*_args) -> bool:
        return True

    async def fake_queue_stats(_url: str) -> tuple[int, int]:
        return 3, 1

    ctx.app.dependency_overrides[get_db_checker] = lambda: ok_bool
    ctx.app.dependency_overrides[get_redis_checker] = lambda: ok_bool
    ctx.app.dependency_overrides[get_judge0_checker] = lambda: ok_bool
    ctx.app.dependency_overrides[get_queue_stats_getter] = lambda: fake_queue_stats

    # Non-platform-admins cannot inspect infrastructure telemetry.
    assert (await client.get("/api/admin/infrastructure")).status_code == 401
    assert (await client.get("/api/admin/infrastructure", headers=world.a.org)).status_code == 403
    assert (await client.get("/api/admin/infrastructure", headers=world.a.cand)).status_code == 403

    # Register one fresh worker and one stale worker (>45s old).
    await client.post(
        "/api/internal/workers/heartbeat",
        json={
            "worker_id": "fresh-worker",
            "hostname": "host-a",
            "deployment_mode": "standalone",
            "judge0_ok": True,
            "jobs_completed": 2,
        },
        headers=SECRET,
    )
    async with ctx.factory() as db:
        db.add(
            WorkerNode(
                worker_id="stale-worker",
                hostname="host-b",
                deployment_mode="central",
                status="online",
                judge0_ok=True,
                active_jobs=0,
                jobs_completed=5,
                jobs_failed=1,
                metadata_json={},
                registered_at=utcnow() - timedelta(minutes=10),
                last_heartbeat_at=utcnow() - timedelta(seconds=120),
            )
        )
        await db.commit()

    res = await client.get("/api/admin/infrastructure", headers=world.platform)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["dependencies"] == {"postgres": "ok", "redis": "ok", "judge0": "ok"}
    assert body["queue_depth"] == 3
    assert body["dead_letter_depth"] == 1
    by_id = {w["worker_id"]: w for w in body["workers"]}
    assert by_id["fresh-worker"]["status"] == "online" and by_id["fresh-worker"]["stale"] is False
    assert by_id["stale-worker"]["status"] == "offline" and by_id["stale-worker"]["stale"] is True
