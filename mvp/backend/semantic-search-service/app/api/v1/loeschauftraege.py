"""
Loeschauftraege nach dem Widerruf der Art.-9-Einwilligung (GLOSSARY.md
"Loeschauftrag", DSFA R9b), nur fuer Admins: offene Auftraege mit Frist lesen und
den Loeschablauf fuer einen Auftrag ausfuehren. Ablauf:
services/loeschauftrag_service.py.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.fehler import INTERNER_FEHLER
from core.logging import get_logger, log_pseudonym
from dependencies import require_admin
from services import loeschauftrag_service
from services.loeschauftrag_service import (
    AuftragErledigt,
    AuftragUnbekannt,
    StandGeaendert,
)

logger = get_logger(__name__)

router = APIRouter()

# Kennzeichen fuer das Frontend: anders als "schon erledigt" erneut ausfuehren
STAND_GEAENDERT = "loeschauftrag_stand_geaendert"


class OffenerAuftragResponse(BaseModel):
    id: uuid.UUID
    # Admins sehen die Kennung (Glossar "Kennung"), dazu den Anzeigenamen, falls es ihn gibt
    user_id: str
    anzeigename: Optional[str]
    # Juengster Widerruf; widerruft die Person nach einer neuen Einwilligung erneut,
    # bleibt es bei einem offenen Auftrag
    widerrufen_am: datetime
    angelegt_am: datetime
    frist: datetime
    ueberfaellig: bool
    # Neue Einwilligung nach dem juengsten Widerruf: was ab da kam, bleibt
    neu_eingewilligt_am: Optional[datetime]


class OffeneAuftraegeResponse(BaseModel):
    frist_tage: int
    auftraege: List[OffenerAuftragResponse]


class AusfuehrungResponse(BaseModel):
    beitraege: int
    einwuerfe: int
    saetze: int


def _service():
    return loeschauftrag_service.get_loeschauftrag_service()


@router.get("", response_model=OffeneAuftraegeResponse)
def offene_auftraege(
    admin_user: str = Depends(require_admin),
) -> OffeneAuftraegeResponse:
    try:
        dienst = _service()
        auftraege = dienst.offene()
    except Exception as e:
        logger.error(
            f"Loeschauftraege nicht gelesen: {type(e).__name__}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)
    return OffeneAuftraegeResponse(
        frist_tage=dienst.frist_tage,
        auftraege=[OffenerAuftragResponse(**vars(a)) for a in auftraege],
    )


@router.post("/{auftrag_id}/ausfuehren", response_model=AusfuehrungResponse)
def ausfuehren(
    auftrag_id: uuid.UUID,
    admin_user: str = Depends(require_admin),
) -> AusfuehrungResponse:
    try:
        ergebnis = _service().ausfuehren(auftrag_id)
    except AuftragUnbekannt:
        raise HTTPException(status_code=404, detail="Löschauftrag nicht gefunden")
    except AuftragErledigt:
        raise HTTPException(status_code=409, detail="Löschauftrag ist schon erledigt")
    except StandGeaendert:
        # Widerruf oder neue Einwilligung waehrend der Ausfuehrung: Auftrag offen, der
        # naechste Klick nimmt den neuen Stand (Qdrant-Teil ist wiederholbar).
        raise HTTPException(status_code=409, detail=STAND_GEAENDERT)
    except Exception as e:
        logger.error(
            f"Loeschauftrag {auftrag_id} nicht ausgefuehrt: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)
    logger.info(
        f"Loeschauftrag {auftrag_id} ausgefuehrt von {log_pseudonym(admin_user)}: "
        f"{ergebnis.beitraege} Beitraege anonymisiert, {ergebnis.einwuerfe} Einwuerfe "
        f"geloescht, {ergebnis.saetze} Saetze mit Platzhalter"
    )
    return AusfuehrungResponse(**vars(ergebnis))
