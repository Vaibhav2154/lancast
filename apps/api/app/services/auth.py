from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.deps import Principal
from app.core.errors import api_error
from app.core.security import (
    dummy_verify,
    email_fingerprint,
    hash_password,
    issue_token,
    verify_password,
)
from app.core.timeutil import utcnow
from app.db.models import Membership, User, UserSession
from app.services import audit


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def count_users(db: AsyncSession) -> int:
    return int(await db.scalar(select(func.count()).select_from(User)) or 0)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == normalize_email(email)))


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    full_name: str,
    password: str,
    is_platform_admin: bool = False,
) -> User:
    if await get_user_by_email(db, email) is not None:
        raise api_error(409, "EMAIL_TAKEN", "A user with this email already exists")
    user = User(
        id=uuid4(),
        email=normalize_email(email),
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        is_platform_admin=is_platform_admin,
    )
    db.add(user)
    await db.flush()
    return user


async def login(
    db: AsyncSession, settings: Settings, email: str, password: str
) -> tuple[str, UserSession, User]:
    user = await get_user_by_email(db, email)
    valid = False
    if user is not None and user.is_active:
        valid = verify_password(password, user.password_hash)
    else:
        dummy_verify(password)

    if not valid:
        await audit.record(
            db,
            action="auth.login_failed",
            resource_type="user",
            resource_id=email_fingerprint(email),
            actor_id=user.id if user else None,
            reason_code="BAD_CREDENTIALS",
        )
        await db.commit()
        raise api_error(401, "BAD_CREDENTIALS", "Invalid email or password")

    assert user is not None
    now = utcnow()
    session = UserSession(
        id=uuid4(),
        user_id=user.id,
        created_at=now,
        expires_at=now + timedelta(minutes=settings.session_ttl_minutes),
    )
    db.add(session)
    await db.flush()
    token = issue_token(user.id, session.id, session.expires_at, settings)
    await audit.record(
        db,
        action="auth.login",
        resource_type="session",
        resource_id=str(session.id),
        actor_id=user.id,
    )
    return token, session, user


async def logout(db: AsyncSession, principal: Principal) -> None:
    principal.session.revoked_at = utcnow()
    await audit.record(
        db,
        action="auth.logout",
        resource_type="session",
        resource_id=str(principal.session.id),
        actor_id=principal.user.id,
    )


async def list_memberships(db: AsyncSession, user_id: UUID):
    return (await db.scalars(select(Membership).where(Membership.user_id == user_id))).all()
