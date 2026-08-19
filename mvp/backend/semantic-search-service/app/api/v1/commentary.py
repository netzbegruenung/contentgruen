import datetime
import logging
from fastapi import APIRouter, Header, HTTPException, Depends

from dependencies import get_commentary_service, get_reference_service
from dtos.commentary import (
    AddCommentaryRequest,
    AddCommentaryResponse,
    CommentarySearchResponse,
    SearchCommentaryByTextRequest,
)
from services.content.commentary_service import CommentaryService
from domain.models.commentary import CommentaryReference
from services.content.reference_service import ReferenceService
from domain.models.reference import Reference
from domain.models.content_status import NEW_CONTENT_STATUS
from domain.models.content_origin import ContentOrigin


router = APIRouter()
logger = logging.getLogger(__name__)


# Test endpoint to check if the API is running
@router.get("/")
async def read_test():
    return {"message": "This is a test endpoint"}


from fastapi import Query
from uuid import UUID


# Endpoint to search commentary by UUID
@router.get("/getById")
async def get_by_id(
    commentary_id: UUID = Query(
        ..., description="The UUID of the commentary to retrieve"
    ),
    commentary_service: CommentaryService = Depends(get_commentary_service),
):
    try:
        # Retrieve commentary by ID
        commentary = await commentary_service.get(commentary_id)

        # If no commentary is found, raise a 404 error
        if commentary is None:
            raise HTTPException(
                status_code=404, detail=f"Commentary with id {commentary_id} not found"
            )

        return commentary

    except Exception as e:
        print(f"Error fetching commentary with id {commentary_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Searches for commentaries in the commentary_index using similarity search
@router.post("/searchCommentaries", response_model=CommentarySearchResponse)
async def search_commentaries(
    request: SearchCommentaryByTextRequest,
    commentary_service: CommentaryService = Depends(get_commentary_service),
) -> CommentarySearchResponse:
    try:
        print("/searchCommentaries was called, request: ", request)

        commentary_index_results = await commentary_service.search(
            request.query_text, request.limit
        )
        print(
            "/searchCommentaries commentary_index_results: ", commentary_index_results
        )

        response: CommentarySearchResponse = CommentarySearchResponse(
            results=commentary_index_results
        )

        return response
    except Exception as e:
        print("Error in search_commentaries: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# Adds a new commentary to the commentary_index and for each reference in the request, adds a new reference to the reference_index
@router.post("/addCommentary", response_model=AddCommentaryResponse)
async def add_commentary(
    request: AddCommentaryRequest,
    commentary_service: CommentaryService = Depends(get_commentary_service),
    reference_service: ReferenceService = Depends(get_reference_service),
    x_user: str = Header(...),
) -> AddCommentaryResponse:
    try:
        print("/addCommentary was called, request: ", request)

        if not x_user:
            raise HTTPException(status_code=400, detail="X-User header missing")

        print(f"X-User header: {x_user}")

        # Je Eintrag (reference_id, Notiz): die Notiz gehoert an die Verknuepfung,
        # nicht an die Referenz - dieselbe Quelle kann in einem anderen Beitrag
        # anders beschrieben sein.
        new_references = []
        if request.references is not None and len(request.references) > 0:
            # Create or find reference entries with duplicate detection
            for ref_input in request.references:
                # First check if reference already exists (by exact match)
                existing_reference = await reference_service.find_exact_match(
                    ref_input.reference_string
                )

                if existing_reference:
                    # Reference exists - reuse it
                    reference_id = existing_reference.id
                    logger.info(
                        f"Reusing existing reference {reference_id}: {ref_input.reference_string}"
                    )
                    new_references.append((reference_id, ref_input.description))
                else:
                    # Reference doesn't exist - create new one
                    reference_item = Reference(
                        text=ref_input.description
                        or ref_input.reference_string,  # Use description for semantic indexing, fallback to string
                        reference_string=ref_input.reference_string,
                    )

                    # Add new reference
                    reference_id, was_new, message = (
                        await reference_service.add_reference(
                            reference_item,
                            x_user,
                            NEW_CONTENT_STATUS,
                            ContentOrigin.MANUALLY_CREATED,
                        )
                    )
                    new_references.append((reference_id, ref_input.description))
                    logger.info(
                        f"Created new reference {reference_id}: {ref_input.reference_string}"
                    )

        for reference_id, description in new_references:
            commentary_reference = CommentaryReference(
                reference_id=reference_id,
                created=datetime.datetime.now(),
                description=description,
            )

            if not request.commentary.references:
                request.commentary.references = []

            request.commentary.references.append(commentary_reference)

        # Add commentary to commentary index
        commentary_was_new, commentary_id, commentary_text = (
            await commentary_service.add_commentary(
                request.commentary,
                x_user,
                NEW_CONTENT_STATUS,
                ContentOrigin.MANUALLY_CREATED,
            )
        )

        # Create response object
        response = AddCommentaryResponse(id=commentary_id)

        return response

    except HTTPException:
        raise
    except ValueError as e:
        print(f"Validation error in add_commentary: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in add_commentary: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while adding commentary. Please try again later.",
        )


# getTitleForCommentary()


# getTagsForCommentary()


# getAnalysisForCommentary()
