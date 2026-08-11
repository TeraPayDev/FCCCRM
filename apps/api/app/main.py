from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.security_headers import BasicRateLimitMiddleware, SecurityHeadersMiddleware

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BasicRateLimitMiddleware, requests_per_minute=300)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    """Return a minimal API root response."""
    return {
        "name": settings.app_name,
        "status": "running",
        "version": settings.app_version,
    }
