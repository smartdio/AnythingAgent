from fastapi import Request, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from typing import Callable
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("middleware")

async def verify_api_key_middleware(
    request: Request,
    call_next: Callable
):
    """
    API key verification middleware.

    Args:
        request: Request object.
        call_next: Next handler function.

    Returns:
        Response object.

    Raises:
        HTTPException: Raised when verification fails.
    """
    # If API key verification is not enabled, proceed directly
    if not settings.ENABLE_API_KEY:
        return await call_next(request)
    
    # Get and verify Authorization header
    authorization = request.headers.get(settings.API_KEY_NAME)
    if not authorization:
        logger.warning(f"Missing {settings.API_KEY_NAME} header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{settings.API_KEY_NAME} header not found"
        )
    
    # Parse Authorization header
    scheme, api_key = get_authorization_scheme_param(authorization)
    if scheme.lower() != settings.API_KEY_PREFIX.lower():
        logger.warning(f"Invalid authorization scheme: {scheme}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme"
        )
    
    if not api_key or api_key.strip() != settings.API_KEY:
        logger.warning("Invalid API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # API key verification passed, continue processing request
    response = await call_next(request)
    return response 