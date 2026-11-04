"""
Kürzungsvorschlag (#403): Auf Klick im Kommentar-Formular schlägt der Dienst eine
Kurzfassung aus den eigenen Sätzen des Kommentars vor, ohne KI. Die Person übernimmt
oder verwirft ihn; nichts wird gespeichert, und der Text erscheint in keinem Log.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from core.logging import get_logger
from dtos.commentary import KOMMENTAR_TEXT_MAX
from dependencies import get_kuerzungsvorschlag_service, require_user
from services.kuerzungsvorschlag_service import KuerzungsvorschlagService
from utils.rate_limiter import kuerzungsvorschlag_rate_limiter

logger = get_logger(__name__)

router = APIRouter()

#: Gekürzt wird nur der Haupttext eines Kommentars; mehr schickt das Formular nie.
TEXT_MAX = KOMMENTAR_TEXT_MAX
AUSSAGE_MAX = 1000

#: Fehlt das Sprachmodell, scheitert jede Anfrage gleich; geloggt wird das einmal.
_nicht_verfuegbar_geloggt = False


class KuerzungsvorschlagRequest(BaseModel):
    text: str = Field("", max_length=TEXT_MAX)
    aussage: Optional[str] = Field(None, max_length=AUSSAGE_MAX)


class KuerzungsvorschlagResponse(BaseModel):
    #: None, wenn kein Satz in die Kurzfassung passt.
    vorschlag: Optional[str]


@router.post("", response_model=KuerzungsvorschlagResponse)
async def kuerzungsvorschlag(
    request: KuerzungsvorschlagRequest,
    user_id: str = Depends(require_user),
    service: KuerzungsvorschlagService = Depends(get_kuerzungsvorschlag_service),
):
    """Eine Kurzfassung aus den Sätzen des Kommentars vorschlagen."""
    if await kuerzungsvorschlag_rate_limiter.is_rate_limited(user_id):
        raise HTTPException(status_code=429, detail="Too many requests")
    try:
        # spaCy rechnet auf der CPU; nicht in der Event-Loop.
        vorschlag = await run_in_threadpool(
            service.vorschlagen, request.text, request.aussage
        )
    except (ImportError, OSError) as fehler:
        global _nicht_verfuegbar_geloggt
        if not _nicht_verfuegbar_geloggt:
            _nicht_verfuegbar_geloggt = True
            logger.error(
                "Kuerzungsvorschlag nicht verfuegbar: %s", type(fehler).__name__
            )
        raise HTTPException(status_code=503, detail="Kürzungsvorschlag nicht verfügbar")
    return KuerzungsvorschlagResponse(vorschlag=vorschlag)
