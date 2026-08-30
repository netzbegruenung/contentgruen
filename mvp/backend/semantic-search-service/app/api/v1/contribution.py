from typing import List
from fastapi import APIRouter, Header, HTTPException, Depends, Query

from dependencies import get_settings
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from dtos.contribution import GetContributionsOfUserResponse
from domain.models.content import ContentDbEntry
from core.config import Settings
from core.logging import get_logger

logger = get_logger(__name__)


router = APIRouter()


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
        content_index_results: List[ContentDbEntry] = (
            await content_repository.getByAuthor(
                user_id=x_user,
                limit=page_size,
                offset=offset,
            )
        )
        total_count = await content_repository.getCountByAuthor(user_id=x_user)

        logger.debug(
            f"/getContributionsOfUser got {len(content_index_results)} results"
        )

        response: GetContributionsOfUserResponse = GetContributionsOfUserResponse(
            results_count=len(content_index_results),
            results=content_index_results,
            total_records_count=total_count,
        )

        return response
    except Exception as e:
        logger.error(f"Error in /getContributionsOfUser: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# getPendingContributions()


# getFlaggedContributions()


# postFlagContent()
