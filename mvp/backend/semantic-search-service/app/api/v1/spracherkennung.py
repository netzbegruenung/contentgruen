"""
Spracherkennung beim Schreiben (#405): Die Formulare für Beiträge und für "Aussage
vorab anlegen" fragen etwa eine Sekunde nach der letzten Eingabe nach und zeigen einen
Sprachhinweis, wenn der Text offenbar nicht deutsch ist.

Das Ergebnis sieht nur die schreibende Person: nichts wird gespeichert, und der Text
erscheint in keinem Log. Speichern bleibt unabhängig davon immer möglich. Suchanfragen
laufen nicht hierüber.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from core.logging import get_logger
from dependencies import get_spracherkennung, require_user
from services.spracherkennung.spracherkennung import Spracherkennung
from utils.rate_limiter import spracherkennung_rate_limiter

logger = get_logger(__name__)

router = APIRouter()

#: Titel und Text eines Beitrags zusammen, großzügig über den Grenzen der Formulare
#: (wie beim Gegenlesen), damit die Erkennung nie vor dem Speichern scheitert.
TEXT_MAX = 11_000

#: Fehlt Lingua, scheitert jede Anfrage gleich; geloggt wird das einmal.
_nicht_verfuegbar_geloggt = False


class SpracherkennungRequest(BaseModel):
    text: str = Field("", max_length=TEXT_MAX)


class SpracherkennungResponse(BaseModel):
    #: ISO 639-1, wenn der Text offenbar nicht deutsch ist; sonst null.
    sprache: Optional[str]


@router.post("", response_model=SpracherkennungResponse)
async def spracherkennung(
    request: SpracherkennungRequest,
    user_id: str = Depends(require_user),
    erkennung: Spracherkennung = Depends(get_spracherkennung),
):
    """Ist der Text offenbar nicht deutsch? Kurze Texte gelten immer als deutsch."""
    if await spracherkennung_rate_limiter.is_rate_limited(user_id):
        raise HTTPException(status_code=429, detail="Too many requests")
    try:
        # Lingua rechnet auf der CPU; nicht in der Event-Loop.
        sprache = await run_in_threadpool(erkennung.fremdsprache, request.text)
    except (ImportError, OSError) as fehler:
        # Lingua nicht installiert: Das Formular zeigt dann einfach keinen Sprachhinweis.
        global _nicht_verfuegbar_geloggt
        if not _nicht_verfuegbar_geloggt:
            _nicht_verfuegbar_geloggt = True
            logger.error("Spracherkennung nicht verfuegbar: %s", type(fehler).__name__)
        raise HTTPException(status_code=503, detail="Spracherkennung nicht verfügbar")
    return SpracherkennungResponse(sprache=sprache)
