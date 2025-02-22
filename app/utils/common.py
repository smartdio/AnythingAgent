import time
import uuid
from typing import Optional, Any
import json

def generate_id(prefix: str = "") -> str:
    """
    Generate unique ID.

    Args:
        prefix: ID prefix.

    Returns:
        Unique ID string.
    """
    unique_id = str(uuid.uuid4()).replace("-", "")
    return f"{prefix}{unique_id}" if prefix else unique_id

def get_current_timestamp() -> int:
    """
    Get current timestamp.

    Returns:
        Current timestamp (seconds).
    """
    return int(time.time())

def safe_json_loads(data: str, default: Any = None) -> Any:
    """
    Safely parse JSON string.

    Args:
        data: JSON string.
        default: Default value when parsing fails.

    Returns:
        Parsed object, or default value.
    """
    try:
        return json.loads(data)
    except Exception:
        return default

def format_error_response(error: str, code: int = 400) -> dict:
    """
    Format error response.

    Args:
        error: Error message.
        code: Error code.

    Returns:
        Error response dictionary.
    """
    return {
        "error": error,
        "code": code
    } 