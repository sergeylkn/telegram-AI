"""FastAPI application factory and lifecycle hooks."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.telegram_webhook import router as telegram_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup shared application resources."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)
    logger.info("application_startup", environment=settings.environment)

    app.state.settings = settings
    try:
        yield
    finally:
        logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    app = FastAPI(title="telegram-AI", version="0.1.0", lifespan=lifespan)

    app.include_router(telegram_router, prefix="/webhooks", tags=["telegram"])
    app.include_router(admin_router, prefix="/admin", tags=["admin"])

    return app


app = create_app()
