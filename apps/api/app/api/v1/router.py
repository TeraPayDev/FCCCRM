from fastapi import APIRouter

from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.datasets import router as datasets_router
from app.api.v1.endpoints.engineering import router as engineering_router
from app.api.v1.endpoints.gis import router as gis_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.organisations import router as organisations_router
from app.api.v1.endpoints.public_data import router as public_data_router
from app.api.v1.endpoints.roadmap import router as roadmap_router
from app.api.v1.endpoints.version import router as version_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(version_router)
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(gis_router)
api_router.include_router(datasets_router)
api_router.include_router(organisations_router)
api_router.include_router(public_data_router)

api_router.include_router(roadmap_router)
api_router.include_router(engineering_router)
