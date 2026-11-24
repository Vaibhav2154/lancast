from fastapi import APIRouter

from app.core.deps import AppSettings, CurrentPrincipal, DbSession, OptionalPrincipal, deny
from app.core.errors import api_error
from app.schemas.auth_tenants import (
    LoginRequest,
    MeOut,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services import audit
from app.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
    body: RegisterRequest, principal: OptionalPrincipal, db: DbSession
) -> UserOut:
    """First user bootstraps the platform admin; afterwards only platform admins may register."""
    first_user = await auth_service.count_users(db) == 0
    if not first_user:
        if principal is None:
            raise api_error(401, "UNAUTHENTICATED", "Authentication required")
        if not principal.user.is_platform_admin:
            await deny(
                db,
                user=principal.user,
                tenant_id=None,
                resource_type="platform",
                resource_id="register",
                reason_code="NOT_PLATFORM_ADMIN",
            )
    user = await auth_service.create_user(
        db,
        email=body.email,
        full_name=body.full_name,
        password=body.password,
        is_platform_admin=first_user,
    )
    await audit.record(
        db,
        action="user.register",
        resource_type="user",
        resource_id=str(user.id),
        actor_id=principal.user.id if principal else user.id,
        metadata={"bootstrap_admin": first_user},
    )
    await db.commit()
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession, settings: AppSettings) -> TokenResponse:
    token, session, _ = await auth_service.login(db, settings, body.email, body.password)
    await db.commit()
    return TokenResponse(access_token=token, expires_at=session.expires_at)


@router.post("/logout", status_code=204)
async def logout(principal: CurrentPrincipal, db: DbSession) -> None:
    await auth_service.logout(db, principal)
    await db.commit()


@router.get("/me", response_model=MeOut)
async def me(principal: CurrentPrincipal, db: DbSession) -> MeOut:
    memberships = await auth_service.list_memberships(db, principal.user.id)
    return MeOut.model_validate({"user": principal.user, "memberships": memberships})
