from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/version")
async def get_version():
    """
    Get service version information
    """
    return {
        "version": settings.VERSION,
        "project_name": settings.PROJECT_NAME
    } 