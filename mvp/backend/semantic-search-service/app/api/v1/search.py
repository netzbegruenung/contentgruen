from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List, Optional

from core.config import settings
from core.logging import get_logger

# Search scoring constants live in the orchestrator (single source of truth);
# re-exported here for backwards compatibility / external references.
from services.search.search_orchestrator import (
    SearchOrchestrator,
    ContentTypeSearchSpec,
    MINIMUM_SCORE_THRESHOLD,
    DIRECT_MATCH_PENALTY,
    STATEMENT_WEIGHT,
    RELEVANCE_WEIGHT,
)

from auth.authorization import require_auth
from dependencies import (
    get_commentary_service,
    get_generic_text_service,
    get_image_service,
    get_post_service,
    get_statement_service,
    get_reference_service,
    get_voting_service,
)
from services.usage_tracking_service import get_usage_service
from services.voting_service import VotingService
from services.search_tracking_service import get_search_tracking_service
from services.polarity_filter_service import get_polarity_filter_service
from services.keyword_overlap_service import get_keyword_overlap_service
from dtos.search import (
    CommentarySearchResult,
    GenericTextSearchResult,
    ImageSearchResult,
    PostSearchResult,
    SearchByTextRequest,
    SearchResponse,
)
from domain.models.content_type import ContentType
from domain.models.statement import Statement, StatementSearchResult
from services.content.commentary_service import CommentaryService
from services.content.statement_service import StatementService
from services.content.generic_text_service import GenericTextService
from services.content.reference_service import ReferenceService
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin, SEARCH_QUERY_AUTHOR

logger = get_logger(__name__)

router = APIRouter()


# Test endpoint to check if the API is running
@router.get("/")
async def read_test():
    return {"message": "This is a test endpoint"}


