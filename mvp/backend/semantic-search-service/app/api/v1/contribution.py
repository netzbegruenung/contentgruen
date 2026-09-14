from typing import List
from fastapi import APIRouter, Header, HTTPException, Depends, Query

from dependencies import get_settings
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from dtos.contribution import ContributionEntry, GetContributionsOfUserResponse
from domain.models.content_type import ContentType
from services.usage_tracking_service import get_usage_service
from core.config import Settings
from core.logging import get_logger

logger = get_logger(__name__)


router = APIRouter()

# "Meine Beitraege" zeigt nur ausformulierte Beitraege. Aussagen entstehen beim
# Beitragen nebenbei (das Formular legt die beantwortete Aussage an), Herkunftsangaben
# ueber die Herkunftseingabe - beide gehoeren nicht in die Liste.
AUSFORMULIERTE_TYPEN = [
    ContentType.COMMENTARY.value,
    ContentType.GENERIC_TEXT.value,
    ContentType.IMAGE.value,
    ContentType.POST.value,
]


# Test endpoint to check if the API is running
@router.get("/")
async def read_test():
    return {"message": "This is a test endpoint"}


# getContributionsOfUser()
@router.get("/getContributionsOfUser", response_model=GetContributionsOfUserResponse)
async def search_content(
    x_user: str = Header(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    settings: Settings = Depends(get_settings),
) -> GetContributionsOfUserResponse:
    try:
        logger.debug("/getContributionsOfUser was called")

        if not x_user:
            raise HTTPException(status_code=400, detail="X-User header missing")

        offset = (page - 1) * page_size

        repository_factory = QdrantRepositoryFactory()
        content_repository = repository_factory.create_content_repository(settings)
        beitraege: List[ContributionEntry] = await content_repository.getByAuthor(
            user_id=x_user,
            limit=page_size,
            offset=offset,
            content_types=AUSFORMULIERTE_TYPEN,
            eintrag_modell=ContributionEntry,
        )
        total_count = await content_repository.getCountByAuthor(
            user_id=x_user, content_types=AUSFORMULIERTE_TYPEN
        )

        logger.debug(f"/getContributionsOfUser got {len(beitraege)} results")

        # Die Nutzung liegt in PostgreSQL; nachgetragen wie bei /content/recent.
        mit_nutzung = get_usage_service().enrich_content_with_usage(
            [beitrag.model_dump() for beitrag in beitraege]
        )

        response: GetContributionsOfUserResponse = GetContributionsOfUserResponse(
            results_count=len(mit_nutzung),
            results=mit_nutzung,
            total_records_count=total_count,
        )

        return response
    except Exception as e:
        logger.error(f"Error in /getContributionsOfUser: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# getPendingContributions()


# getFlaggedContributions()


# postFlagContent()
