"""
API dependencies module.
Additional dependency functions can be added here.
"""

from fastapi import Header, HTTPException, status
from app.core.config import settings

async def verify_api_key(authorization: str = Header(...)) -> str:
    """
    Verify API key.

    Args:
        authorization: Authorization header value.

    Returns:
        API key.

    Raises:
        HTTPException: Raised when verification fails.
    """
    if not authorization.startswith(f"{settings.API_KEY_PREFIX} "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    api_key = authorization.split(" ")[1]
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key not provided"
        )
    
    # TODO: Additional API key verification logic can be added here
    
    return api_key 