from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routers import agent, auth, health, listings
from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware
from app.core.redis import redis_client

API_PREFIX = "/api/v1"

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("startup", env=get_settings().app_env)
    yield
    await redis_client.aclose()
    await engine.dispose()
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=settings.app_env == "production")

    app = FastAPI(
        title="PropVisit API",
        version="0.1.0",
        description="Property listings and site-visit booking.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Cache", "X-Request-ID", "Retry-After"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    register_error_handlers(app)
    for router in (health.router, auth.router, listings.router, agent.router):
        app.include_router(router, prefix=API_PREFIX)

    if not (settings.supabase_url and settings.supabase_key):
        # Local-disk image fallback: serve uploaded files directly.
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")
    return app


app = create_app()
