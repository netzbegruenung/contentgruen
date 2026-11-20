"""
Linkvorschau fuer geteilte Links (#360): ein Stueck HTML mit og-Angaben fuer index.html.

Nur fuer den nginx im Frontend-Image, der es per SSI in /beitrag/<id> und /result
einsetzt (nginx.conf, nginx.docker.conf). Er ruft den Dienst direkt im internen Netz
auf, nicht ueber das BFF; dort ist der Pfad gesperrt (EndpointPolicy.Blocked, 404).

200 mit dem Stueck oder 204 ohne Rumpf. Bei 204, jedem Fehler und nach Ablauf der
Frist setzt nginx die allgemeinen Angaben aus index.html ein: Gesperrte, geloeschte
und unbekannte Beitraege zeigen so nichts von sich, und die Seite laedt normal.

Der Suchtext kommt im Header X-Suchtext, nicht in der Adresse: Adressen stehen in
Zugriffsprotokollen (#275). Er wird nicht geloggt.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, Response
from pydantic import ValidationError

from core.config import Settings
from dependencies import (
    get_beitrag_laden,
    get_commentary_service,
    get_generic_text_service,
    get_image_service,
    get_post_service,
    get_settings,
)
from domain.models.content_type import ContentType
from dtos.beitragstypen import ANTWORT_JE_TYP
from services.beitrag_laden import BeitragLader, BeitragUnlesbar
from services.content.base_content_service import BaseContentService
from services.linkvorschau import (
    beitrag_adresse,
    beitrag_tags,
    ergebnis_tags,
    suchtext_aus_adresse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

HTML = "text/html; charset=utf-8"


def _stueck(tags: Optional[str]) -> Response:
    if not tags:
        return Response(status_code=204)
    return Response(content=tags, media_type=HTML)


@router.get("/beitrag/{beitrag_id}", response_class=Response)
async def beitrag_vorschau(
    beitrag_id: uuid.UUID,
    laden: BeitragLader = Depends(get_beitrag_laden),
    commentary_service: BaseContentService = Depends(get_commentary_service),
    generic_text_service: BaseContentService = Depends(get_generic_text_service),
    post_service: BaseContentService = Depends(get_post_service),
    image_service: Optional[BaseContentService] = Depends(get_image_service),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Titel und Anfang des Texts eines sichtbaren Beitrags; sonst 204.

    Liest wie GET /api/v1/content/beitrag/{id}: Gesperrt, geloescht und nie
    vorhanden sind "nicht da". Keine Angaben zur Person.
    """
    dienste = {
        ContentType.COMMENTARY.value: commentary_service,
        ContentType.GENERIC_TEXT.value: generic_text_service,
        ContentType.POST.value: post_service,
        ContentType.IMAGE.value: image_service,
    }
    try:
        allgemein = await laden(beitrag_id)
        typ = allgemein.content_type.value if allgemein else None
        dienst = dienste.get(typ) if typ in ANTWORT_JE_TYP else None
        if dienst is None:
            return _stueck(None)
        beitrag = await dienst.get(beitrag_id)
    except (BeitragUnlesbar, ValidationError):
        # Geloggt haben beitrag_laden bzw. das Repository.
        return _stueck(None)
    except ValueError:
        # Zwischen beiden Lesungen gesperrt oder geloescht (base_repository.get).
        return _stueck(None)
    except Exception as fehler:
        logger.warning(f"Linkvorschau nicht ladbar: {type(fehler).__name__}")
        return _stueck(None)
    if beitrag is None:
        return _stueck(None)
    return _stueck(
        beitrag_tags(
            getattr(beitrag, "title", None),
            getattr(beitrag, "text", None),
            beitrag_adresse(settings.app_url, str(beitrag_id)),
        )
    )


@router.get("/ergebnis", response_class=Response)
async def ergebnis_vorschau(
    x_suchtext: Optional[str] = Header(default=None),
) -> Response:
    """„Antworten auf: <Suchtext>“ fuer die Ergebnisseite; ohne Suchtext 204."""
    return _stueck(ergebnis_tags(suchtext_aus_adresse(x_suchtext)))
