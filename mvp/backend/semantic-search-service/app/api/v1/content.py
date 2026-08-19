from fastapi import APIRouter, HTTPException, Depends, Query, Header
from typing import List, Optional, Dict, Any
import logging

from dependencies import get_settings, get_reference_service
from dtos.content import (
    ContentGetAllResponse,
    SearchContentByTextRequest,
    ContentSearchResponse,
)
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from domain.models.content import ContentDbEntry, ContentSearchResult
from core.config import Settings
from services.usage_tracking_service import get_usage_service
from services.content.reference_service import ReferenceService

router = APIRouter()
logger = logging.getLogger(__name__)


# Test endpoint to check if the API is running
@router.get("/")
async def read_test():
    return {"message": "This is a test endpoint"}


# Retrieves all content from the index
@router.get("/getAll")
async def get_all(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    settings: Settings = Depends(get_settings),
) -> ContentGetAllResponse:
    try:
        print("/getAll was called")

        offset = (page - 1) * page_size
        repository_factory = QdrantRepositoryFactory()
        content_repository = repository_factory.create_content_repository(settings)
        content_index_results: List[ContentDbEntry] = await content_repository.getAll(
            limit=page_size, offset=offset
        )
        total_count = await content_repository.count()

        print(f"/getAll got {len(content_index_results)} results from content_index")

        # Enrich results with usage statistics
        usage_service = get_usage_service()
        results_dict = [item.model_dump() for item in content_index_results]
        enriched_results = usage_service.enrich_content_with_usage(results_dict)

        response: ContentGetAllResponse = ContentGetAllResponse(
            results_count=len(enriched_results),
            results=enriched_results,
            total_records_count=total_count,
        )

        return response
    except Exception as e:
        print("Error in /getAll: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# Searches for content in the content_index using similarity search
@router.post("/searchContent", response_model=ContentSearchResponse)
async def search_content(
    request: SearchContentByTextRequest,
    settings: Settings = Depends(get_settings),
) -> ContentSearchResponse:
    try:
        print("/searchContent was called, request: ", request)

        repository_factory = QdrantRepositoryFactory()
        content_repository = repository_factory.create_content_repository(settings)
        content_index_results: List[ContentSearchResult] = (
            await content_repository.search(request.query_text, request.limit)
        )
        print("/searchContent content_index_results: ", content_index_results)

        # Enrich results with usage statistics
        usage_service = get_usage_service()
        results_dict = [item.model_dump() for item in content_index_results]
        enriched_results = usage_service.enrich_content_with_usage(results_dict)

        response: ContentSearchResponse = ContentSearchResponse(
            results=enriched_results
        )

        return response
    except Exception as e:
        print("Error in search_content: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# Get recent content
@router.get("/recent")
async def get_recent_content(
    x_user: Optional[str] = Header(default="anonymous"),
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
        logger.debug(f"Request parameters: limit={limit}, user={x_user}")

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
            # Enrich references with actual text
            if item.references:
                for ref in item.references:
                    try:
                        reference_data = await reference_service.get(ref.reference_id)
                        if reference_data:
                            ref.reference_text = reference_data.reference_string
                            # Notiz dieses Beitrags vor globalem Referenztext.
                            ref.reference_description = (
                                getattr(ref, "description", None) or reference_data.text
                            )
                            logger.debug(
                                f"Enriched reference {ref.reference_id} with URL and description"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to fetch reference {ref.reference_id}: {e}"
                        )

            item_dict = item.model_dump()
            item_dict["result_type"] = "commentary"
            all_recent.append(item_dict)

        # Convert generictext items to dict with type indicator and enrich references
        for item in recent_generictexts:
            # Enrich references with actual text
            if item.references:
                for ref in item.references:
                    try:
                        reference_data = await reference_service.get(ref.reference_id)
                        if reference_data:
                            ref.reference_text = reference_data.reference_string
                            # Notiz dieses Beitrags vor globalem Referenztext.
                            ref.reference_description = (
                                getattr(ref, "description", None) or reference_data.text
                            )
                            logger.debug(
                                f"Enriched reference {ref.reference_id} with URL and description"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to fetch reference {ref.reference_id}: {e}"
                        )

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
        enriched_results = usage_service.enrich_content_with_usage(all_recent)

        logger.info(f"/recent endpoint returning {len(enriched_results)} results")

        if logger.isEnabledFor(logging.DEBUG):
            result_ids = [item.get("id", "unknown") for item in enriched_results]
            logger.debug(f"Returning content IDs: {result_ids}")

        return {"results_count": len(enriched_results), "results": enriched_results}

    except Exception as e:
        logger.error(f"Error in /recent endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
