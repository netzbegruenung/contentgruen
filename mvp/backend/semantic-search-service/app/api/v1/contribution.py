from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query

from dependencies import get_aufrufer, get_settings, get_reference_service
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from services.content.reference_service import ReferenceService
from dtos.contribution import (
    ContributionEntry,
    GetContributionsOfUserResponse,
    MeinBeitragResponse,
)
from services.beitrag_fuer_aufrufer import Aufrufer, als_responses
from domain.content_registry import BEITRAGSTYPEN_WERTE
from services.usage_tracking_service import get_usage_service
from core.config import Settings
from core.logging import get_logger

logger = get_logger(__name__)


router = APIRouter()


# Test endpoint to check if the API is running
@router.get("/")
async def read_test():
    return {"message": "This is a test endpoint"}


# getContributionsOfUser(): wessen Beitraege, sagt allein die Anmeldung, nie die Adresse.
@router.get("/getContributionsOfUser", response_model=GetContributionsOfUserResponse)
async def search_content(
    aufrufer: Aufrufer = Depends(get_aufrufer),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    settings: Settings = Depends(get_settings),
    reference_service: ReferenceService = Depends(get_reference_service),
) -> GetContributionsOfUserResponse:
    # Vor dem try: sonst wuerde das 401 unten zu einem 500.
    if not aufrufer.angemeldet:
        raise HTTPException(status_code=401, detail="Dafür musst du angemeldet sein.")
    person = aufrufer.kennung
    try:
        logger.debug("/getContributionsOfUser was called")

        offset = (page - 1) * page_size

        repository_factory = QdrantRepositoryFactory()
        content_repository = repository_factory.create_content_repository(settings)
        beitraege: List[ContributionEntry] = await content_repository.getByAuthor(
            user_id=person,
            limit=page_size,
            offset=offset,
            content_types=BEITRAGSTYPEN_WERTE,
            eintrag_modell=ContributionEntry,
        )
        total_count = await content_repository.getCountByAuthor(
            user_id=person, content_types=BEITRAGSTYPEN_WERTE
        )

        logger.debug(f"/getContributionsOfUser got {len(beitraege)} results")

        # Herkunft wie bei /content/recent aufloesen: im Payload stehen nur die ID der
        # Referenz und die Notiz dieses Beitrags, die volle Karte zeigt die Adresse.
        for beitrag in beitraege:
            for ref in beitrag.references:
                try:
                    referenz = await reference_service.get(ref.reference_id)
                    if referenz:
                        ref.reference_text = referenz.reference_string
                        ref.reference_description = ref.description or referenz.text
                except Exception as e:
                    logger.warning(
                        f"Herkunft {ref.reference_id} nicht lesbar: {type(e).__name__}"
                    )

        # Die Nutzung liegt in PostgreSQL; nachgetragen wie bei /content/recent, dazu
        # der Zuwachs der letzten 7 Tage (#349). Faellt PostgreSQL aus, fehlen nur die
        # Zahlen - die Liste selbst kommt aus Qdrant. Getrennt abgefangen: Scheitert nur
        # der Zuwachs, bleibt die schon gelesene Nutzung stehen.
        mit_nutzung = [beitrag.model_dump() for beitrag in beitraege]
        try:
            mit_nutzung = get_usage_service().enrich_content_with_usage(mit_nutzung)
        except Exception as e:
            logger.warning(
                f"Nutzung fuer Meine Beitraege nicht lesbar, zeige 0: {type(e).__name__}"
            )
            mit_nutzung = [{**eintrag, "usage_count": 0} for eintrag in mit_nutzung]
        try:
            mit_nutzung = get_usage_service().nutzung_letzte_7_tage_nachtragen(
                mit_nutzung
            )
        except Exception as e:
            logger.warning(
                f"Zuwachs fuer Meine Beitraege nicht lesbar, zeige 0: {type(e).__name__}"
            )
            mit_nutzung = [
                {**eintrag, "nutzung_letzte_7_tage": 0} for eintrag in mit_nutzung
            ]
        # Am Kommentar je Fassung (#355); fehlen die Zahlen, bleibt es bei der Summe.
        try:
            mit_nutzung = get_usage_service().nutzung_je_fassung_nachtragen(mit_nutzung)
        except Exception as e:
            logger.warning(
                f"Nutzung je Fassung nicht lesbar, zeige keine: {type(e).__name__}"
            )
            mit_nutzung = [
                {**eintrag, "nutzung_je_fassung": None} for eintrag in mit_nutzung
            ]

        # Nur eigene Beitraege: das Kennzeichen ist immer gesetzt, die Kennung bleibt
        # wie ueberall nur Admins; Bearbeitungshistorie geht nicht nach aussen (#385).
        results = als_responses(MeinBeitragResponse, mit_nutzung, aufrufer)
        response: GetContributionsOfUserResponse = GetContributionsOfUserResponse(
            results_count=len(results),
            results=results,
            total_records_count=total_count,
        )

        return response
    except Exception as e:
        logger.error(
            f"Error in /getContributionsOfUser: {type(e).__name__}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


# getPendingContributions()


# getFlaggedContributions()


# postFlagContent()
