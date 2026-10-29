from dataclasses import replace
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Header, Request
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
    get_aufrufer,
    get_aussage_themen_service,
    get_commentary_service,
    get_generic_text_service,
    get_image_service,
    get_post_service,
    get_statement_service,
    get_reference_service,
    get_suchen_ohne_treffer_service,
    get_voting_service,
)
from services.usage_tracking_service import get_usage_service
from services.anzeigename_service import angemeldet
from services.beitrag_fuer_aufrufer import Aufrufer
from services.voting_service import VotingService
from services.aussage_themen_service import AussageThemenService
from services.search_tracking_service import (
    get_search_tracking_service,
    tagespseudonym,
)
from services.suchen_ohne_treffer_service import SuchenOhneTrefferService
from services.embeddings.qdrant_embeddings_manager import einbettungen_geteilt
from services.search.search_query_statement import (
    SearchQueryStatementRecorder,
    get_search_query_statement_recorder,
)
from utils.client_identity import derive_client_key
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
from domain.models.statement import StatementSearchResult
from services.content.commentary_service import CommentaryService
from services.content.statement_service import StatementService
from services.content.generic_text_service import GenericTextService
from services.content.reference_service import ReferenceService

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
# Die Suchanfrage wird hier mehrfach gebraucht: Dublettenpruefung und Speichern der
# Aussage, Aussagensuche, Direktsuche. Eingebettet wird sie nur einmal (#304).
@einbettungen_geteilt
async def search_by_text(
    request: SearchByTextRequest,
    http_request: Request,
    statement_service: StatementService = Depends(get_statement_service),
    commentary_service: CommentaryService = Depends(get_commentary_service),
    generictext_service: GenericTextService = Depends(get_generic_text_service),
    post_service=Depends(get_post_service),
    image_service=Depends(get_image_service),
    reference_service: ReferenceService = Depends(get_reference_service),
    voting_service: VotingService = Depends(get_voting_service),
    recorder: SearchQueryStatementRecorder = Depends(
        get_search_query_statement_recorder
    ),
    suchen_ohne_treffer: SuchenOhneTrefferService = Depends(
        get_suchen_ohne_treffer_service
    ),
    aufrufer: Aufrufer = Depends(get_aufrufer),
    themen_service: AussageThemenService = Depends(get_aussage_themen_service),
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
) -> SearchResponse:
    try:
        # Keine Logzeile je Suche: Der Suchtext ist der sensibelste Einzelwert der
        # Plattform, und schon die Uhrzeit der Zeile passte, je Tag durchgezaehlt, zum
        # Anlagezeitpunkt der Aussage aus derselben Suche (#239, #275).

        # Handle both authenticated and anonymous users
        if aufrufer.kennung:
            validated_user = require_auth(aufrufer.kennung, operation="read")
            # Ohne Kennung: zusammen mit der Zeile darueber waere sonst genau die
            # Verknuepfung "wer hat wonach gesucht" im Log, die hier vermieden wird.
            logger.debug("👤 Authorized user search")
        else:
            validated_user = "anonymous"
            logger.debug("👤 Anonymous user search")
        # Ab hier gilt die gepruefte Kennung, fuer Stimmen wie fuer Anzeigenamen.
        aufrufer = replace(aufrufer, kennung=validated_user)

        # Check that request is valid
        if request.query_text is None or request.query_text == "":
            raise HTTPException(status_code=400, detail="query_text cannot be empty")
        if request.limit is None or request.limit < 1 or request.limit > 20:
            raise HTTPException(
                status_code=400,
                detail="limit must be a positive integer between 1 and 20",
            )

        statement_was_new = False
        statement_id = None
        statement_text = request.query_text

        # Die Suchanfrage wird als Aussage aufgenommen (SEARCH_QUERY, Systemautor)
        # - nur hier, das Frontend legt nichts mehr an. Rate-Limit und Sperre je
        # Text: services/search/search_query_statement.py.
        try:
            statement_was_new, statement_id, statement_text = await recorder.anlegen(
                statement_service,
                request.query_text,
                derive_client_key(http_request),
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
        orchestrator.fuer_aufrufer(aufrufer)
        try:
            orchestrator.themen_ergaenzen(themen_service)
        except Exception as e:
            # Ohne Themen bleibt die Suche nutzbar; nur der Filter fehlt dann.
            logger.warning(
                f"Failed to add topics to search results: {type(e).__name__}"
            )

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
            statement_id=str(statement_id) if statement_id is not None else None,
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

        total_results = (
            len(commentary_search_results)
            + len(generictext_search_results)
            + len(post_search_results)
            + len(image_search_results)
        )

        # Suchereignis und "Suchen ohne Treffer" bilden das Tagespseudonym aus
        # derselben Kennung und demselben Zeitpunkt: So ist es fuer beide dasselbe,
        # und Pseudonym und Tag gehoeren zusammen, auch kurz vor Mitternacht.
        user_id = validated_user if angemeldet(validated_user) else None
        jetzt = datetime.now(timezone.utc)

        # Track search event for metrics (fire-and-forget, don't block response)
        try:
            search_tracking_service = get_search_tracking_service()

            # Neither the query text nor the client IP is handed on: the search
            # text was stored in full without ever being read back, and the IP
            # hash was written but never evaluated. The user or session id is
            # turned into a daily pseudonym inside the tracking service.
            search_tracking_service.track_search(
                results_count=total_results,
                session_id=x_session_id,
                user_id=user_id,
                moment=jetzt,
            )
        except Exception as e:
            # Don't fail the search if tracking fails
            logger.warning(f"Failed to track search event: {e}")

        # Kennzahl "Suchen ohne Treffer": gezaehlt an der Aussage zur Suchanfrage,
        # getrennt vom Suchereignis. Das Tagespseudonym dient nur dazu, Personen zu
        # unterscheiden, gespeichert wird es dort nicht. total_results zaehlt nur,
        # was ueber der Schwelle des SearchOrchestrators lag.
        try:
            suchen_ohne_treffer.erfassen(
                statement_id,
                total_results,
                tagespseudonym(user_id=user_id, session_id=x_session_id, moment=jetzt),
                heute=jetzt.date(),
            )
        except Exception as e:
            # Nur der Fehlertyp: SQLAlchemy-Fehler tragen die Parameter, und
            # statement_id neben dem Zeitstempel der Logzeile waere genau der
            # Zeitpunkt, den die Tabelle nicht speichert.
            logger.warning(f"Failed to count search without hits: {type(e).__name__}")

        return response

    except HTTPException:
        # Intentional client errors (e.g. invalid limit) must surface with their own
        # status code, not be re-wrapped as a 500 by the catch-all below.
        raise
    except Exception as e:
        logger.error(f"❌ Error in searchByText: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# searchByTopic(topic)
