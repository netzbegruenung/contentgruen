"""
Art.-9-Einwilligung der angemeldeten Person (#489): Stand lesen, einwilligen,
widerrufen. Die Person kommt aus ``X-User``. Was die Einwilligung sperrt:
services/art9_einwilligung_service.py.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from core.fehler import INTERNER_FEHLER
from core.logging import get_logger, log_pseudonym
from dependencies import require_user
from domain.art9_einwilligung import (
    AKTUELLER_WORTLAUT,
    WORTLAUT_KENNUNG_MAX,
    WORTLAUTE,
)
from services import art9_einwilligung_service
from services.abzeichen_service import get_abzeichen_service
from services.art9_einwilligung_service import UnbekannterWortlaut

logger = get_logger(__name__)

router = APIRouter()


class Wortlaut(BaseModel):
    kennung: str
    text: str


class StandResponse(BaseModel):
    eingewilligt: bool
    # Kennung des Wortlauts, dem die Person zugestimmt hat, auch nach einem Widerruf
    wortlaut: Optional[str]
    eingewilligt_am: Optional[datetime]
    widerrufen_am: Optional[datetime]
    # Der Wortlaut, den die App zum Einwilligen zeigt
    aktueller_wortlaut: Wortlaut


class EinwilligenRequest(BaseModel):
    wortlaut: str = Field(..., max_length=WORTLAUT_KENNUNG_MAX)


def _service():
    return art9_einwilligung_service.get_art9_einwilligung_service()


@router.get("", response_model=StandResponse)
def stand(user_id: str = Depends(require_user)) -> StandResponse:
    try:
        einwilligung = _service().stand(user_id)
    except Exception as e:
        logger.error(
            f"Art.-9-Einwilligung von {log_pseudonym(user_id)} nicht gelesen: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)
    return StandResponse(
        eingewilligt=einwilligung is not None and einwilligung.gilt,
        wortlaut=einwilligung.wortlaut if einwilligung else None,
        eingewilligt_am=einwilligung.eingewilligt_am if einwilligung else None,
        widerrufen_am=einwilligung.widerrufen_am if einwilligung else None,
        aktueller_wortlaut=Wortlaut(
            kennung=AKTUELLER_WORTLAUT, text=WORTLAUTE[AKTUELLER_WORTLAUT]
        ),
    )


@router.post("", status_code=204)
def einwilligen(
    request: EinwilligenRequest, user_id: str = Depends(require_user)
) -> Response:
    try:
        _service().einwilligen(user_id, request.wortlaut)
    except UnbekannterWortlaut:
        raise HTTPException(
            status_code=422, detail="Unbekannter Wortlaut der Einwilligung"
        )
    except Exception as e:
        logger.error(
            f"Art.-9-Einwilligung von {log_pseudonym(user_id)} nicht gespeichert: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)
    return Response(status_code=204)


@router.delete("", status_code=204)
def widerrufen(user_id: str = Depends(require_user)) -> Response:
    try:
        _service().widerrufen(user_id)
    except Exception as e:
        logger.error(
            f"Widerruf der Art.-9-Einwilligung von {log_pseudonym(user_id)} nicht gespeichert: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)
    # Ohne Einwilligung keine Meilensteine: das sichtbare Abzeichen sofort weg (#351).
    abzeichen = get_abzeichen_service()
    if abzeichen is not None:
        abzeichen.vergessen(user_id)
    return Response(status_code=204)
