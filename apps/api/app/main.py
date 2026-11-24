from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.routers import assessments, attempts, auth, capsules, internal, tenants
from app.routers.health import router as health_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="LANCAST — Adaptive Resource and Security Orchestration Framework for Campus Assessments",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.public_base_url, "http://localhost:5173", "http://localhost"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health_router)
    application.include_router(auth.router)
    application.include_router(tenants.router)
    application.include_router(assessments.router)
    application.include_router(assessments.grading_router)
    application.include_router(capsules.router)
    application.include_router(attempts.router)
    application.include_router(internal.router)
    return application


app = create_app()
