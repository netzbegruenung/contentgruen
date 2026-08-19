from typing import List
from fastapi import APIRouter, HTTPException, Depends, Header, Query
import datetime
import logging
import uuid
from uuid import UUID

from dependencies import get_post_service
from dtos.post import (
    AddPostRequest,
    AddPostResponse,
    PostGetAllResponse,
    PostSearchResponse,
    SearchPostByTextRequest,
)
from services.content.base_content_service import BaseContentService
from domain.models.post import PostDbEntry
from domain.models.author_entry import AuthorEntry
from domain.models.content_status import NEW_CONTENT_STATUS
from domain.models.content_origin import ContentOrigin

router = APIRouter()
logger = logging.getLogger(__name__)


# Test endpoint to check if the API is running
@router.get("/")
async def read_test():
    return {"message": "This is a test endpoint"}


# Retrieve a single post by its UUID
@router.get("/getById")
async def get_by_id(
    post_id: UUID = Query(..., description="The UUID of the post to retrieve"),
    post_service: BaseContentService = Depends(get_post_service),
):
    try:
        # The repository contract is raise-on-missing (ValueError), not return-None,
        # so a missing id must be mapped to 404 here rather than relying on `post is None`.
        post = await post_service.get(post_id)
        return post
    except HTTPException:
        raise
    except ValueError as e:
        logger.info(f"Post with id {post_id} not found: {e}")
        raise HTTPException(
            status_code=404, detail=f"Post with id {post_id} not found"
        )
    except Exception as e:
        logger.error(f"Error fetching post with id {post_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Retrieve all posts from the index
@router.get("/getAll")
async def get_all(
    post_service: BaseContentService = Depends(get_post_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PostGetAllResponse:
    try:
        offset = (page - 1) * page_size
        results: List[PostDbEntry] = await post_service.get_all(
            limit=page_size, offset=offset
        )
        return PostGetAllResponse(
            results_count=len(results),
            results=results,
            total_records_count=await post_service.count(),
        )
    except Exception as e:
        logger.error(f"Error in /getAll: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Search posts in the post index using similarity search
@router.post("/searchPost", response_model=PostSearchResponse)
async def search_post(
    request: SearchPostByTextRequest,
    post_service: BaseContentService = Depends(get_post_service),
) -> PostSearchResponse:
    try:
        results = await post_service.search(request.query_text, request.limit)
        return PostSearchResponse(results=results)
    except Exception as e:
        logger.error(f"Error in search_post: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Add a new post to the post index
@router.post("/addPost", response_model=AddPostResponse)
async def add_post(
    request: AddPostRequest,
    post_service: BaseContentService = Depends(get_post_service),
    x_user: str = Header(...),
) -> AddPostResponse:
    try:
        if not x_user:
            raise HTTPException(status_code=400, detail="X-User header missing")

        now = datetime.datetime.now()
        post_input = request.post
        # Post ingestion is the type-specific input seam (kept at the router, not in a
        # service clone): build the stored entry and persist via the generic service.
        entry = PostDbEntry(
            **post_input.model_dump(),
            id=uuid.uuid4(),
            created=now,
            last_modified=now,
            original_author=x_user,
            last_modified_by=x_user,
            authors=[AuthorEntry(name=x_user)],
            status=NEW_CONTENT_STATUS,
            origin=ContentOrigin.MANUALLY_CREATED,
        )
        # Fall back to the title for the embedded text if the body is empty.
        if not entry.text:
            entry.text = entry.title

        post_id = await post_service.add(entry)
        return AddPostResponse(id=post_id)

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in add_post: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in add_post: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while adding the post. Please try again later.",
        )
