from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/version")
async def version() -> dict[str, str]:
    """Return the CRAM API application version and environment."""
    settings = get_settings()
    return {
        "service": "cram-api",
        "version": settings.app_version,
        "environment": settings.app_env,
    }
