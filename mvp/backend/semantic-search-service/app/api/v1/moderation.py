"""
API endpoints for content moderation and reporting.
"""

import uuid

from fastapi import APIRouter, HTTPException, Depends, Header, Query, Request
from typing import Literal, Optional
from pydantic import BaseModel, Field

from services.moderation_service import get_moderation_service
from core.config import Settings
from core.logging import get_logger
from dependencies import get_settings, get_current_user_optional, require_admin
from utils.rate_limiter import report_rate_limiter
from utils.client_identity import derive_client_key

logger = get_logger(__name__)

router = APIRouter()


# Request/Response Models
class ReportContentRequest(BaseModel):
    """Request model for reporting content."""

    content_id: str = Field(..., description="UUID of the content to report")
    content_type: str = Field(
        ...,
        max_length=50,
        description="Type of content (commentary, generictext, etc.)",
    )
    # Literal statt str: die Pruefung lag bisher nur im Service, der bei einem
    # unbekannten Grund False zurueckgab und damit ein 400 ohne Begruendung
    # erzeugte. Als Schema-Typ steht der erlaubte Wertebereich in der API-Doku
    # und der Fehler nennt ihn.
    reason: Literal["spam", "inappropriate", "duplicate", "other"] = Field(
        ..., description="Reason for report"
    )
    # 1000 Zeichen. Ohne Obergrenze wurde ein 5000-Zeichen-Text angenommen und
    # in eine Text-Spalte ohne Laengenbegrenzung geschrieben -- auf einer Route,
    # die bewusst ohne Anmeldung erreichbar ist.
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional detailed description (max 1000 characters)",
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
    http_request: Request,
    x_user_id: Optional[str] = Header(None, alias="X-User"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    settings: Settings = Depends(get_settings),
):
    """
    Report a content item.

    Die Route bleibt bewusst ohne Anmeldung erreichbar: DSA Art. 16 verlangt ein
    leicht zugaengliches Meldeverfahren, und wer etwa eine Urheberrechts-
    verletzung meldet, ist typischerweise kein Nutzer der Plattform.

    Das Rate-Limit haengt deshalb an der Adresse des Aufrufers, nicht mehr an
    X-Session-Id. Der Session-Header wird von der SPA selbst erzeugt und in
    localStorage gehalten; wer je Anfrage einen neuen Wert schickt, hatte damit
    gar kein Limit. Er dient weiterhin der Zuordnung anonymer Meldungen, aber
    keiner Sicherheitsentscheidung mehr.

    Fuer angemeldete Melder gilt zusaetzlich ein Limit auf der Nutzerkennung und
    eine Deduplizierung auf (Nutzer, Inhalt).
    """
    try:
        is_authenticated = bool(x_user_id and x_user_id != "anonymous")

        # Die Adresse begrenzt jeden Aufrufer, auch den anonymen. Der Schluessel
        # ist ein prozesslokaler Hash und wird weder gespeichert noch geloggt.
        rate_limit_keys = [derive_client_key(http_request)]
        if is_authenticated:
            rate_limit_keys.append(f"user:{x_user_id}")

        for key in rate_limit_keys:
            if await report_rate_limiter.is_rate_limited(key):
                logger.info("Rate limit exceeded for content report")
                raise HTTPException(
                    status_code=429,
                    detail="Too many reports. Please wait before submitting another report.",
                )

        moderation_service = get_moderation_service()

        # Existenz pruefen, bevor irgendetwas angelegt wird. Vorher genuegte ein
        # gueltiges UUID-Format, sodass Meldungen zu nie existierenden Kennungen
        # im Posteingang landeten.
        if not await moderation_service.content_exists(request.content_id):
            raise HTTPException(status_code=404, detail="Content not found")

        logger.info(f"Content report received: {request.content_id} - {request.reason}")

        # Meldungen brauchen eine Melder-Kennung: der Service verlangt sie, und die
        # Tabelle hat einen CHECK darauf. Wer ohne Anmeldung und ohne
        # X-Session-Id meldet -- etwa direkt gegen die API statt ueber die SPA --
        # bekam deshalb 400, obwohl die Route ausdruecklich ohne Anmeldung
        # erreichbar sein soll. Ein Zufallstoken je Meldung erfuellt die
        # Bedingung, ohne irgendetwas ueber den Melder auszusagen; insbesondere
        # ist er nicht aus der Adresse abgeleitet.
        reporter_session = x_session_id
        if not is_authenticated and not reporter_session:
            reporter_session = f"anon:{uuid.uuid4()}"

        success = await moderation_service.report_content(
            content_id=request.content_id,
            content_type=request.content_type,
            reason=request.reason,
            user_id=x_user_id if is_authenticated else None,
            session_id=reporter_session,
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
