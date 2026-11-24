from datetime import timedelta
from uuid import uuid4

from helpers import PASSWORD, bearer, login
from sqlalchemy import select

from app.core.security import issue_token
from app.core.timeutil import utcnow
from app.db.models import AuditEvent, User, UserSession


async def test_first_registration_bootstraps_platform_admin(client):
    res = await client.post(
        "/api/auth/register",
        json={"email": "Root@Example.com", "full_name": "Root", "password": PASSWORD},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["is_platform_admin"] is True
    assert body["email"] == "root@example.com"
    assert "password" not in body and "password_hash" not in body


async def test_registration_closed_after_bootstrap(client, world):
    payload = {"email": "new@example.com", "full_name": "N", "password": PASSWORD}
    assert (await client.post("/api/auth/register", json=payload)).status_code == 401
    res = await client.post("/api/auth/register", json=payload, headers=world.a.cand)
    assert res.status_code == 403
    res = await client.post("/api/auth/register", json=payload, headers=world.platform)
    assert res.status_code == 201
    assert res.json()["is_platform_admin"] is False


async def test_weak_password_rejected(client):
    res = await client.post(
        "/api/auth/register",
        json={"email": "a@example.com", "full_name": "A", "password": "short"},
    )
    assert res.status_code == 422


async def test_login_me_and_bad_credentials(client, world):
    me = await client.get("/api/auth/me", headers=world.a.org)
    assert me.status_code == 200
    assert me.json()["memberships"][0]["role"] == "organizer"

    bad = await client.post(
        "/api/auth/login", json={"email": world.a.cand_email, "password": "wrong-password-1"}
    )
    assert bad.status_code == 401
    unknown = await client.post(
        "/api/auth/login", json={"email": "ghost@example.com", "password": PASSWORD}
    )
    assert unknown.status_code == 401
    # Same response shape for unknown user vs wrong password (no enumeration).
    assert bad.json() == unknown.json()


async def test_logout_revokes_token(client, world):
    headers = await login(client, world.a.cand_email)
    assert (await client.get("/api/auth/me", headers=headers)).status_code == 200
    assert (await client.post("/api/auth/logout", headers=headers)).status_code == 204
    assert (await client.get("/api/auth/me", headers=headers)).status_code == 401


async def test_missing_malformed_and_expired_tokens_rejected(client, ctx, world):
    assert (await client.get("/api/auth/me")).status_code == 401
    assert (await client.get("/api/auth/me", headers=bearer("garbage"))).status_code == 401

    async with ctx.factory() as db:
        user = await db.scalar(select(User).where(User.email == world.a.cand_email))
        expired_at = utcnow() - timedelta(minutes=1)
        session = UserSession(
            id=uuid4(), user_id=user.id, created_at=expired_at, expires_at=expired_at
        )
        db.add(session)
        await db.commit()
        token = issue_token(user.id, session.id, expired_at, ctx.settings)
    assert (await client.get("/api/auth/me", headers=bearer(token))).status_code == 401


async def test_token_with_unknown_session_rejected(client, ctx, world):
    async with ctx.factory() as db:
        user = await db.scalar(select(User).where(User.email == world.a.cand_email))
        token = issue_token(user.id, uuid4(), utcnow() + timedelta(hours=1), ctx.settings)
    assert (await client.get("/api/auth/me", headers=bearer(token))).status_code == 401


async def test_login_and_failures_are_audited(client, ctx, world):
    await client.post(
        "/api/auth/login", json={"email": world.a.cand_email, "password": "wrong-password-1"}
    )
    async with ctx.factory() as db:
        actions = set((await db.scalars(select(AuditEvent.action))).all())
    assert {"auth.login", "auth.login_failed", "tenant.create", "membership.add"} <= actions
