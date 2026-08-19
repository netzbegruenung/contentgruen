from typing import List
from fastapi import APIRouter, HTTPException, Depends, Header
import datetime
import logging

from dependencies import get_generic_text_service, get_reference_service
from dtos.generic_text import (
    AddGenericTextRequest,
    AddGenericTextResponse,
    GenericTextGetAllResponse,
    GenericTextSearchResponse,
    SearchGenericTextByTextRequest,
)
from services.content.generic_text_service import GenericTextService
from services.content.reference_service import ReferenceService
from domain.models.generic_text import GenericTextDbEntry, GenericTextReference
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


# Endpoint to search generic text by UUID
@router.get("/getById")
async def get_by_id(
    generic_text_id: UUID = Query(
        ..., description="The UUID of the generic text to retrieve"
    ),
    generic_text_service: GenericTextService = Depends(get_generic_text_service),
):
    try:
        # Retrieve generic text by ID
        generic_text = await generic_text_service.get(generic_text_id)

        # If no generic text is found, raise a 404 error
        if generic_text is None:
            raise HTTPException(
                status_code=404,
                detail=f"GenericText with id {generic_text_id} not found",
            )

        return generic_text

    except Exception as e:
        print(f"Error fetching generic text with id {generic_text_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Retrieves all generic text from the index
@router.get("/getAll")
async def get_all(
    generic_text_service: GenericTextService = Depends(get_generic_text_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> GenericTextGetAllResponse:
    try:
        print("/getAll was called")

        offset = (page - 1) * page_size
        generic_text_index_results: List[GenericTextDbEntry] = (
            await generic_text_service.get_all(limit=page_size, offset=offset)
        )
        print(
            f"/getAll got {len(generic_text_index_results)} results from generic_text_index"
        )

        response: GenericTextGetAllResponse = GenericTextGetAllResponse(
            results_count=len(generic_text_index_results),
            results=generic_text_index_results,
            total_records_count=await generic_text_service.count(),
        )

        return response
    except Exception as e:
        print("Error in /getAll: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# Searches for generic texts in the generic_text_index using similarity search
@router.post("/searchGenericText", response_model=GenericTextSearchResponse)
async def search_generic_text(
    request: SearchGenericTextByTextRequest,
    generic_text_service: GenericTextService = Depends(get_generic_text_service),
) -> GenericTextSearchResponse:
    try:
        print("/searchGenericText was called, request: ", request)

        generic_text_index_results = await generic_text_service.search(
            request.query_text, request.limit
        )
        print(
            "/searchGenericText generic_text_index_results: ",
            generic_text_index_results,
        )

        response: GenericTextSearchResponse = GenericTextSearchResponse(
            results=generic_text_index_results
        )

        return response
    except Exception as e:
        print("Error in search_generic_text: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# Adds a new generic text to the generic_text_index
@router.post("/addGenericText", response_model=AddGenericTextResponse)
async def add_generic_text(
    request: AddGenericTextRequest,
    generic_text_service: GenericTextService = Depends(get_generic_text_service),
    reference_service: ReferenceService = Depends(get_reference_service),
    x_user: str = Header(...),
) -> AddGenericTextResponse:
    try:
        print("/addGenericText was called, request: ", request)

        if not x_user:
            raise HTTPException(status_code=400, detail="X-User header missing")

        print(f"X-User header: {x_user}")

        # Handle references first if provided
        new_reference_ids = []
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
                    new_reference_ids.append(reference_id)
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
                    new_reference_ids.append(reference_id)
                    logger.info(
                        f"Created new reference {reference_id}: {ref_input.reference_string}"
                    )

        # Create generictext references list for the model
        generictext_references = []
        for reference_id in new_reference_ids:
            generictext_reference = GenericTextReference(
                reference_id=reference_id, created=datetime.datetime.now()
            )
            generictext_references.append(generictext_reference)

        # Add references to the generic text model
        request.generictext.references = generictext_references

        # Add generic text to generic_text index - generic texts require review
        success, generic_text_id, text = await generic_text_service.add_generic_text(
            request.generictext,
            x_user,
            NEW_CONTENT_STATUS,
            ContentOrigin.MANUALLY_CREATED,
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to add generic text")

        # Create response object
        response = AddGenericTextResponse(id=generic_text_id)

        return response

    except HTTPException:
        raise
    except ValueError as e:
        print(f"Validation error in add_generic_text: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in add_generic_text: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while adding generic text. Please try again later.",
        )


# getTitleForGenericText()


# getTagsForGenericText()


# getAnalysisForGenericText()
