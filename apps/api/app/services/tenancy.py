from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import api_error
from app.db.models import Membership, Tenant, User
from app.services import audit
from app.services.auth import create_user, get_user_by_email


async def create_tenant(db: AsyncSession, actor: User, slug: str, name: str) -> Tenant:
    if await db.scalar(select(Tenant).where(Tenant.slug == slug)) is not None:
        raise api_error(409, "SLUG_TAKEN", "A tenant with this slug already exists")
    tenant = Tenant(id=uuid4(), slug=slug, name=name.strip())
    db.add(tenant)
    await db.flush()
    await audit.record(
        db,
        action="tenant.create",
        resource_type="tenant",
        resource_id=str(tenant.id),
        actor_id=actor.id,
        tenant_id=tenant.id,
    )
    return tenant


async def add_member(
    db: AsyncSession,
    actor: User,
    tenant_id: UUID,
    *,
    email: str,
    role: str,
    full_name: str | None,
    password: str | None,
) -> tuple[User, Membership]:
    user = await get_user_by_email(db, email)
    if user is None:
        if not full_name or not password:
            raise api_error(
                422,
                "USER_DETAILS_REQUIRED",
                "full_name and password are required to create a new user",
            )
        user = await create_user(db, email=email, full_name=full_name, password=password)
    existing = await db.scalar(
        select(Membership).where(Membership.tenant_id == tenant_id, Membership.user_id == user.id)
    )
    if existing is not None:
        raise api_error(409, "ALREADY_MEMBER", "User is already a member of this tenant")
    membership = Membership(id=uuid4(), tenant_id=tenant_id, user_id=user.id, role=role)
    db.add(membership)
    await db.flush()
    await audit.record(
        db,
        action="membership.add",
        resource_type="membership",
        resource_id=str(membership.id),
        actor_id=actor.id,
        tenant_id=tenant_id,
        metadata={"user_id": str(user.id), "role": role},
    )
    return user, membership


async def list_members(db: AsyncSession, tenant_id: UUID) -> list[tuple[User, Membership]]:
    rows = await db.execute(
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.tenant_id == tenant_id)
        .order_by(User.email)
    )
    return [(u, m) for u, m in rows.all()]
