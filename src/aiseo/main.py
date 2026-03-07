"""FastAPI application factory."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aiseo.config import reset_request_api_key_overrides, set_request_api_key_overrides
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

    # CORS middleware — allow all origins for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    from aiseo.api import api_router

    app.include_router(api_router)

    @app.middleware("http")
    async def inject_request_api_keys(request, call_next):
        headers_to_settings = {
            "x-openai-api-key": "openai_api_key",
            "x-anthropic-api-key": "anthropic_api_key",
            "x-google-api-key": "google_api_key",
            "x-perplexity-api-key": "perplexity_api_key",
            "x-xai-api-key": "xai_api_key",
        }
        overrides: dict[str, str] = {}
        for header_name, setting_name in headers_to_settings.items():
            value = request.headers.get(header_name)
            if value:
                overrides[setting_name] = value.strip()

        token = set_request_api_key_overrides(overrides)
        try:
            return await call_next(request)
        finally:
            reset_request_api_key_overrides(token)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
