"""
Sperrnachrichten und Widerspruch fuer den Autor eines gesperrten Beitrags (#448).

Jede angemeldete Person sieht nur die Sperren an ihren eigenen Beitraegen; wessen,
ergibt sich aus der Anmeldung, nie aus einer Kennung in der Adresse. Bestaetigen
oder Entsperren nach einem Widerspruch liegt bei den Admins (api/v1/moderation.py).
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.logging import get_logger
from dependencies import require_user
from domain.models.widerspruch import Widerspruchsergebnis
from services.moderation_service import get_moderation_service

logger = get_logger(__name__)

router = APIRouter()

WIDERSPRUCH_MAX = 2000


class Sperrnachricht(BaseModel):
    id: str
    content_id: str
    content_type: Optional[str]
    titel: Optional[str]
    sperrgrund: str
    begruendung: str
    gesperrt_am: Optional[str]
    # Gesetzt nur, wenn die Sperre nach dem Widerspruch aufgehoben wurde.
    aufgehoben_am: Optional[str]
    # Der eigene Text des Widerspruchs; leer, wenn er ohne Text kam.
    widerspruch: Optional[str]
    widerspruch_am: Optional[str]
    pruefergebnis: Optional[str]
    pruefung_begruendung: Optional[str]
    geprueft_am: Optional[str]


class MeineSperrenResponse(BaseModel):
    sperren: List[Sperrnachricht]


class WiderspruchRequest(BaseModel):
    """Formlos: Der Text darf fehlen."""

    text: Optional[str] = Field(None, max_length=WIDERSPRUCH_MAX)


class WiderspruchResponse(BaseModel):
    success: bool


@router.get("/meine", response_model=MeineSperrenResponse)
async def meine_sperren(user_id: str = Depends(require_user)):
    """Die Sperrnachrichten der angemeldeten Person, die neueste zuerst (auch nach erfolgreichem Widerspruch)."""
    try:
        return MeineSperrenResponse(
            sperren=await get_moderation_service().meine_sperren(user_id)
        )
    except Exception as e:
        logger.error(
            f"Error in meine_sperren endpoint: {type(e).__name__}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{sperre_id}/widerspruch", response_model=WiderspruchResponse)
async def widersprechen(
    sperre_id: uuid.UUID,
    anfrage: WiderspruchRequest,
    user_id: str = Depends(require_user),
):
    """
    Einer Sperre an einem eigenen Beitrag widersprechen; die Admins pruefen erneut.
    404 auch fuer die Sperre eines fremden Beitrags, damit niemand fremde Sperren
    erraten kann; 409, wenn schon widersprochen ist.
    """
    try:
        ergebnis = await get_moderation_service().widersprechen(
            str(sperre_id), user_id, anfrage.text
        )
    except Exception as e:
        logger.error(
            f"Error in widersprechen endpoint: {type(e).__name__}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    if ergebnis is Widerspruchsergebnis.NICHT_GEFUNDEN:
        raise HTTPException(status_code=404, detail="Sperre nicht gefunden")
    if ergebnis is Widerspruchsergebnis.SCHON_WIDERSPROCHEN:
        raise HTTPException(status_code=409, detail="Schon widersprochen")
    return WiderspruchResponse(success=True)
