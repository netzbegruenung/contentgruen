from fastapi import APIRouter, HTTPException, Depends, Query, Header, Response
from typing import List, Optional, Dict, Any, Union
import logging
import uuid

from pydantic import ValidationError

from dependencies import (
    get_aufrufer,
    get_beitrag_laden,
    get_beitrag_loeschen_service,
    get_commentary_service,
    get_generic_text_service,
    get_image_service,
    get_post_service,
    get_settings,
    get_reference_service,
)
from dtos.content import (
    ContentGetAllResponse,
)
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from domain.models.content import ContentDbEntry
from domain.models.content_type import ContentType
from core.config import Settings
from services.usage_tracking_service import get_usage_service
from services.anzeigename_service import angemeldet
from services.beitrag_fuer_aufrufer import Aufrufer, als_responses, fuer_aufrufer
from services.beitrag_laden import BeitragLader, BeitragUnlesbar
from services.content.base_content_service import BaseContentService
from dtos.beitrag import (
    BeitragResponse,
    HintergrundinfoResponse,
    KommentarResponse,
    PostResponse,
)
from dtos.image import BildResponse
from services.content.reference_service import ReferenceService
from services.content.beitrag_loeschen_service import (
    BeitragLoeschenService,
    LoeschErgebnis,
)
from services.content.verweise_entfernen import VerweiseNichtEntfernt
from core.fehler import INTERNER_FEHLER

router = APIRouter()
logger = logging.getLogger(__name__)

# Was /recent liefert, je result_type; ein Typ ohne Eintrag bekommt die allgemeine
# Auswahl (BeitragResponse), statt die Route abzubrechen.
NEUESTE = {"commentary": KommentarResponse, "generictext": HintergrundinfoResponse}


