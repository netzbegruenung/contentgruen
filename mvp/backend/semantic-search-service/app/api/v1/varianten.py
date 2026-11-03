"""
Die Varianten eines Beitrags (#356): Ziel des Links "N Varianten" an der Karte.

Fuer Besucher wie Angemeldete, wie die Suche, in der die Karte steht
(EndpointPolicy.cs); ``fuer_aufrufer`` entscheidet, wer Anzeigenamen sieht.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.config import Settings
from core.fehler import INTERNER_FEHLER
from dependencies import (
    get_aufrufer,
    get_content_repository,
    get_reference_service,
    get_settings,
)
from dtos.beitrag import BeitragResponse
from api.v1.usage import OFT_GENUTZT
from repositories.varianten_repository import (
    VariantenRepository,
    get_varianten_repository,
)
from services.beitrag_fuer_aufrufer import Aufrufer, fuer_aufrufer
from services.content.reference_service import ReferenceService
from services.oft_genutzt_service import BeitragLaden, sichtbaren_beitrag_laden
from services.usage_tracking_service import get_usage_service
from services.varianten import varianten_ergaenzen

logger = logging.getLogger(__name__)

router = APIRouter()


class VariantenResponse(BaseModel):
    """Das Original und seine sichtbaren Varianten, als Karten wie bei /usage/trending/woche."""

    original: Dict[str, Any]
    varianten: List[Dict[str, Any]]


def karten_beitrag_laden(
    settings: Settings, reference_service: ReferenceService
) -> BeitragLaden:
    """
    Ein sichtbarer Beitrag mit allem, was die Karte braucht; sonst None. Wie bei
    "Oft genutzt" (api/v1/usage.py) im ``try`` des Endpunkts gebaut: Scheitert ein
    Repository, antwortet er mit seinem 500 und Log.
    """
    from repositories.implementations.qdrant.qdrant_repository_factory import (
        QdrantRepositoryFactory,
    )

    return sichtbaren_beitrag_laden(
        settings,
        get_content_repository(settings),
        QdrantRepositoryFactory(),
        reference_service,
    )


@router.get("/{original_id}", response_model=VariantenResponse)
async def varianten(
    original_id: uuid.UUID,
    aufrufer: Aufrufer = Depends(get_aufrufer),
    settings: Settings = Depends(get_settings),
    reference_service: ReferenceService = Depends(get_reference_service),
    repository: VariantenRepository = Depends(get_varianten_repository),
) -> VariantenResponse:
    """
    404, wenn das Original nicht sichtbar ist. Varianten, die gesperrt oder geloescht
    sind, fehlen. Die meistgenutzte zuerst, bei gleicher Nutzung die neueste.
    """
    try:
        laden = karten_beitrag_laden(settings, reference_service)
        original = await laden(original_id)
        if original is None:
            raise HTTPException(status_code=404, detail="Beitrag nicht gefunden")
        # Gleichzeitig: Jede Variante kostet einige Abrufe im Suchindex.
        geladen = await asyncio.gather(
            *(
                laden(variante_id)
                for variante_id in repository.varianten_von(original_id)
            )
        )
        eintraege = [original, *(v for v in geladen if v is not None)]

        angereichert = get_usage_service().enrich_content_with_usage(eintraege)
        antworten = fuer_aufrufer(
            [
                OFT_GENUTZT.get(e["result_type"], BeitragResponse).model_validate(e)
                for e in angereichert
            ],
            aufrufer,
        )
        varianten_ergaenzen(antworten, repository)
        karten = [
            (
                antwort,
                {**antwort.model_dump(mode="json"), "result_type": e["result_type"]},
            )
            for e, antwort in zip(angereichert, antworten)
        ]
        (_, erste), *rest = karten
        # Nach dem Zeitpunkt selbst, nicht nach seinem Text: Der hat nicht immer
        # Sekundenbruchteile und ordnet sich dann nicht zeitlich. timestamp(), damit
        # Zeitpunkte mit und ohne Zeitzone vergleichbar bleiben.
        rest.sort(key=lambda paar: paar[0].created.timestamp(), reverse=True)
        rest.sort(key=lambda paar: paar[0].usage_count or 0, reverse=True)
        return VariantenResponse(original=erste, varianten=[k for _, k in rest])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading variants: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)
