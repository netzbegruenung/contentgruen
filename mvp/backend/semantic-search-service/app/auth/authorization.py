"""
Authorization utilities for validating user permissions and identity.
"""

import re
from fastapi import HTTPException
from typing import Optional


class AuthorizationError(Exception):
    """Custom exception for authorization failures."""

    pass


def validate_user_id(user_id: str) -> str:
    """
    Validate that the user ID is properly formatted and safe.

    Args:
        user_id: The user ID from X-User header

    Returns:
        str: The validated user ID

    Raises:
        HTTPException: If user ID is invalid
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID is required")

    # Remove whitespace
    user_id = user_id.strip()

    if not user_id:
        raise HTTPException(status_code=401, detail="User ID cannot be empty")

    # Check length limits
    if len(user_id) < 2:
        raise HTTPException(status_code=401, detail="User ID too short")

    if len(user_id) > 100:
        raise HTTPException(status_code=401, detail="User ID too long")

    # Check for valid characters (alphanumeric, underscore, hyphen, dot, @)
    if not re.match(r"^[a-zA-Z0-9._@-]+$", user_id):
        raise HTTPException(
            status_code=401, detail="User ID contains invalid characters"
        )

    return user_id


def check_user_permissions(
    user_id: str, operation: str, resource: Optional[str] = None
) -> bool:
    """
    Check if user has permission to perform an operation on a resource.

    Args:
        user_id: The validated user ID
        operation: The operation being performed (read, write, delete, etc.)
        resource: Optional resource identifier

    Returns:
        bool: True if user has permission

    Raises:
        HTTPException: If user lacks permission
    """
    # For now, implement basic validation
    # In a full system, this would check against a user permissions database

    validated_user_id = validate_user_id(user_id)

    # Basic rate limiting check - prevent obvious abuse
    if operation == "write" and len(validated_user_id) < 3:
        raise HTTPException(
            status_code=403, detail="User account too new for write operations"
        )

    # Check for suspicious patterns
    suspicious_patterns = ["admin", "root", "system", "test123", "guest"]
    user_lower = validated_user_id.lower()

    if any(pattern in user_lower for pattern in suspicious_patterns):
        if operation in ["write", "delete"]:
            raise HTTPException(
                status_code=403,
                detail="Write operations not allowed for this user type",
            )

    return True


def require_auth(
    user_id: str, operation: str = "read", resource: Optional[str] = None
) -> str:
    """
    Validate user authorization for an operation.

    Args:
        user_id: User ID from X-User header
        operation: Operation being performed
        resource: Optional resource identifier

    Returns:
        str: Validated user ID

    Raises:
        HTTPException: If authorization fails
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User header missing")

    validated_user_id = validate_user_id(user_id)
    check_user_permissions(validated_user_id, operation, resource)

    return validated_user_id
