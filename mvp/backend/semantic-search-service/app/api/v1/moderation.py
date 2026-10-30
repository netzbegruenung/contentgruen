"""
API endpoints for content moderation and reporting.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Header, Query, Request
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from domain.models.meldegrund import Meldegrund
from domain.models.sperrgrund import Sperrgrund
from services.moderation_service import (
    SchonGesperrt,
    SperreUngueltig,
    get_moderation_service,
)
from services.content.verweise_entfernen import VerweiseNichtEntfernt
from core.config import Settings
from core.logging import get_logger
from dependencies import get_settings, get_current_user_optional, require_admin
from utils.rate_limiter import report_rate_limiter
from utils.besucher_pseudonym import besucher_merkmal
from utils.client_identity import derive_client_key
from repositories.content_report_repository import melder_pseudonym

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
    reason: Meldegrund = Field(..., description="Reason for report")
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


class SperrenRequest(BaseModel):
    """Sperrgrund und Begruendung; beides erfaehrt der Autor (#448)."""

    sperrgrund: Sperrgrund = Field(..., description="Sperrgrund aus der Liste")
    begruendung: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Was genau am Beitrag gegen die Nutzungsbedingungen verstoesst",
    )


class SperreBestaetigenRequest(BaseModel):
    """Begruendung, warum die Sperre nach dem Widerspruch bleibt."""

    begruendung: str = Field(..., min_length=1, max_length=2000)


class SperreResponse(BaseModel):
    """Response model for sperren and entsperren."""

    success: bool
    message: str


class GesperrteResponse(BaseModel):
    """Response model for the list of gesperrte Beitraege."""

    total: int
    beitraege: List[Dict[str, Any]]


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
    settings: Settings = Depends(get_settings),
):
    """
    Report a content item.

    Die Route bleibt bewusst ohne Anmeldung erreichbar: DSA Art. 16 verlangt ein
    leicht zugaengliches Meldeverfahren, und wer etwa eine Urheberrechts-
    verletzung meldet, ist typischerweise kein Nutzer der Plattform.

    Das Rate-Limit haengt deshalb an der Adresse des Aufrufers, nicht mehr an
    X-Session-Id. Den Session-Header erzeugte die SPA selbst; wer je Anfrage
    einen neuen Wert schickte, hatte damit gar kein Limit. Seit #446 gibt es ihn
    nicht mehr, und ein mitgeschickter Wert wird auch nicht gespeichert.

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

        # Anonyme Meldungen tragen das Tagespseudonym des Besuchers: Admins sehen
        # so, ob offene Meldungen am selben Tag aus derselben Quelle kommen. Es
        # bleibt nur, bis die Meldung erledigt ist; dann ersetzt das Repository es
        # durch einen Zufallswert (repositories/content_report_repository.py).
        # Eine Sitzungskennung aus dem Browser gibt es seit #446 nicht mehr, auch
        # nicht neben der Kennung angemeldeter Melder.
        reporter_session = (
            None
            if is_authenticated
            else melder_pseudonym(
                besucher_merkmal(http_request), datetime.now(timezone.utc).date()
            )
        )

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
    - reviewed: Reports that were handled (bearbeitet), e.g. the content was gesperrt
    - dismissed: Reports that were dismissed
    - all: All reports regardless of status
    """
    try:
        logger.info(f"Admin fetching {status} reports (limit={limit}, offset={offset})")

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


# Admin Endpoints - Sperren / Entsperren
@router.put("/content/{content_id}/sperren", response_model=SperreResponse)
async def sperren(
    content_id: uuid.UUID,
    anfrage: SperrenRequest,
    admin_user: str = Depends(require_admin),
):
    """
    Einen gemeldeten Beitrag sperren (Admin only), mit Sperrgrund und Begruendung.

    Der Beitrag verschwindet aus Suche und Ansicht, bleibt aber erhalten und laesst
    sich entsperren. Alle Meldungen zum Beitrag stehen danach auf bearbeitet. Der
    Autor sieht die Sperrnachricht in "Meine Beitraege" und kann widersprechen.
    """
    try:
        logger.info(f"Admin blocking (sperren) content: {content_id}")

        moderation_service = get_moderation_service()
        if not await moderation_service.sperren(
            str(content_id),
            gesperrt_von=admin_user,
            sperrgrund=anfrage.sperrgrund,
            begruendung=anfrage.begruendung,
        ):
            raise HTTPException(status_code=404, detail="Beitrag nicht gefunden")

        return SperreResponse(success=True, message=f"Beitrag {content_id} gesperrt")

    except SchonGesperrt:
        raise HTTPException(status_code=409, detail="Beitrag ist schon gesperrt")
    except SperreUngueltig as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in sperren endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/content/{content_id}/entsperren", response_model=SperreResponse)
