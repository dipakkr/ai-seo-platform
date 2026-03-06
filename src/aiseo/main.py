"""FastAPI application factory."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from aiseo.models import create_db_and_tables

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    logger.info("starting_aiseo")
    create_db_and_tables()
    yield
    logger.info("shutting_down_aiseo")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI SEO Platform",
        description="AI Visibility Intelligence for SaaS Founders",
        version="0.1.0",
        lifespan=lifespan,
    )

    # API routes will be added in Phase 4
    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
