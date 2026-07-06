from fastapi import APIRouter, Header, HTTPException, Depends, Query
from typing import List
from uuid import UUID
from datetime import datetime
import logging

from dependencies import get_reference_service
from dtos.reference import (
    AddReferenceRequest,
    AddReferenceResponse,
    SearchReferencesRequest,
    SearchReferencesResponse,
    ReferenceSearchItem,
    GetReferenceResponse,
)
from services.content.reference_service import ReferenceService
from domain.models.reference import Reference
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin
from middleware.rate_limiter import (
    check_reference_creation_rate_limit,
    check_reference_search_rate_limit,
)


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def read_test():
    return {"message": "Reference API is running"}


@router.get("/getById", response_model=GetReferenceResponse)
async def get_by_id(
    reference_id: UUID = Query(
        ..., description="The UUID of the reference to retrieve"
    ),
    reference_service: ReferenceService = Depends(get_reference_service),
):
    """Get a reference by its ID"""
    try:
        reference = await reference_service.get(reference_id)

        if reference is None:
            raise HTTPException(
                status_code=404, detail=f"Reference with id {reference_id} not found"
            )

        # Count how many commentaries use this reference
        # This would need to be implemented by searching commentaries
        usage_count = reference.usage_count or 0

        return GetReferenceResponse(
            id=reference.id,
            reference_string=reference.reference_string,
            text=reference.text,
            created=reference.created,
            last_modified=reference.last_modified,
            original_author=reference.original_author,
            usage_count=usage_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching reference with id {reference_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/search",
    response_model=SearchReferencesResponse,
    dependencies=[Depends(check_reference_search_rate_limit)],
)
async def search_references(
    request: SearchReferencesRequest,
    reference_service: ReferenceService = Depends(get_reference_service),
) -> SearchReferencesResponse:
    """Search for references by text"""
    try:
        # Search for references
        results = await reference_service.search(request.query_text, request.limit)

        # Check for exact match
        has_exact_match = False
        exact_match_id = None

        # Check if there's an exact match in the results
        for result in results:
            if result.reference_string == request.query_text:
                has_exact_match = True
                exact_match_id = result.id
                break

        # Convert to response format
        search_items = [
            ReferenceSearchItem(
                id=result.id,
                reference_string=result.reference_string,
                text=result.text,
                created=result.created,
                usage_count=result.usage_count or 0,
                score=result.score,
            )
            for result in results
        ]

        return SearchReferencesResponse(
            results=search_items,
            has_exact_match=has_exact_match,
            exact_match_id=exact_match_id,
        )

    except Exception as e:
        logger.error(f"Error in search_references: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/add",
    response_model=AddReferenceResponse,
    dependencies=[Depends(check_reference_creation_rate_limit)],
)
async def add_reference(
    request: AddReferenceRequest,
    reference_service: ReferenceService = Depends(get_reference_service),
    x_user: str = Header(...),
) -> AddReferenceResponse:
    """Add a new reference or return existing if duplicate (exact match)"""
    try:
        if not x_user:
            raise HTTPException(status_code=400, detail="X-User header missing")

        # Check for exact match first
        existing = await reference_service.find_exact_match(request.reference_string)

        if existing:
            # Reference exists - return its info
            return AddReferenceResponse(
                id=existing.id,
                was_new=False,
                message="Reference already exists",
            )

        # No exact match - create new reference
        reference = Reference(
            text=request.text or request.reference_string,
            reference_string=request.reference_string,
        )

        # Add reference
        reference_id, was_new, message = await reference_service.add_reference(
            reference,
            x_user,
            ContentStatus.PENDING_REVIEW,
            ContentOrigin.MANUALLY_CREATED,
        )

        return AddReferenceResponse(
            id=reference_id,
            was_new=was_new,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in add_reference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Note: check-and-add functionality has been merged into the /add endpoint
