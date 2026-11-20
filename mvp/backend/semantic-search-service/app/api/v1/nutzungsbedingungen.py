"""
Zustimmung der angemeldeten Person zu den Nutzungsbedingungen: Stand lesen, zustimmen.
Die Person kommt aus ``X-User``. Was ohne Zustimmung gesperrt ist:
services/nutzungsbedingungen_service.py.

Den Stand liefert auch ``GET /api/v1/art9-einwilligung`` (Feld
``nutzungsbedingungen``), damit die App nach dem Anmelden mit einer Abfrage weiss, ob
sie auf /einwilligung fuehrt.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from core.fehler import INTERNER_FEHLER
from core.logging import get_logger, log_pseudonym
from dependencies import require_user
from domain.nutzungsbedingungen import AKTUELLER_STAND, STAENDE, STAND_KENNUNG_MAX
from services import nutzungsbedingungen_service
from services.nutzungsbedingungen_service import StandGiltNicht, UnbekannterStand

logger = get_logger(__name__)

router = APIRouter()


class NbFassung(BaseModel):
    # Kennung JJJJ-MM-TT und die Stand-Zeile der Seite ("19. November 2026")
    kennung: str
    stand: str


class NbStandResponse(BaseModel):
    zugestimmt: bool
    # Stand, dem die Person zuletzt zugestimmt hat, auch wenn er nicht mehr zaehlt
    stand: Optional[str]
    zugestimmt_am: Optional[datetime]
    # Der Stand, dem die App zustimmen laesst
    aktueller_stand: NbFassung


class ZustimmenRequest(BaseModel):
    stand: str = Field(..., max_length=STAND_KENNUNG_MAX)


def _service():
    return nutzungsbedingungen_service.get_nutzungsbedingungen_service()


def nb_stand(user_id: str) -> NbStandResponse:
    """Der Stand der Person; wirft, wenn er nicht lesbar ist."""
    zustimmung = _service().stand(user_id)
    return NbStandResponse(
        zugestimmt=zustimmung is not None and zustimmung.zaehlt,
        stand=zustimmung.stand if zustimmung else None,
        zugestimmt_am=zustimmung.zugestimmt_am if zustimmung else None,
        aktueller_stand=NbFassung(
            kennung=AKTUELLER_STAND, stand=STAENDE[AKTUELLER_STAND]
        ),
    )


@router.get("", response_model=NbStandResponse)
def stand(user_id: str = Depends(require_user)) -> NbStandResponse:
    try:
        return nb_stand(user_id)
    except Exception as e:
        logger.error(
            f"Zustimmung zu den Nutzungsbedingungen von {log_pseudonym(user_id)} nicht gelesen: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)


@router.post("", status_code=204)
def zustimmen(
    request: ZustimmenRequest, user_id: str = Depends(require_user)
) -> Response:
    try:
        _service().zustimmen(user_id, request.stand)
    except UnbekannterStand:
        raise HTTPException(
            status_code=422, detail="Unbekannter Stand der Nutzungsbedingungen"
        )
    except StandGiltNicht:
        # Etwa ein Tab von gestern: /einwilligung laedt dann den aktuellen Stand.
        raise HTTPException(
            status_code=400,
            detail="Dieser Stand der Nutzungsbedingungen gilt nicht mehr",
        )
    except Exception as e:
        logger.error(
            f"Zustimmung zu den Nutzungsbedingungen von {log_pseudonym(user_id)} nicht gespeichert: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)
    return Response(status_code=204)
