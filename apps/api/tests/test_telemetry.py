from datetime import timedelta

from sqlalchemy import func, select

from app.core.timeutil import utcnow
from app.db.models import TelemetrySampleRecord

SECRET = {"X-Worker-Token": "test-worker-secret-0123456789"}


def _sample(machine_id: str = "dispatcher-1", **overrides):
    base = {
        "machine_id": machine_id,
        "role": "standalone",
        "cpu_percent": 22.5,
        "memory_percent": 41.0,
        "disk_percent": 55.0,
        "network_rx_kbps": 120.4,
        "network_tx_kbps": 85.2,
        "queue_depth": 2,
        "active_jobs": 1,
        "healthy": True,
    }
    base.update(overrides)
    return base


async def test_telemetry_ingestion_auth_validation_and_retention(client, ctx, world):
    # Unauthenticated and bad token rejected (T12).
    assert (await client.post("/api/internal/telemetry/samples", json=_sample())).status_code == 401
    assert (
        await client.post(
            "/api/internal/telemetry/samples",
            json=_sample(),
            headers={"X-Worker-Token": "invalid"},
        )
    ).status_code == 401

    # Out-of-range values rejected.
    bad_cpu = await client.post(
        "/api/internal/telemetry/samples", json=_sample(cpu_percent=150.0), headers=SECRET
    )
    assert bad_cpu.status_code == 422

    # Spoofed future timestamp rejected (T12 clock skew guard).
    future = (utcnow() + timedelta(minutes=5)).isoformat()
    skew = await client.post(
        "/api/internal/telemetry/samples", json=_sample(collected_at=future), headers=SECRET
    )
    assert skew.status_code == 422 and skew.json()["detail"]["code"] == "CLOCK_SKEW"

    # Seed an expired row (> retention window) and verify ingestion prunes it (T20).
    async with ctx.factory() as db:
        db.add(
            TelemetrySampleRecord(
                machine_id="old-node",
                role="worker",
                collected_at=utcnow() - timedelta(hours=30),
                cpu_percent=10.0,
                memory_percent=20.0,
                disk_percent=30.0,
                network_rx_kbps=0.0,
                network_tx_kbps=0.0,
                queue_depth=0,
                active_jobs=0,
                healthy=True,
                metadata_json={},
            )
        )
        await db.commit()

    ok = await client.post("/api/internal/telemetry/samples", json=_sample(), headers=SECRET)
    assert ok.status_code == 200
    assert ok.json()["machine_id"] == "dispatcher-1"

    async with ctx.factory() as db:
        total = await db.scalar(select(func.count()).select_from(TelemetrySampleRecord))
        assert total == 1


async def test_admin_telemetry_rbac_and_stale_missing_states(client, ctx, world):
    # RBAC: platform admin only.
    assert (await client.get("/api/admin/telemetry")).status_code == 401
    assert (await client.get("/api/admin/telemetry", headers=world.a.org)).status_code == 403
    assert (await client.get("/api/admin/telemetry", headers=world.a.cand)).status_code == 403

    # Empty telemetry triggers missing + safe_fallback_active (FR-RES-10).
    empty = await client.get("/api/admin/telemetry", headers=world.platform)
    assert empty.status_code == 200
    assert empty.json()["telemetry_state"] == "missing"
    assert empty.json()["safe_fallback_active"] is True
    assert empty.json()["machines"] == []

    # Fresh healthy sample transitions state to healthy.
    await client.post("/api/internal/telemetry/samples", json=_sample("node-a"), headers=SECRET)
    healthy = (await client.get("/api/admin/telemetry", headers=world.platform)).json()
    assert healthy["telemetry_state"] == "healthy"
    assert healthy["safe_fallback_active"] is False
    assert len(healthy["machines"]) == 1
    assert healthy["machines"][0]["stale"] is False
    assert "organizer_admin" in healthy["workload_latencies"]

    # Adding a stale second machine transitions state to degraded + safe_fallback_active.
    async with ctx.factory() as db:
        db.add(
            TelemetrySampleRecord(
                machine_id="node-b",
                role="worker",
                collected_at=utcnow() - timedelta(seconds=120),
                cpu_percent=50.0,
                memory_percent=60.0,
                disk_percent=40.0,
                network_rx_kbps=0.0,
                network_tx_kbps=0.0,
                queue_depth=0,
                active_jobs=0,
                healthy=True,
                metadata_json={},
            )
        )
        await db.commit()

    degraded = (await client.get("/api/admin/telemetry", headers=world.platform)).json()
    assert degraded["telemetry_state"] == "degraded"
    assert degraded["safe_fallback_active"] is True
    by_machine = {m["machine_id"]: m for m in degraded["machines"]}
    assert by_machine["node-a"]["stale"] is False
    assert by_machine["node-b"]["stale"] is True
