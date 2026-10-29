"""
Gegenlesen beim Schreiben (#358): feste Regeln ohne KI über Titel und Text eines
Beitrags. Das Formular fragt etwa eine Sekunde nach der letzten Eingabe nach und
zeigt das Siegel mit dem Kriterienanteil der Güte und die Anmerkungen darunter.

Das Ergebnis sieht nur die schreibende Person: nichts wird gespeichert, und der
Text erscheint in keinem Log. Speichern bleibt unabhängig davon immer möglich.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from core.logging import get_logger
from dependencies import get_gegenlesen_service, require_user
from services.gegenlesen.gegenlesen_service import Art, GegenlesenService, Stelle
from utils.rate_limiter import gegenlesen_rate_limiter

logger = get_logger(__name__)

router = APIRouter()

#: Großzügig über den Grenzen der Formulare, damit das Gegenlesen nie vor dem
#: Speichern scheitert; dort gelten die eigentlichen Grenzen.
TITEL_MAX = 500
TEXT_MAX = 10_000
AUSSAGE_MAX = 1000

#: Fehlt das Sprachmodell, scheitert jede Anfrage gleich; geloggt wird das einmal.
_nicht_verfuegbar_geloggt = False


class GegenlesenRequest(BaseModel):
    titel: str = Field("", max_length=TITEL_MAX)
    text: str = Field("", max_length=TEXT_MAX)
    aussage: Optional[str] = Field(None, max_length=AUSSAGE_MAX)
    #: Kommentar und Hintergrundinfo: Der Titel stellt eine Behauptung auf. Ein
    #: Post-Titel ist beschreibend; dort entfällt die Prüfung auf Verneinung.
    titel_ist_behauptung: bool = True


class AnmerkungResponse(BaseModel):
    art: Art
    stelle: Stelle
    text: str
    woerter: List[str]


class GegenlesenResponse(BaseModel):
    guete: Optional[int]
    anmerkungen: List[AnmerkungResponse]


@router.post("", response_model=GegenlesenResponse)
async def gegenlesen(
    request: GegenlesenRequest,
    user_id: str = Depends(require_user),
    service: GegenlesenService = Depends(get_gegenlesen_service),
):
    """Titel, Text und (optional) die Aussage, auf die der Beitrag antwortet, gegenlesen."""
    if await gegenlesen_rate_limiter.is_rate_limited(user_id):
        raise HTTPException(status_code=429, detail="Too many requests")
    try:
        # spaCy rechnet auf der CPU (wenige Millisekunden); nicht in der Event-Loop.
        ergebnis = await run_in_threadpool(
            service.gegenlesen,
            request.titel,
            request.text,
            request.aussage,
            request.titel_ist_behauptung,
        )
    except (ImportError, OSError) as fehler:
        # Sprachmodell nicht installiert: Das Formular zeigt dann einfach nichts.
        global _nicht_verfuegbar_geloggt
        if not _nicht_verfuegbar_geloggt:
            _nicht_verfuegbar_geloggt = True
            logger.error("Gegenlesen nicht verfuegbar: %s", type(fehler).__name__)
        raise HTTPException(status_code=503, detail="Gegenlesen nicht verfügbar")
    return GegenlesenResponse(
        guete=ergebnis.guete,
        anmerkungen=[AnmerkungResponse(**vars(a)) for a in ergebnis.anmerkungen],
    )