# Searches for content in various indexes using similarity search
# later to probably be split up in specific seach operations
# returns analysis of input content (=identified statement), topics (TBD), commentaries & generictext snippets
@router.post("/searchByText", response_model=SearchResponse)
async def search_by_text(
    request: SearchByTextRequest,
    statement_service: StatementService = Depends(get_statement_service),
    commentary_service: CommentaryService = Depends(get_commentary_service),
    generictext_service: GenericTextService = Depends(get_generic_text_service),
    post_service=Depends(get_post_service),
    image_service=Depends(get_image_service),
    reference_service: ReferenceService = Depends(get_reference_service),
    voting_service: VotingService = Depends(get_voting_service),
    x_user: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
) -> SearchResponse:
    try:
        logger.info(
            f"🔍 Search request: query='{request.query_text}', limit={request.limit}"
        )

        # Handle both authenticated and anonymous users
        if x_user:
            validated_user = require_auth(x_user, operation="read")
            logger.debug(f"👤 Authorized user: {validated_user}")
        else:
            validated_user = "anonymous"
            logger.debug("👤 Anonymous user search")

        # Check that request is valid
        if request.query_text is None or request.query_text == "":
            raise HTTPException(status_code=400, detail="query_text cannot be empty")
        if request.limit is None or request.limit < 1 or request.limit > 20:
            raise HTTPException(
                status_code=400,
                detail="limit must be a positive integer between 1 and 20",
            )

        # Qdrant handles concurrent searches correctly without needing locks
        statement_was_new = False
        statement_id = None
        statement_text = request.query_text

        # Add the query text to the statement index (if new) - statements don't require review and are released directly
        statement: Statement = Statement(
            text=request.query_text,
            replysuggestions=[],
        )
        try:
            # SEARCH_QUERY trennt die Suchanfrage vom kuratierten Material, und der
            # Autor ist ein Systemwert: wer gesucht hat, haengt nicht am Statement.
            statement_was_new, statement_id, statement_text = (
                await statement_service.add_statement(
                    statement,
                    SEARCH_QUERY_AUTHOR,
                    ContentStatus.RELEASED_INTERNAL,
                    ContentOrigin.SEARCH_QUERY,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to auto-create statement during search: {e}")
            # Continue with search even if auto-creation fails

        # Business logic: Query most similar statements that do contain replysuggestions from the statement index
        statement_index_results: List[StatementSearchResult] = (
            await statement_service.search_statements(
                request.query_text,
                settings.statement_search_limit,
                settings.min_reply_suggestions_for_search,
            )
        )
        logger.debug(
            f"📊 Statement search results: {len(statement_index_results)} items"
        )

        # Apply polarity filtering to statement results
        polarity_filter = get_polarity_filter_service(
            enable_filtering=settings.enable_polarity_filtering
        )
        statement_index_results, polarity_metadata = (
            polarity_filter.analyze_and_filter_statement_results(
                query_text=request.query_text,
                statement_results=statement_index_results,
                get_text_fn=lambda r: r.text,
            )
        )
        logger.debug(
            f"📊 After polarity filtering: {len(statement_index_results)} statement results"
        )

        # Apply keyword overlap boosting to statement results
        keyword_overlap_service = get_keyword_overlap_service(
            enable_boosting=settings.enable_keyword_overlap_boost,
            boost_strength=settings.keyword_overlap_boost_strength,
        )
        statement_index_results, keyword_metadata = (
            keyword_overlap_service.analyze_and_boost_results(
                query_text=request.query_text,
                results=statement_index_results,
                get_text_fn=lambda r: r.text,
            )
        )
        logger.debug(
            f"📊 After keyword overlap boosting: {len(statement_index_results)} statement results"
        )

        # Run the type-agnostic search pipeline over the registered content types.
        specs = [
            ContentTypeSearchSpec(
                content_type=ContentType.COMMENTARY,
                service=commentary_service,
                result_cls=CommentarySearchResult,
                result_field="commentary_result",
            ),
            ContentTypeSearchSpec(
                content_type=ContentType.GENERIC_TEXT,
                service=generictext_service,
                result_cls=GenericTextSearchResult,
                result_field="generictext_result",
            ),
            ContentTypeSearchSpec(
                content_type=ContentType.POST,
                service=post_service,
                result_cls=PostSearchResult,
                result_field="post_result",
            ),
            *(
                [
                    ContentTypeSearchSpec(
                        content_type=ContentType.IMAGE,
                        service=image_service,
                        result_cls=ImageSearchResult,
                        result_field="image_result",
                    )
                ]
                if image_service is not None
                else []
            ),
        ]
        orchestrator = SearchOrchestrator(
            specs,
            reference_service=reference_service,
            usage_service=get_usage_service(),
            voting_service=voting_service,
        )

        # Phase 1: statement-based reply retrieval. Phase 2: direct-search fallback.
        await orchestrator.collect_statement_based(
            statement_index_results, request.limit, polarity_metadata
        )
        await orchestrator.collect_direct(request.query_text, request.limit)

        # Phase 3: sort/truncate, then enrich with usage counts and (if any) user votes.
        orchestrator.sort_and_truncate(request.limit)
        orchestrator.enrich_with_usage()
        if validated_user and validated_user != "anonymous":
            orchestrator.apply_user_votes(validated_user)

        commentary_search_results = orchestrator.results_for(ContentType.COMMENTARY)
        generictext_search_results = orchestrator.results_for(ContentType.GENERIC_TEXT)
        post_search_results = orchestrator.results_for(ContentType.POST)
        image_search_results = orchestrator.results_for(ContentType.IMAGE)

        logger.debug(
            f"🎯 Final results: {len(commentary_search_results)} commentaries, "
            f"{len(generictext_search_results)} generictexts"
        )

        response = SearchResponse(
            query_was_newly_added_as_statement=statement_was_new,
            statement_id=str(statement_id),
            statement_text=statement_text,
            commentary_search_results_count=len(commentary_search_results),
            commentary_search_results=commentary_search_results,
            generictext_search_results_count=len(generictext_search_results),
            generictext_search_results=generictext_search_results,
            post_search_results_count=len(post_search_results),
            post_search_results=post_search_results,
            image_search_results_count=len(image_search_results),
            image_search_results=image_search_results,
        )

        # Track search event for metrics (fire-and-forget, don't block response)
        try:
            search_tracking_service = get_search_tracking_service()
            total_results = (
                len(commentary_search_results)
                + len(generictext_search_results)
                + len(post_search_results)
                + len(image_search_results)
            )

            # Neither the query text nor the client IP is handed on: the search
            # text was stored in full without ever being read back, and the IP
            # hash was written but never evaluated. The user or session id is
            # turned into a daily pseudonym inside the tracking service.
            search_tracking_service.track_search(
                results_count=total_results,
                session_id=x_session_id,
                user_id=validated_user if validated_user != "anonymous" else None,
            )
        except Exception as e:
            # Don't fail the search if tracking fails
            logger.warning(f"Failed to track search event: {e}")

        return response

    except HTTPException:
        # Intentional client errors (e.g. invalid limit) must surface with their own
        # status code, not be re-wrapped as a 500 by the catch-all below.
        raise
    except Exception as e:
        logger.error(f"❌ Error in searchByText: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# searchByTopic(topic)
