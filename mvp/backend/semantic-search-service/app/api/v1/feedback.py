"""
Feedback an das Team (#343). Senden darf jede Person, auch ohne Anmeldung; lesen,
als erledigt markieren und einzeln loeschen (#425) duerfen nur Admins. Was
gespeichert wird: services/feedback_service.py.
"""

import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, field_validator

from core.logging import get_logger
from dependencies import get_feedback_service, require_admin
from services.feedback_service import (
    AUFBEWAHRUNG_TAGE,
    KONTAKT_MAX,
    LIMIT_STANDARD,
    TEXT_MAX,
    FeedbackEintrag,
    FeedbackService,
)
from utils.client_identity import derive_client_key
from utils.rate_limiter import feedback_rate_limiter

logger = get_logger(__name__)

router = APIRouter()


class FeedbackSendenRequest(BaseModel):
    text: str = Field(..., max_length=TEXT_MAX)
    kontakt: Optional[str] = Field(None, max_length=KONTAKT_MAX)

    @field_validator("text")
    @classmethod
    def _text_nicht_leer(cls, wert: str) -> str:
        wert = wert.strip()
        if not wert:
            raise ValueError("Feedback darf nicht leer sein")
        return wert

    @field_validator("kontakt")
    @classmethod
    def _leerer_kontakt_ist_keiner(cls, wert: Optional[str]) -> Optional[str]:
        if wert is None:
            return None
        return wert.strip() or None


class FeedbackSendenResponse(BaseModel):
    success: bool


class FeedbackEintragResponse(BaseModel):
    id: uuid.UUID
    text: str
    kontakt: Optional[str]
    eingegangen_am: date
    erledigt: bool

    @classmethod
    def aus(cls, e: FeedbackEintrag) -> "FeedbackEintragResponse":
        return cls(
            id=e.id,
            text=e.text,
            kontakt=e.kontakt,
            eingegangen_am=e.eingegangen_am,
            erledigt=e.erledigt,
        )


class FeedbackErledigtRequest(BaseModel):
    erledigt: bool


class FeedbackListeResponse(BaseModel):
    aufbewahrung_tage: int
    eintraege: List[FeedbackEintragResponse]


@router.post("/senden", status_code=201, response_model=FeedbackSendenResponse)
async def feedback_senden(
    request: FeedbackSendenRequest,
    http_request: Request,
    service: FeedbackService = Depends(get_feedback_service),
):
    """
    Feedback speichern. Ohne Anmeldung erreichbar (BFF/Proxy/EndpointPolicy.cs);
    das Rate-Limit haengt deshalb an der Adresse, wie bei Meldungen. Der Schluessel
    ist ein prozesslokaler Hash und wird weder gespeichert noch geloggt. X-User
    wird bewusst nicht gelesen: Feedback traegt keine Kennung.
    """
    if await feedback_rate_limiter.is_rate_limited(derive_client_key(http_request)):
        raise HTTPException(
            status_code=429, detail="Too much feedback. Please wait a moment."
        )
    try:
        service.senden(request.text, request.kontakt)
    except Exception as e:
        logger.error(f"Error storing feedback: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to store feedback")
    return FeedbackSendenResponse(success=True)


@router.get("", response_model=FeedbackListeResponse)
async def feedback_liste(
    limit: int = Query(LIMIT_STANDARD, ge=1, le=500),
    erledigt: Optional[bool] = Query(None),
    admin_user: str = Depends(require_admin),
    service: FeedbackService = Depends(get_feedback_service),
):
    """
    Das neueste Feedback zuerst, mit Kontakt, falls angegeben. erledigt=false
    liefert nur das offene, erledigt=true nur das erledigte, ohne alles.
    """
    try:
        eintraege = service.neueste(limit, erledigt)
    except Exception as e:
        logger.error(f"Error fetching feedback: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch feedback")
    return FeedbackListeResponse(
        aufbewahrung_tage=AUFBEWAHRUNG_TAGE,
        eintraege=[FeedbackEintragResponse.aus(e) for e in eintraege],
    )


@router.patch("/{feedback_id}", response_model=FeedbackEintragResponse)
async def feedback_erledigt_setzen(
    feedback_id: uuid.UUID,
    request: FeedbackErledigtRequest,
    admin_user: str = Depends(require_admin),
    service: FeedbackService = Depends(get_feedback_service),
):
    """Als erledigt markieren oder das zuruecknehmen; die Frist bleibt."""
    eintrag = service.erledigt_setzen(feedback_id, request.erledigt)
    if eintrag is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return FeedbackEintragResponse.aus(eintrag)


@router.delete("/{feedback_id}", status_code=204)
async def feedback_loeschen(
    feedback_id: uuid.UUID,
    admin_user: str = Depends(require_admin),
    service: FeedbackService = Depends(get_feedback_service),
):
    """Ein Feedback samt Kontakt sofort loeschen, vor der Frist."""
    if not service.loeschen(feedback_id):
        raise HTTPException(status_code=404, detail="Feedback not found")
    return Response(status_code=204)
