"""
API endpoints for usage tracking functionality.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import uuid
import hashlib
from datetime import datetime, timedelta

from dependencies import get_settings, get_current_user_optional
from services.usage_tracking_service import get_usage_service
from services.cleanup.usage_cleanup_service import get_cleanup_service
from core.config import Settings

logger = logging.getLogger(__name__)


router = APIRouter()


class TrackUsageRequest(BaseModel):
    """Request model for tracking usage."""

    session_id: Optional[str] = Field(None, max_length=255)

    @validator("session_id")
    def validate_session_id(cls, v):
        if v and len(v) > 255:
            raise ValueError("Session ID must be less than 255 characters")
        return v


class TrackUsageResponse(BaseModel):
    """Response model for tracking usage."""

    success: bool
    message: str
    usage_count: int


class UserUsageStatsResponse(BaseModel):
    """Response model for user usage statistics."""

    user_id: str
    unique_contents_contributed: int
    total_usage_count: int
    top_content: list[Dict[str, Any]]


class TrendingContentResponse(BaseModel):
    """Response model for trending content."""

    trending: list[Dict[str, Any]]


class CleanupStatusResponse(BaseModel):
    """Response model for cleanup service status."""

    running: bool
    retention_days: int
    last_cleanup: Optional[str]
    last_cleanup_count: int
    next_cleanup: Optional[str]


class CleanupResultResponse(BaseModel):
    """Response model for cleanup operation result."""

    success: bool
    deleted_count: int
    message: str


@router.post("/content/{content_id}/usage", response_model=TrackUsageResponse)
async def track_content_usage(
    content_id: str,
    request: Request,
    body: TrackUsageRequest,
    user_agent: Optional[str] = Header(None),
    current_user: Optional[str] = Depends(get_current_user_optional),
    settings: Settings = Depends(get_settings),
):
    """
    Track that a content item was used (copied).

    This endpoint should be called when a user clicks the copy button.
    It increments the usage counter for the specified content.
    """
    logger.info(
        f"Tracking usage for content {content_id}, user: {current_user}, session: {body.session_id}"
    )
    try:
        # Validate content_id format
        try:
            content_uuid = uuid.UUID(content_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid content ID format")

        # Validate content_id exists (add check)
        service = get_usage_service()
        # TODO: Add content existence check once repository method is available

        # Sanitize session_id if provided
        if body.session_id:
            # Remove any potentially malicious characters
            body.session_id = body.session_id[:255]  # Truncate to max length

        # Get client IP (consider proxy headers) and hash it for privacy
        client_ip = request.client.host if request.client else None
        if "X-Forwarded-For" in request.headers:
            client_ip = request.headers["X-Forwarded-For"].split(",")[0].strip()

        # Hash IP for privacy (store only hash, not actual IP)
        ip_hash = None
        if client_ip:
            ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()

        # Sanitize user agent
        if user_agent and len(user_agent) > 500:
            user_agent = user_agent[:500]

        # Track usage
        logger.info(f"Calling usage service for content {content_id}")
        success = service.track_content_usage(
            content_id=str(content_uuid),
            user_id=current_user,
            session_id=body.session_id,
            ip_address=ip_hash,  # Pass hash instead of raw IP
            user_agent=user_agent,
        )

        if not success:
            logger.error(f"Failed to track usage for content {content_id}")
            raise HTTPException(status_code=500, detail="Failed to track usage")

        # Get updated count
        usage_count = service.get_content_usage(content_id)
        logger.info(
            f"Successfully tracked usage for content {content_id}, new count: {usage_count}"
        )

        return TrackUsageResponse(
            success=True, message="Usage tracked successfully", usage_count=usage_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error tracking usage for content {content_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/content/{content_id}/usage", response_model=Dict[str, int])
async def get_content_usage(
    content_id: str, settings: Settings = Depends(get_settings)
):
    """
    Get the usage count for a specific content item.
    """
    try:
        # Validate content_id format
        try:
            uuid.UUID(content_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid content ID format")

        service = get_usage_service()
        usage_count = service.get_content_usage(content_id)

        return {"usage_count": usage_count}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting usage for content {content_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/{user_id}/usage-stats", response_model=UserUsageStatsResponse)
async def get_user_usage_stats(
    user_id: str,
    current_user: str = Depends(get_current_user_optional),
    settings: Settings = Depends(get_settings),
):
    """
    Get usage statistics for a specific user's contributed content.

    This shows how many times the user's content has been used by others.
    """
    try:
        # Check authorization - users can only see their own stats unless admin
        # For now, allow users to see their own stats
        if current_user != user_id and not settings.is_admin_user(current_user):
            raise HTTPException(
                status_code=403, detail="Not authorized to view these statistics"
            )

        service = get_usage_service()
        stats = await service.get_user_usage_stats(user_id)

        return UserUsageStatsResponse(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting usage stats for user {user_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trending", response_model=TrendingContentResponse)
async def get_trending_content(
    limit: int = 10, settings: Settings = Depends(get_settings)
):
    """
    Get currently trending content based on recent usage.
    """
    try:
        if limit < 1 or limit > 50:
            raise HTTPException(
                status_code=400, detail="Limit must be between 1 and 50"
            )

        service = get_usage_service()
        trending = service.get_trending_content(limit=limit)

        return TrendingContentResponse(trending=trending)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trending content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/cleanup/status", response_model=CleanupStatusResponse)
async def get_cleanup_status(
    current_user: Optional[str] = Depends(get_current_user_optional),
    settings: Settings = Depends(get_settings),
):
    """
    Get the status of the usage data cleanup service.
    Admin only endpoint.
    """
    try:
        # Check if user is admin (simplified check)
        if not settings.is_admin_user(current_user):
            raise HTTPException(status_code=403, detail="Admin access required")

        cleanup_service = get_cleanup_service()
        status = cleanup_service.get_status()

        return CleanupStatusResponse(**status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cleanup status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/cleanup/run", response_model=CleanupResultResponse)
async def run_cleanup_manually(
    days_to_keep: int = 90,
    current_user: Optional[str] = Depends(get_current_user_optional),
    settings: Settings = Depends(get_settings),
):
    """
    Manually trigger cleanup of old usage data.
    Admin only endpoint.

    Args:
        days_to_keep: Number of days of data to retain (default 90)
    """
    try:
        # Check if user is admin
        if not settings.is_admin_user(current_user):
            raise HTTPException(status_code=403, detail="Admin access required")

        # Validate days_to_keep
        if days_to_keep < 1 or days_to_keep > 365:
            raise HTTPException(
                status_code=400, detail="days_to_keep must be between 1 and 365"
            )

        logger.info(
            f"Manual cleanup triggered by {current_user} with {days_to_keep} days retention"
        )

        # Run cleanup
        service = get_usage_service()
        deleted_count = service.cleanup_old_events(days_to_keep)

        return CleanupResultResponse(
            success=True,
            deleted_count=deleted_count,
            message=f"Successfully deleted {deleted_count} old usage events",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running manual cleanup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
