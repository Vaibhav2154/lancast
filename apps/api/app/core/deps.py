from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import api_error
from app.core.security import decode_token
from app.core.timeutil import as_utc, utcnow
from app.db.models import Membership, Tenant, User, UserSession
from app.db.session import get_db_session
from app.services import audit

ROLE_TENANT_ADMIN = "tenant_admin"
ROLE_ORGANIZER = "organizer"
ROLE_CANDIDATE = "candidate"
TENANT_ROLES = (ROLE_TENANT_ADMIN, ROLE_ORGANIZER, ROLE_CANDIDATE)
ORGANIZER_ROLES = (ROLE_TENANT_ADMIN, ROLE_ORGANIZER)

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]
_bearer = HTTPBearer(auto_error=False)
_Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


@dataclass(frozen=True)
class Principal:
    user: User
    session: UserSession


@dataclass(frozen=True)
class TenantContext:
    tenant_id: UUID
    user: User
    role: str


def _unauthenticated(message: str = "Authentication required"):
    return api_error(401, "UNAUTHENTICATED", message, {"WWW-Authenticate": "Bearer"})


async def _resolve_principal(
    creds: HTTPAuthorizationCredentials, db: AsyncSession, settings: Settings
) -> Principal:
    try:
        claims = decode_token(creds.credentials, settings)
        session_id = UUID(claims["jti"])
        user_id = UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise _unauthenticated("Invalid or expired token") from exc

    session = await db.get(UserSession, session_id)
    if (
        session is None
        or session.user_id != user_id
        or session.revoked_at is not None
        or as_utc(session.expires_at) <= utcnow()
    ):
        raise _unauthenticated("Session is no longer valid")
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthenticated("Account is not active")
    return Principal(user=user, session=session)


async def get_current_principal(
    creds: _Credentials, db: DbSession, settings: AppSettings
) -> Principal:
    if creds is None:
        raise _unauthenticated()
    return await _resolve_principal(creds, db, settings)


async def get_optional_principal(
    creds: _Credentials, db: DbSession, settings: AppSettings
) -> Principal | None:
    if creds is None:
        return None
    return await _resolve_principal(creds, db, settings)


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]
OptionalPrincipal = Annotated[Principal | None, Depends(get_optional_principal)]


async def deny(
    db: AsyncSession,
    *,
    user: User,
    tenant_id: UUID | None,
    resource_type: str,
    resource_id: str,
    reason_code: str,
    metadata: dict | None = None,
    status_code: int = 403,
) -> None:
    """Audit an authorization denial, commit it (so it survives), then raise."""
    await audit.record(
        db,
        action="authz.denied",
        resource_type=resource_type,
        resource_id=resource_id,
        actor_id=user.id,
        tenant_id=tenant_id,
        reason_code=reason_code,
        metadata=metadata,
    )
    await db.commit()
    raise api_error(status_code, "FORBIDDEN", "You do not have access to this resource")


async def authorize_tenant(
    db: AsyncSession, user: User, tenant_id: UUID, roles: tuple[str, ...], path: str
) -> TenantContext:
    """Tenant scope comes from authenticated membership only (FR-TEN-03)."""
    tenant = await db.get(Tenant, tenant_id)
    active = tenant is not None and tenant.is_active
    membership = None
    if active:
        membership = await db.scalar(
            select(Membership).where(
                Membership.tenant_id == tenant_id, Membership.user_id == user.id
            )
        )
    if membership is None or membership.role not in roles:
        if not active:
            reason = "TENANT_UNAVAILABLE"
        elif membership is None:
            reason = "NOT_MEMBER"
        else:
            reason = "ROLE_FORBIDDEN"
        await deny(
            db,
            user=user,
            tenant_id=tenant_id if tenant is not None else None,
            resource_type="tenant",
            resource_id=str(tenant_id),
            reason_code=reason,
            metadata={"path": path, "required_roles": sorted(roles)},
        )
    return TenantContext(tenant_id=tenant_id, user=user, role=membership.role)


def require_tenant_role(*roles: str):
    """Dependency factory: caller must hold one of `roles` in the path's tenant."""

    async def dependency(
        tenant_id: UUID, principal: CurrentPrincipal, db: DbSession
    ) -> TenantContext:
        return await authorize_tenant(db, principal.user, tenant_id, roles, f"tenant/{tenant_id}")

    return dependency


async def require_tenant_manager(
    tenant_id: UUID, principal: CurrentPrincipal, db: DbSession
) -> TenantContext:
    """Platform admins or this tenant's admins may manage tenant membership."""
    if principal.user.is_platform_admin:
        if await db.get(Tenant, tenant_id) is None:
            raise api_error(404, "NOT_FOUND", "Tenant not found")
        return TenantContext(tenant_id=tenant_id, user=principal.user, role="platform_admin")
    return await authorize_tenant(
        db, principal.user, tenant_id, (ROLE_TENANT_ADMIN,), f"tenant/{tenant_id}/manage"
    )


async def require_platform_admin(principal: CurrentPrincipal, db: DbSession) -> Principal:
    if not principal.user.is_platform_admin:
        await deny(
            db,
            user=principal.user,
            tenant_id=None,
            resource_type="platform",
            resource_id="admin",
            reason_code="NOT_PLATFORM_ADMIN",
        )
    return principal


PlatformAdmin = Annotated[Principal, Depends(require_platform_admin)]
TenantManager = Annotated[TenantContext, Depends(require_tenant_manager)]
OrganizerCtx = Annotated[TenantContext, Depends(require_tenant_role(*ORGANIZER_ROLES))]
CandidateCtx = Annotated[TenantContext, Depends(require_tenant_role(ROLE_CANDIDATE))]
