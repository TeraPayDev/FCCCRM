from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return the CRAM API health status."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "cram-api",
        "version": settings.app_version,
    }
