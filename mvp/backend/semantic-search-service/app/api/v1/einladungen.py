"""
Einladungen (#429). Verwalten duerfen nur Admins; pruefen und einloesen darf jede
Person ohne Anmeldung, die den Link hat (BFF/Proxy/EndpointPolicy.cs). Was gespeichert
wird und was nicht: services/einladung_service.py.
"""

import asyncio
import re
import uuid
from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from core.logging import get_logger
from dependencies import get_einladung_service, require_admin
from services.einladung_service import (
    EINLOESUNGEN_MAX,
    GUELTIG_TAGE_MAX,
    NOTIZ_MAX,
    Einladung,
    EinladungService,
    EinladungUngueltig,
    EinladungZustand,
    KontoAnlegenFehlgeschlagen,
    EinloesenNichtEingerichtet,
)
from utils.client_identity import derive_client_key
from utils.rate_limiter import einladung_pruefen_rate_limiter, einladung_rate_limiter
from utils.utc_tag import heute_utc

logger = get_logger(__name__)

router = APIRouter()

# Nur grob: ein @, davor und dahinter kein Leerraum, dahinter ein Punkt. Ob es die
# Adresse gibt, zeigt erst die Mail von Keycloak.
MAIL_MUSTER = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAIL_MAX = 254
CODE_MAX = 64


class EinladungAnlegenRequest(BaseModel):
    notiz: str = Field(..., max_length=NOTIZ_MAX)
    erlaubte_einloesungen: int = Field(..., ge=1, le=EINLOESUNGEN_MAX)
    gueltig_bis: date

    @field_validator("notiz")
    @classmethod
    def _notiz_nicht_leer(cls, wert: str) -> str:
        wert = wert.strip()
        if not wert:
            raise ValueError("Die Notiz darf nicht leer sein")
        return wert

    @field_validator("gueltig_bis")
    @classmethod
    def _gueltig_bis_im_rahmen(cls, wert: date) -> date:
        heute = heute_utc()
        if wert < heute:
            raise ValueError("Der letzte Tag liegt in der Vergangenheit")
        if wert > heute + timedelta(days=GUELTIG_TAGE_MAX):
            raise ValueError(f"Hoechstens {GUELTIG_TAGE_MAX} Tage gueltig")
        return wert


class EinladungSchaltenRequest(BaseModel):
    abgeschaltet: bool


class EinladungResponse(BaseModel):
    id: uuid.UUID
    code: str
    notiz: str
    erlaubte_einloesungen: int
    einloesungen: int
    gueltig_bis: date
    abgeschaltet: bool
    angelegt_am: date
    zustand: EinladungZustand

    @classmethod
    def aus(cls, e: Einladung) -> "EinladungResponse":
        return cls(
            id=e.id,
            code=e.code,
            notiz=e.notiz,
            erlaubte_einloesungen=e.erlaubte_einloesungen,
            einloesungen=e.einloesungen,
            gueltig_bis=e.gueltig_bis,
            abgeschaltet=e.abgeschaltet,
            angelegt_am=e.angelegt_am,
            zustand=e.zustand(),
        )


class EinladungListeResponse(BaseModel):
    # Ob Einloesen ueberhaupt geht; sonst sagt das Dashboard, dass Links ins Leere fuehren.
    einloesen_eingerichtet: bool
    einladungen: List[EinladungResponse]


class CodeRequest(BaseModel):
    code: str = Field(..., max_length=CODE_MAX)


class PruefenResponse(BaseModel):
    einloesbar: bool


class EinloesenRequest(CodeRequest):
    email: str = Field(..., max_length=MAIL_MAX)

    @field_validator("email")
    @classmethod
    def _email_grob_pruefen(cls, wert: str) -> str:
        # Klein, wie Keycloak Benutzernamen ablegt.
        wert = wert.strip().lower()
        if not MAIL_MUSTER.match(wert):
            raise ValueError("Keine gueltige Mail-Adresse")
        return wert


class EinloesenResponse(BaseModel):
    success: bool


@router.get("", response_model=EinladungListeResponse)
async def einladungen_liste(
    admin_user: str = Depends(require_admin),
    service: EinladungService = Depends(get_einladung_service),
):
    """Alle Einladungen, die neuesten zuerst, mit Zaehler und Zustand."""
    return EinladungListeResponse(
        einloesen_eingerichtet=service.einloesen_eingerichtet,
        einladungen=[EinladungResponse.aus(e) for e in service.alle()],
    )


@router.post("", status_code=201, response_model=EinladungResponse)
async def einladung_anlegen(
    request: EinladungAnlegenRequest,
    admin_user: str = Depends(require_admin),
    service: EinladungService = Depends(get_einladung_service),
):
    einladung = service.anlegen(
        request.notiz, request.erlaubte_einloesungen, request.gueltig_bis
    )
    return EinladungResponse.aus(einladung)


@router.patch("/{einladung_id}", response_model=EinladungResponse)
async def einladung_schalten(
    einladung_id: uuid.UUID,
    request: EinladungSchaltenRequest,
    admin_user: str = Depends(require_admin),
    service: EinladungService = Depends(get_einladung_service),
):
    """Abschalten oder wieder einschalten; der Zaehler bleibt."""
    einladung = service.schalten(einladung_id, request.abgeschaltet)
    if einladung is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return EinladungResponse.aus(einladung)


@router.post("/pruefen", response_model=PruefenResponse)
async def einladung_pruefen(
    request: CodeRequest,
    http_request: Request,
    service: EinladungService = Depends(get_einladung_service),
):
    """
    Ob sich mit dem Code ein Konto anlegen laesst. Warum nicht (abgelaufen,
    aufgebraucht, unbekannt), erfaehrt niemand: Das hilft nur beim Durchprobieren.
    """
    if await einladung_pruefen_rate_limiter.is_rate_limited(
        derive_client_key(http_request)
    ):
        raise HTTPException(status_code=429, detail="Too many requests.")
    return PruefenResponse(einloesbar=service.ist_einloesbar(request.code))


@router.post("/einloesen", status_code=202, response_model=EinloesenResponse)
async def einladung_einloesen(
    request: EinloesenRequest,
    http_request: Request,
    service: EinladungService = Depends(get_einladung_service),
):
    """
    Legt das Konto an; Keycloak schickt die Mail "Passwort festlegen". Gibt es zur
    Adresse schon ein Konto, ist die Antwort dieselbe: Ob eine Adresse ein Konto hat,
    soll hier niemand herausfinden. X-User wird nicht gelesen.
    """
    if await einladung_rate_limiter.is_rate_limited(derive_client_key(http_request)):
        raise HTTPException(status_code=429, detail="Too many requests.")
    try:
        # Im Thread: Keycloak antwortet ueber das Netz, bis zu zehn Sekunden je Schritt.
        await asyncio.to_thread(service.einloesen, request.code, request.email)
    except EinladungUngueltig:
        raise HTTPException(status_code=410, detail="Invitation not valid")
    except EinloesenNichtEingerichtet:
        raise HTTPException(status_code=503, detail="Registration not configured")
    except KontoAnlegenFehlgeschlagen:
        raise HTTPException(status_code=502, detail="Account could not be created")
    return EinloesenResponse(success=True)
