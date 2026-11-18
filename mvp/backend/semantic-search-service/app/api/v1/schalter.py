"""
Schalter mit Obergrenze und Admin-Wert (#708, GLOSSARY.md "Schalter"), nur fuer
Admins: Stand aller Schalter lesen und den Admin-Wert setzen. Logik:
services/schalter_service.py.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.config import Settings
from core.fehler import INTERNER_FEHLER
from core.logging import get_logger, log_pseudonym
from dependencies import get_settings, require_admin
from services.schalter_service import (
    ObergrenzeAus,
    SchalterService,
    UnbekannterSchalter,
    get_schalter_service,
)

logger = get_logger(__name__)

router = APIRouter()

OBERGRENZE_AUS = (
    "Der Server erlaubt diesen Schalter nicht (Umgebungsvariable aus). "
    "Einschalten geht erst, wenn die Obergrenze an ist."
)


class SchalterResponse(BaseModel):
    name: str
    erklaerung: str
    umgebungsvariable: str
    obergrenze: bool
    admin_wert: bool
    wirksam: bool
    dsfa_hinweis: Optional[str]


class SchalterListeResponse(BaseModel):
    schalter: List[SchalterResponse]


class SchalterSetzenRequest(BaseModel):
    an: bool


def _service() -> SchalterService:
    return get_schalter_service()


def _liste(dienst: SchalterService, settings: Settings) -> SchalterListeResponse:
    return SchalterListeResponse(
        schalter=[SchalterResponse(**vars(s)) for s in dienst.stand(settings)]
    )


@router.get("", response_model=SchalterListeResponse)
def schalter_liste(
    admin_user: str = Depends(require_admin),
    settings: Settings = Depends(get_settings),
    dienst: SchalterService = Depends(_service),
) -> SchalterListeResponse:
    return _liste(dienst, settings)


@router.put("/{name}", response_model=SchalterListeResponse)
def schalter_setzen(
    name: str,
    anfrage: SchalterSetzenRequest,
    admin_user: str = Depends(require_admin),
    settings: Settings = Depends(get_settings),
    dienst: SchalterService = Depends(_service),
) -> SchalterListeResponse:
    """Admin-Wert setzen; Einschalten ueber die Obergrenze hinaus: 409."""
    try:
        dienst.setzen(name, anfrage.an, admin_user, settings)
    except UnbekannterSchalter:
        raise HTTPException(status_code=404, detail="Schalter nicht gefunden")
    except ObergrenzeAus:
        raise HTTPException(status_code=409, detail=OBERGRENZE_AUS)
    except Exception as e:
        logger.error(
            f"Schalter {name} nicht gesetzt: {type(e).__name__}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)
    logger.info(
        f"Schalter {name} auf {'an' if anfrage.an else 'aus'} "
        f"von {log_pseudonym(admin_user)}"
    )
    return _liste(dienst, settings)