async def entsperren(
    content_id: uuid.UUID,
    admin_user: str = Depends(require_admin),
):
    """
    Eine Sperre aufheben (Admin only). Der Beitrag ist danach wieder so sichtbar
    wie vor der Sperre.
    """
    try:
        logger.info(f"Admin unblocking (entsperren) content: {content_id}")

        moderation_service = get_moderation_service()
        if not await moderation_service.entsperren(
            str(content_id), entsperrt_von=admin_user
        ):
            raise HTTPException(status_code=404, detail="Beitrag nicht gefunden")

        return SperreResponse(success=True, message=f"Beitrag {content_id} entsperrt")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in entsperren endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/sperren/{sperre_id}/bestaetigen", response_model=SperreResponse)
async def sperre_bestaetigen(
    sperre_id: uuid.UUID,
    anfrage: SperreBestaetigenRequest,
    admin_user: str = Depends(require_admin),
):
    """
    Nach einem Widerspruch erneut geprueft: Die Sperre bleibt (Admin only). Die
    Begruendung sieht der Autor in seiner Sperrnachricht. Das andere Ergebnis der
    Pruefung ist Entsperren.
    """
    try:
        logger.info(f"Admin confirming Sperre {sperre_id} after Widerspruch")

        if not await get_moderation_service().sperre_bestaetigen(
            str(sperre_id), admin_user, anfrage.begruendung
        ):
            raise HTTPException(
                status_code=404, detail="Keine Sperre mit offenem Widerspruch"
            )

        return SperreResponse(success=True, message="Sperre bestaetigt")

    except SperreUngueltig as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in sperre_bestaetigen endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/gesperrt", response_model=GesperrteResponse)
async def gesperrte_beitraege(admin_user: str = Depends(require_admin)):
    """
    Alle gesperrten Beitraege (Admin only), auch solche ohne Meldung, jeder mit
    seiner Sperre unter "sperre" (Sperrgrund, Widerspruch, Pruefung).
    """
    try:
        logger.info("Admin fetching gesperrte Beitraege")

        beitraege = await get_moderation_service().gesperrte_beitraege()
        return GesperrteResponse(total=len(beitraege), beitraege=beitraege)

    except Exception as e:
        logger.error(f"Error in gesperrte_beitraege endpoint: {e}", exc_info=True)
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

    Removes content from Qdrant and marks related reports as resolved. Vorher
    verschwinden die Verweise der Aussagen auf ihn; scheitert das, ist der Beitrag
    nicht entfernt und die Antwort ein Fehler (#294).

    Kein Moderationsweg mehr: Gemeldete Beitraege sperrt ein Admin (siehe
    sperren). Der Endpunkt bleibt fuer Loeschungen aus Datenschutzgruenden, etwa
    wenn ein Text eine Person erkennbar macht (docs/LOESCHKONZEPT.md). Der Autor
    loescht seinen Beitrag nicht hier, sondern ueber DELETE /api/v1/content/{id}:
    Das setzt nur den Zustand "geloescht" (#250).
    """
    try:
        logger.info(f"Admin deleting content: {content_type}/{content_id}")

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
    except VerweiseNichtEntfernt:
        # Kein "ok": Aussagen verwiesen sonst auf einen Beitrag, den es nicht mehr gibt.
        raise HTTPException(
            status_code=500,
            detail=(
                "Verweise von Aussagen auf den Beitrag konnten nicht entfernt werden. "
                "Der Beitrag ist nicht gelöscht; bitte erneut versuchen."
            ),
        )
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
        logger.info(f"Admin dismissing report: {report_id}")

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
        logger.info("Admin fetching report stats")

        moderation_service = get_moderation_service()
        stats = moderation_service.get_report_stats()

        return ReportStatsResponse(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_report_stats endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
