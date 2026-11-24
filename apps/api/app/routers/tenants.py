from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import DbSession, PlatformAdmin, TenantManager
from app.db.models import Tenant
from app.schemas.auth_tenants import MemberCreate, MemberOut, TenantCreate, TenantOut
from app.services import tenancy

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


@router.post("", response_model=TenantOut, status_code=201)
async def create_tenant(body: TenantCreate, admin: PlatformAdmin, db: DbSession) -> Tenant:
    tenant = await tenancy.create_tenant(db, admin.user, body.slug, body.name)
    await db.commit()
    return tenant


@router.get("", response_model=list[TenantOut])
async def list_tenants(admin: PlatformAdmin, db: DbSession) -> list[Tenant]:
    return list((await db.scalars(select(Tenant).order_by(Tenant.slug))).all())


@router.post("/{tenant_id}/memberships", response_model=MemberOut, status_code=201)
async def add_membership(
    tenant_id: UUID, body: MemberCreate, ctx: TenantManager, db: DbSession
) -> MemberOut:
    user, membership = await tenancy.add_member(
        db,
        ctx.user,
        tenant_id,
        email=body.email,
        role=body.role,
        full_name=body.full_name,
        password=body.password,
    )
    await db.commit()
    return MemberOut(
        user_id=user.id, email=user.email, full_name=user.full_name, role=membership.role
    )


@router.get("/{tenant_id}/memberships", response_model=list[MemberOut])
async def list_memberships(tenant_id: UUID, ctx: TenantManager, db: DbSession) -> list[MemberOut]:
    rows = await tenancy.list_members(db, tenant_id)
    return [
        MemberOut(user_id=u.id, email=u.email, full_name=u.full_name, role=m.role) for u, m in rows
    ]
