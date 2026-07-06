"""
API endpoints for content moderation and reporting.
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Query
from typing import Optional
from pydantic import BaseModel, Field

from services.moderation_service import get_moderation_service
from core.config import Settings
from core.logging import get_logger
from dependencies import get_settings, get_current_user_optional, require_admin
from utils.rate_limiter import report_rate_limiter

logger = get_logger(__name__)

router = APIRouter()


# Request/Response Models
class ReportContentRequest(BaseModel):
    """Request model for reporting content."""

    content_id: str = Field(..., description="UUID of the content to report")
    content_type: str = Field(
        ..., description="Type of content (commentary, generictext, etc.)"
    )
    reason: str = Field(
        ..., description="Reason for report (spam, inappropriate, duplicate, other)"
    )
    description: Optional[str] = Field(
        None, description="Optional detailed description"
    )


class ReportContentResponse(BaseModel):
    """Response model for content report submission."""

    success: bool
    message: str


class PendingReportsResponse(BaseModel):
    """Response model for list of pending reports."""

    total: int
    reports: list


class DeleteContentResponse(BaseModel):
    """Response model for content deletion."""

    success: bool
    message: str


class DismissReportResponse(BaseModel):
    """Response model for report dismissal."""

    success: bool
    message: str


class ReportStatsResponse(BaseModel):
    """Response model for report statistics."""

    total: int
    pending: int
    reviewed: int
    dismissed: int
    by_status: dict


# Public Endpoint - Report Content
@router.post("/report", response_model=ReportContentResponse)
async def report_content(
    request: ReportContentRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    settings: Settings = Depends(get_settings),
):
    """
    Report a content item.

    Anyone can report content (authenticated or anonymous).
    Reports are tracked by user_id or session_id.
    Rate limited to 5 reports per 15 minutes per user/session.
    """
    try:
        # Determine identifier for rate limiting (prefer user_id, fallback to session_id)
        rate_limit_identifier = (
            x_user_id
            if x_user_id and x_user_id != "anonymous"
            else x_session_id or "unknown"
        )

        # Check rate limit
        if await report_rate_limiter.is_rate_limited(rate_limit_identifier):
            logger.warning(
                f"Rate limit exceeded for report from: {rate_limit_identifier}"
            )
            raise HTTPException(
                status_code=429,
                detail="Too many reports. Please wait before submitting another report.",
            )

        logger.info(f"Content report received: {request.content_id} - {request.reason}")

        moderation_service = get_moderation_service()
        success = await moderation_service.report_content(
            content_id=request.content_id,
            content_type=request.content_type,
            reason=request.reason,
            user_id=x_user_id if x_user_id and x_user_id != "anonymous" else None,
            session_id=x_session_id,
            description=request.description,
        )

        if success:
            return ReportContentResponse(
                success=True,
                message="Content reported successfully. We will review it shortly.",
            )
        else:
            raise HTTPException(
                status_code=400, detail="Failed to submit report. Please try again."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in report_content endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# Admin Endpoints - Get Reports
@router.get("/reports", response_model=PendingReportsResponse)
async def get_reports(
    status: str = Query(
        "pending",
        description="Filter by status: pending, reviewed, dismissed, or all",
        regex="^(pending|reviewed|dismissed|all)$",
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of reports"),
    offset: int = Query(0, ge=0, description="Number of reports to skip"),
    admin_user: str = Depends(require_admin),
    settings: Settings = Depends(get_settings),
):
    """
    Get content reports filtered by status (Admin only).

    Status options:
    - pending: Reports awaiting review (default)
    - reviewed: Reports where content was deleted
    - dismissed: Reports that were dismissed
    - all: All reports regardless of status
    """
    try:
        logger.info(
            f"Admin {admin_user} fetching {status} reports (limit={limit}, offset={offset})"
        )

        moderation_service = get_moderation_service()
        reports = await moderation_service.get_reports(
            status=status, limit=limit, offset=offset
        )

        return PendingReportsResponse(total=len(reports), reports=reports)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_reports endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# Admin Endpoint - Delete Content
@router.delete(
    "/content/{content_type}/{content_id}", response_model=DeleteContentResponse
)
async def delete_content(
    content_type: str,
    content_id: str,
    admin_user: str = Depends(require_admin),
    settings: Settings = Depends(get_settings),
):
    """
    Delete content from the system (Admin only).

    Removes content from Qdrant and marks related reports as resolved.
    """
    try:
        logger.info(f"Admin {admin_user} deleting content: {content_type}/{content_id}")

        moderation_service = get_moderation_service()
        success = await moderation_service.delete_content(
            content_id=content_id, content_type=content_type, deleted_by=admin_user
        )

        if success:
            return DeleteContentResponse(
                success=True,
                message=f"Content {content_id} deleted successfully",
            )
        else:
            raise HTTPException(
                status_code=404, detail="Content not found or already deleted"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_content endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# Admin Endpoint - Dismiss Report
@router.put("/reports/{report_id}/dismiss", response_model=DismissReportResponse)
async def dismiss_report(
    report_id: str,
    notes: Optional[str] = None,
    admin_user: str = Depends(require_admin),
    settings: Settings = Depends(get_settings),
):
    """
    Dismiss a content report without taking action (Admin only).

    Marks report as reviewed without deleting content.
    """
    try:
        logger.info(f"Admin {admin_user} dismissing report: {report_id}")

        moderation_service = get_moderation_service()
        success = await moderation_service.dismiss_report(
            report_id=report_id, dismissed_by=admin_user, notes=notes
        )

        if success:
            return DismissReportResponse(
                success=True, message=f"Report {report_id} dismissed successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Report not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in dismiss_report endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# Admin Endpoint - Get Report Statistics
@router.get("/stats", response_model=ReportStatsResponse)
async def get_report_stats(
    admin_user: str = Depends(require_admin),
    settings: Settings = Depends(get_settings),
):
    """
    Get report statistics (Admin only).

    Returns counts of reports by status.
    """
    try:
        logger.info(f"Admin {admin_user} fetching report stats")

        moderation_service = get_moderation_service()
        stats = moderation_service.get_report_stats()

        return ReportStatsResponse(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_report_stats endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
