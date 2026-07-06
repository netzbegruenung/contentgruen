from typing import List
from fastapi import APIRouter, HTTPException, Depends, Header, Query
import datetime
import logging
import uuid
from uuid import UUID

from dependencies import get_image_service, get_caption_suggestion_service
from dtos.image import (
    AddImageRequest,
    ImageGetAllResponse,
    SuggestCaptionRequest,
    SuggestCaptionResponse,
)
from services.content.base_content_service import BaseContentService
from services.vision.caption_suggestion_service import CaptionSuggestionService
from domain.models.image import ImageDbEntry
from domain.models.author_entry import AuthorEntry
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def read_test():
    return {"message": "This is a test endpoint"}


@router.get("/getById")
async def get_by_id(
    image_id: UUID = Query(..., description="The UUID of the image to retrieve"),
    image_service: BaseContentService = Depends(get_image_service),
):
    try:
        image = await image_service.get(image_id)
        return image
    except HTTPException:
        raise
    except ValueError as e:
        logger.info(f"Image with id {image_id} not found: {e}")
        raise HTTPException(status_code=404, detail=f"Image with id {image_id} not found")
    except Exception as e:
        logger.error(f"Error fetching image with id {image_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/getAll")
async def get_all(
    image_service: BaseContentService = Depends(get_image_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ImageGetAllResponse:
    try:
        offset = (page - 1) * page_size
        results: List[ImageDbEntry] = await image_service.get_all(
            limit=page_size, offset=offset
        )
        return ImageGetAllResponse(
            results_count=len(results),
            results=results,
            total_records_count=await image_service.count(),
        )
    except Exception as e:
        logger.error(f"Error in /getAll: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/addImage")
async def add_image(
    request: AddImageRequest,
    image_service: BaseContentService = Depends(get_image_service),
    x_user: str = Header(...),
):
    """
    Create an image entry.

    Phase A (caption provided): stores immediately at PENDING_REVIEW. Returns 201.
    Phase B (no caption): stores at PENDING_DESCRIPTION for async worker processing.
    Returns 202 Accepted with the assigned id and status.
    """
    try:
        image_input = request.image
        caption_provided = bool(image_input.text and image_input.text.strip())

        now = datetime.datetime.now(datetime.timezone.utc)
        initial_status = (
            ContentStatus.PENDING_REVIEW
            if caption_provided
            else ContentStatus.PENDING_DESCRIPTION
        )

        entry = ImageDbEntry(
            **image_input.model_dump(),
            id=uuid.uuid4(),
            created=now,
            last_modified=now,
            original_author=x_user,
            last_modified_by=x_user,
            authors=[AuthorEntry(name=x_user)],
            status=initial_status,
            origin=ContentOrigin.MANUALLY_CREATED,
        )

        image_id = await image_service.add(entry)

        if caption_provided:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=201,
                content={"id": str(image_id)},
            )
        else:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=202,
                content={"id": str(image_id), "status": "pending_description"},
            )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in add_image: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in add_image: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while adding the image. Please try again later.",
        )


@router.post("/suggestCaption", response_model=SuggestCaptionResponse)
async def suggest_caption(
    request: SuggestCaptionRequest,
    caption_service: CaptionSuggestionService = Depends(get_caption_suggestion_service),
    x_user: str = Header(...),
) -> SuggestCaptionResponse:
    """Generate an AI caption suggestion for an image URL (authenticated, rate-limited via middleware)."""
    if not request.image_url or not request.image_url.strip():
        raise HTTPException(status_code=422, detail="image_url must not be empty")

    try:
        caption = await caption_service.suggest_caption(request.image_url)
        return SuggestCaptionResponse(suggested_caption=caption)
    except Exception as e:
        logger.error(f"Caption suggestion failed for URL {request.image_url[:80]}: {e}")
        raise HTTPException(
            status_code=502,
            detail="Vorschlag konnte nicht erstellt werden. Bitte gib eine Beschriftung manuell ein.",
        )