# Retrieves all content from the index
@router.get("/getAll")
async def get_all(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    settings: Settings = Depends(get_settings),
    aufrufer: Aufrufer = Depends(get_aufrufer),
) -> ContentGetAllResponse:
    try:
        logger.debug("/getAll was called")

        offset = (page - 1) * page_size
        repository_factory = QdrantRepositoryFactory()
        content_repository = repository_factory.create_content_repository(settings)
        content_index_results: List[ContentDbEntry] = await content_repository.getAll(
            limit=page_size, offset=offset
        )
        total_count = await content_repository.count()

        logger.debug(f"/getAll got {len(content_index_results)} results")

        # Enrich results with usage statistics
        usage_service = get_usage_service()
        results_dict = [item.model_dump() for item in content_index_results]
        enriched_results = usage_service.enrich_content_with_usage(results_dict)

        response: ContentGetAllResponse = ContentGetAllResponse(
            results_count=len(enriched_results),
            results=als_responses(BeitragResponse, enriched_results, aufrufer),
            total_records_count=total_count,
        )

        return response
    except Exception as e:
        logger.error(f"Error in /getAll: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)


# Get recent content
@router.get("/recent")
async def get_recent_content(
    aufrufer: Aufrufer = Depends(get_aufrufer),
    limit: int = Query(default=6, ge=1, le=20),
    settings: Settings = Depends(get_settings),
    reference_service: ReferenceService = Depends(get_reference_service),
) -> Dict[str, Any]:
    """
    Get the most recently added content items.
    Returns a mix of commentary and generictext content ordered by creation date.
    """
    try:
        logger.info(f"=== /api/v1/content/recent endpoint called ===")
        logger.debug(f"Request parameters: limit={limit}")

        repository_factory = QdrantRepositoryFactory()

        # Get recent commentary items
        logger.debug("Fetching recent commentaries from repository...")
        commentary_repository = repository_factory.create_commentary_repository(
            settings
        )
        recent_commentaries = await commentary_repository.get_recent(limit=limit)
        logger.info(f"Found {len(recent_commentaries)} commentary items")

        if logger.isEnabledFor(logging.DEBUG):
            for idx, comm in enumerate(recent_commentaries):
                logger.debug(
                    f"  Commentary {idx+1}: ID={comm.id}, title={comm.title}, created={comm.created}"
                )

        # Get recent generictext items
        logger.debug("Fetching recent generictexts from repository...")
        generictext_repository = repository_factory.create_generic_text_repository(
            settings
        )
        recent_generictexts = await generictext_repository.get_recent(limit=limit)
        logger.info(f"Found {len(recent_generictexts)} generictext items")

        if logger.isEnabledFor(logging.DEBUG):
            for idx, gen in enumerate(recent_generictexts):
                logger.debug(
                    f"  Generictext {idx+1}: ID={gen.id}, title={gen.title}, created={gen.created}"
                )

        # Combine and sort by created date
        all_recent = []

        # Convert commentary items to dict with type indicator and enrich references
        for item in recent_commentaries:
            await reference_service.herkunft_ergaenzen(item)
            item_dict = item.model_dump()
            item_dict["result_type"] = "commentary"
            all_recent.append(item_dict)

        # Convert generictext items to dict with type indicator and enrich references
        for item in recent_generictexts:
            await reference_service.herkunft_ergaenzen(item)
            item_dict = item.model_dump()
            item_dict["result_type"] = "generictext"
            all_recent.append(item_dict)

        # Sort combined list by created date (newest first)
        all_recent.sort(key=lambda x: x["created"], reverse=True)

        # Take only the requested limit
        all_recent = all_recent[:limit]

        logger.debug(
            f"Combined and sorted {len(all_recent)} total items (limited to {limit})"
        )

        # Enrich with usage statistics
        logger.debug("Enriching content with usage statistics...")
        usage_service = get_usage_service()
        angereichert = usage_service.enrich_content_with_usage(all_recent)
        # Je Eintrag das Response-DTO seines Typs; result_type gehoert nicht zum
        # Beitrag und kommt danach wieder dazu.
        antworten = fuer_aufrufer(
            [
                NEUESTE.get(e["result_type"], BeitragResponse).model_validate(e)
                for e in angereichert
            ],
            aufrufer,
        )
        enriched_results = [
            {**antwort.model_dump(mode="json"), "result_type": e["result_type"]}
            for e, antwort in zip(angereichert, antworten)
        ]

        logger.info(f"/recent endpoint returning {len(enriched_results)} results")

        if logger.isEnabledFor(logging.DEBUG):
            result_ids = [item.get("id", "unknown") for item in enriched_results]
            logger.debug(f"Returning content IDs: {result_ids}")

        return {"results_count": len(enriched_results), "results": enriched_results}

    except Exception as e:
        logger.error(f"Error in /recent endpoint: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)


# Die Antwort je Beitragstyp, wie getById des Typs sie liefert. Aussage und Herkunft
# fehlen: Sie sind keine Beitraege (ADR 0002) und haben keine eigene Adresse.
ANSICHT = {
    ContentType.COMMENTARY: KommentarResponse,
    ContentType.GENERIC_TEXT: HintergrundinfoResponse,
    ContentType.POST: PostResponse,
    ContentType.IMAGE: BildResponse,
}

BeitragAnsicht = Union[
    KommentarResponse, HintergrundinfoResponse, PostResponse, BildResponse
]


# response_model=None: Ein Union-Modell liesse Pydantic den Typ raten; die Antwort ist
# schon das DTO ihres Typs, und das DTO ist die Feldauswahl.
@router.get("/beitrag/{beitrag_id}", response_model=None)
async def beitrag_ansehen(
    beitrag_id: uuid.UUID,
    laden: BeitragLader = Depends(get_beitrag_laden),
    commentary_service: BaseContentService = Depends(get_commentary_service),
    generic_text_service: BaseContentService = Depends(get_generic_text_service),
    post_service: BaseContentService = Depends(get_post_service),
    image_service: BaseContentService = Depends(get_image_service),
    reference_service: ReferenceService = Depends(get_reference_service),
    aufrufer: Aufrufer = Depends(get_aufrufer),
) -> BeitragAnsicht:
    """
    Ein Beitrag jedes Typs unter seiner eigenen Adresse (/beitrag/:id, #300).

    Die Adresse traegt nur die ID; den Typ liest erst das aggregierte Repository,
    den Beitrag mit seinen Feldern dann der Dienst seines Typs. Herkunft und Nutzung
    wie in /recent. Oeffentlich wie die Suche (BFF: EndpointPolicy.AllowAnonymous).

    404 fuer gesperrte, geloeschte und nie vorhandene Beitraege, auch fuer Admins:
    Gesperrtes finden sie ueber die Moderation (GLOSSARY.md, "Gesperrt").
    """
    dienste = {
        ContentType.COMMENTARY: commentary_service,
        ContentType.GENERIC_TEXT: generic_text_service,
        ContentType.POST: post_service,
        ContentType.IMAGE: image_service,
    }
    try:
        allgemein = await laden(beitrag_id)
        typ = allgemein.content_type if allgemein else None
        if typ not in ANSICHT:
            raise HTTPException(status_code=404, detail="Beitrag nicht gefunden.")
        # ValueError: zwischen beiden Lesungen gesperrt oder geloescht.
        beitrag = await dienste[typ].get(beitrag_id)
        await reference_service.herkunft_ergaenzen(beitrag)
        [mit_nutzung] = get_usage_service().enrich_content_with_usage(
            [beitrag.model_dump()]
        )
        return als_responses(ANSICHT[typ], [mit_nutzung], aufrufer)[0]
    except HTTPException:
        raise
    except (BeitragUnlesbar, ValidationError):
        # Kaputt, nicht abwesend; geloggt hat das Repository (beitrag_laden.py).
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)
    except ValueError:
        raise HTTPException(status_code=404, detail="Beitrag nicht gefunden.")
    except Exception as e:
        logger.error(f"Error in /beitrag: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)


@router.delete("/{beitrag_id}", status_code=204)
async def beitrag_loeschen(
    beitrag_id: uuid.UUID,
    x_user: Optional[str] = Header(default=None),
    service: BeitragLoeschenService = Depends(get_beitrag_loeschen_service),
) -> Response:
    """
    Der Autor loescht seinen Beitrag: Zustand "geloescht", der Beitrag bleibt
    gespeichert (#250). Endgueltig entfernen nur Admins nach dem Loeschkonzept
    (DELETE /api/v1/moderation/content/..., docs/LOESCHKONZEPT.md).

    404 auch fuer gesperrte und schon geloeschte Beitraege: Fuer den Autor sind
    sie nicht da.
    """
    if not angemeldet(x_user):
        raise HTTPException(status_code=401, detail="Dafür musst du angemeldet sein.")

    try:
        ergebnis = await service.loeschen(beitrag_id, x_user)
    except VerweiseNichtEntfernt:
        # Wie beim Admin-Weg: kein Erfolg melden, der Beitrag ist noch sichtbar (#294).
        raise HTTPException(
            status_code=500,
            detail="Der Beitrag ist nicht gelöscht; bitte erneut versuchen.",
        )
    if ergebnis is LoeschErgebnis.NICHT_DA:
        raise HTTPException(status_code=404, detail="Beitrag nicht gefunden.")
    if ergebnis is LoeschErgebnis.NICHT_AUTOR:
        raise HTTPException(
            status_code=403, detail="Löschen kann nur der Autor des Beitrags."
        )
    return Response(status_code=204)
