"""
Vormoderation unbeantworteter Suchanfragen (Entscheidung des Maintainers vom
13.11.2026, P6): Eine Suchanfrage ohne Antwort sehen Nicht-Admins erst, wenn sie
ueber der Schwelle der Kennzahl "Suchen ohne Treffer" liegt und ein Admin sie
freigegeben hat. Hier die Liste fuer die Moderation und die beiden Entscheidungen;
was daraus folgt: services/suchen_ohne_treffer_service.py.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.logging import get_logger
from dependencies import get_suchen_ohne_treffer_service, require_admin
from services.content.statement_service import AussageNichtGefunden
from services.suchen_ohne_treffer_service import (
    KeineUnbeantworteteSuchanfrage,
    SuchenOhneTrefferService,
)

logger = get_logger(__name__)

router = APIRouter()


class ZuPruefendeSuchanfrage(BaseModel):
    statement_id: uuid.UUID
    statement_text: str
    # Personen, die im Zeitraum ohne Treffer danach gesucht haben (wie in "Hier
    # fehlt eine Antwort"); die Zahl der Suchen steht in der Kennzahl.
    personen_ohne_treffer: int


class ZuPruefendeSuchanfragenResponse(BaseModel):
    suchanfragen: List[ZuPruefendeSuchanfrage]


class ZuPruefendeSuchanfragenAnzahl(BaseModel):
    anzahl: int


class SuchanfrageEntscheidungResponse(BaseModel):
    statement_id: uuid.UUID
    freigegeben: bool


@router.get("/suchanfragen", response_model=ZuPruefendeSuchanfragenResponse)
async def zu_pruefende_suchanfragen(
    admin_user: str = Depends(require_admin),
    service: SuchenOhneTrefferService = Depends(get_suchen_ohne_treffer_service),
) -> ZuPruefendeSuchanfragenResponse:
    """Unbeantwortete Suchanfragen ueber der Schwelle ohne Entscheidung (Admin)."""
    try:
        eintraege = await service.zu_pruefen()
    except Exception as e:
        logger.error(
            f"Error in /moderation/suchanfragen: {type(e).__name__}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")
    return ZuPruefendeSuchanfragenResponse(
        suchanfragen=[
            ZuPruefendeSuchanfrage(
                statement_id=e.statement_id,
                statement_text=e.text,
                personen_ohne_treffer=e.personen,
            )
            for e in eintraege
        ]
    )


@router.get("/suchanfragen/anzahl", response_model=ZuPruefendeSuchanfragenAnzahl)
async def zu_pruefende_suchanfragen_anzahl(
    admin_user: str = Depends(require_admin),
    service: SuchenOhneTrefferService = Depends(get_suchen_ohne_treffer_service),
) -> ZuPruefendeSuchanfragenAnzahl:
    """Nur die Zahl, fuer den Zaehler am Umschalter (Admin); ohne Texte."""
    try:
        anzahl = await service.anzahl_zu_pruefen()
    except Exception as e:
        logger.error(
            f"Error in /moderation/suchanfragen/anzahl: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
    return ZuPruefendeSuchanfragenAnzahl(anzahl=anzahl)


async def _entscheiden(
    service: SuchenOhneTrefferService, statement_id: uuid.UUID, freigegeben: bool
) -> SuchanfrageEntscheidungResponse:
    try:
        await service.entscheiden(statement_id, freigegeben)
    except AussageNichtGefunden:
        raise HTTPException(status_code=404, detail="Statement not found")
    except KeineUnbeantworteteSuchanfrage:
        raise HTTPException(
            status_code=409, detail="Statement is not an unanswered search query"
        )
    except Exception as e:
        logger.error(
            f"Error in /moderation/suchanfragen decision: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
    logger.info(f"Admin decided on search query statement: freigegeben={freigegeben}")
    return SuchanfrageEntscheidungResponse(
        statement_id=statement_id, freigegeben=freigegeben
    )


@router.put(
    "/suchanfragen/{statement_id}/freigeben",
    response_model=SuchanfrageEntscheidungResponse,
)
async def suchanfrage_freigeben(
    statement_id: uuid.UUID,
    admin_user: str = Depends(require_admin),
    service: SuchenOhneTrefferService = Depends(get_suchen_ohne_treffer_service),
) -> SuchanfrageEntscheidungResponse:
    """Fuer alle sichtbar machen, solange sie ueber der Schwelle liegt (Admin)."""
    return await _entscheiden(service, statement_id, True)


@router.put(
    "/suchanfragen/{statement_id}/ablehnen",
    response_model=SuchanfrageEntscheidungResponse,
)
async def suchanfrage_ablehnen(
    statement_id: uuid.UUID,
    admin_user: str = Depends(require_admin),
    service: SuchenOhneTrefferService = Depends(get_suchen_ohne_treffer_service),
) -> SuchanfrageEntscheidungResponse:
    """Bleibt fuer Nicht-Admins unsichtbar und verlaesst die Liste (Admin)."""
    return await _entscheiden(service, statement_id, False)
