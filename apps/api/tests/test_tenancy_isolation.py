from helpers import MCQ_Q, activate, create_assessment, live_assessment, start_attempt
from sqlalchemy import select

from app.db.models import AuditEvent
from app.services import audit


async def _denials(ctx):
    async with ctx.factory() as db:
        rows = (
            await db.scalars(select(AuditEvent).where(AuditEvent.action == "authz.denied"))
        ).all()
    return [(r.reason_code, r.resource_type) for r in rows]


async def test_other_tenants_organizer_cannot_use_tenant_path(client, ctx, world):
    """Tenant scope derives from membership: tenant B staff are denied on tenant A's path."""
    aid, _ = await create_assessment(client, world.a, [MCQ_Q])
    base = f"/api/tenants/{world.a.id}/assessments"

    for method, url in (
        ("get", base),
        ("get", f"{base}/{aid}"),
        ("post", f"{base}/{aid}/publish"),
        ("get", f"{base}/{aid}/results"),
        ("get", f"{base}/{aid}/capsule"),
    ):
        res = await getattr(client, method)(url, headers=world.b.org)
        assert res.status_code == 403, (method, url, res.text)

    assert ("NOT_MEMBER", "tenant") in await _denials(ctx)


async def test_cross_tenant_object_id_is_not_found(client, world):
    """Tenant A's assessment id used under tenant B's own path must not resolve."""
    aid, _ = await create_assessment(client, world.a, [MCQ_Q])
    base = f"/api/tenants/{world.b.id}/assessments/{aid}"
    assert (await client.get(base, headers=world.b.org)).status_code == 404
    assert (await client.post(f"{base}/publish", headers=world.b.org)).status_code == 404
    assert (
        await client.patch(base, json={"title": "pwned"}, headers=world.b.org)
    ).status_code == 404


async def test_candidate_cannot_use_organizer_endpoints(client, ctx, world):
    base = f"/api/tenants/{world.a.id}/assessments"
    res = await client.post(base, json={"title": "x"}, headers=world.a.cand)
    assert res.status_code == 403
    assert ("ROLE_FORBIDDEN", "tenant") in await _denials(ctx)


async def test_tenant_management_requires_platform_or_tenant_admin(client, world):
    assert (await client.get("/api/tenants", headers=world.a.admin)).status_code == 403
    assert (await client.get("/api/tenants", headers=world.platform)).status_code == 200

    path = f"/api/tenants/{world.a.id}/memberships"
    assert (await client.get(path, headers=world.a.org)).status_code == 403
    assert (await client.get(path, headers=world.a.admin)).status_code == 200
    assert (await client.get(path, headers=world.platform)).status_code == 200
    assert (await client.get(path, headers=world.b.admin)).status_code == 403


async def test_candidate_cannot_read_other_candidates_attempt(client, ctx, world):
    _aid, _, attempt = await live_assessment(client, world, [MCQ_Q])
    url = f"/api/attempts/{attempt['id']}"
    assert (await client.get(url, headers=world.a.cand)).status_code == 200
    assert (await client.get(url, headers=world.a.org)).status_code == 200  # organizer read-only
    for other in (world.a.cand2, world.b.cand, world.b.org):
        assert (await client.get(url, headers=other)).status_code == 404
    # Writes are owner-only, even for organizers of the same tenant.
    put = await client.put(
        f"{url}/responses/{attempt['questions'][0]['id']}",
        json={"payload": {"selected": "a"}, "client_seq": 1},
        headers=world.a.org,
    )
    assert put.status_code == 404
    reasons = [r for r, kind in await _denials(ctx) if kind == "attempt"]
    assert "NOT_OWNER" in reasons and "NOT_MEMBER" in reasons


async def test_unenrolled_candidate_cannot_start_attempt(client, ctx, world):
    aid, _ = await create_assessment(client, world.a, [MCQ_Q])
    await activate(client, world.a, aid, [world.a.cand_email])
    res = await start_attempt(client, world.a, aid, world.a.cand2)
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "NOT_ENROLLED"
    # Another tenant's candidate cannot target tenant A's path at all.
    assert (await start_attempt(client, world.a, aid, world.b.cand)).status_code == 403


async def test_enrollment_rejects_non_candidates_and_foreign_users(client, world):
    aid, _ = await create_assessment(client, world.a, [MCQ_Q])
    url = f"/api/tenants/{world.a.id}/assessments/{aid}/enrollments"
    for email in (world.b.cand_email, "org-alpha@example.com"):
        res = await client.post(url, json={"emails": [email]}, headers=world.a.org)
        assert res.status_code == 422, res.text


async def test_my_assessments_only_lists_enrolled_active(client, world):
    aid, _ = await create_assessment(client, world.a, [MCQ_Q])
    await activate(client, world.a, aid, [world.a.cand_email])
    mine = await client.get("/api/me/assessments", headers=world.a.cand)
    assert [a["assessment_id"] for a in mine.json()] == [aid]
    assert (await client.get("/api/me/assessments", headers=world.a.cand2)).json() == []
    assert (await client.get("/api/me/assessments", headers=world.b.cand)).json() == []


async def test_audit_chain_verifies_and_detects_tampering(client, ctx, world):
    await create_assessment(client, world.a, [MCQ_Q])
    async with ctx.factory() as db:
        ok, bad = await audit.verify_chain(db)
        assert ok and bad is None

        events = (await db.scalars(select(AuditEvent).order_by(AuditEvent.sequence_num))).all()
        assert len(events) > 5
        assert events[0].prev_hash == audit.GENESIS_HASH
        victim = events[len(events) // 2]
        victim.reason_code = "TAMPERED"
        await db.commit()

    async with ctx.factory() as db:
        ok, bad = await audit.verify_chain(db)
        assert ok is False
        assert bad == victim.sequence_num
