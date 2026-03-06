"""FastAPI routes for the AI SEO Platform."""

from fastapi import APIRouter

from aiseo.api.integrations import router as integrations_router
from aiseo.api.opportunities import router as opportunities_router
from aiseo.api.projects import router as projects_router
from aiseo.api.queries import router as queries_router
from aiseo.api.results import router as results_router
from aiseo.api.scans import router as scans_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(projects_router)
api_router.include_router(queries_router)
api_router.include_router(integrations_router)
api_router.include_router(scans_router)
api_router.include_router(results_router)
api_router.include_router(opportunities_router)

__all__ = ["api_router"]
