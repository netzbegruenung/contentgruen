from typing import List
from domain.models.zeit import utc_jetzt
from fastapi import APIRouter, HTTPException, Depends, Header, Query
import datetime
import logging
import uuid
from uuid import UUID

from dependencies import (
    get_aufrufer,
    get_aussage_themen_service,
    get_post_service,
    get_statement_service,
    require_art9_einwilligung,
)
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
from services.beitrag_fuer_aufrufer import Aufrufer, als_responses
from dtos.beitrag import PostResponse, PostTreffer
from domain.models.content_type import ContentType
from services.antwort_auf import als_antwort_verknuepfen
from services.aussage_themen_service import AussageThemenService
from services.content.statement_service import StatementService
from core.fehler import INTERNER_FEHLER, UNGUELTIGE_ANFRAGE, Validierungsfehler

router = APIRouter()

# Gewicht der Verknuepfung, wenn die Person die Aussage selbst nennt (#619); wie
# beim Kommentar (api/v1/commentary.py). Gerankt wird je Beitragstyp.
POST_RELEVANZ = 1.0
logger = logging.getLogger(__name__)


# Retrieve a single post by its UUID
@router.get("/getById", response_model=PostResponse)
async def get_by_id(
    post_id: UUID = Query(..., description="The UUID of the post to retrieve"),
    post_service: BaseContentService = Depends(get_post_service),
    aufrufer: Aufrufer = Depends(get_aufrufer),
) -> PostResponse:
    try:
        # The repository contract is raise-on-missing (ValueError), not return-None,
        # so a missing id must be mapped to 404 here rather than relying on `post is None`.
        post = await post_service.get(post_id)
        return als_responses(PostResponse, [post], aufrufer)[0]
    except HTTPException:
        raise
    except ValueError as e:
        logger.info(f"Post with id {post_id} not found: {type(e).__name__}")
        raise HTTPException(status_code=404, detail=f"Post with id {post_id} not found")
    except Exception as e:
        logger.error(f"Error fetching post with id {post_id}: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)


# Retrieve all posts from the index
@router.get("/getAll")
async def get_all(
    post_service: BaseContentService = Depends(get_post_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    aufrufer: Aufrufer = Depends(get_aufrufer),
) -> PostGetAllResponse:
    try:
        offset = (page - 1) * page_size
        results: List[PostDbEntry] = await post_service.get_all(
            limit=page_size, offset=offset
        )
        return PostGetAllResponse(
            results_count=len(results),
            results=als_responses(PostResponse, results, aufrufer),
            total_records_count=await post_service.count(),
        )
    except Exception as e:
        logger.error(f"Error in /getAll: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)


# Search posts in the post index using similarity search
@router.post("/searchPost", response_model=PostSearchResponse)
async def search_post(
    request: SearchPostByTextRequest,
    post_service: BaseContentService = Depends(get_post_service),
    aufrufer: Aufrufer = Depends(get_aufrufer),
) -> PostSearchResponse:
    try:
        results = await post_service.search(request.query_text, request.limit)
        return PostSearchResponse(results=als_responses(PostTreffer, results, aufrufer))
    except Exception as e:
        logger.error(f"Error in search_post: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)


# Add a new post to the post index
@router.post(
    "/addPost",
    response_model=AddPostResponse,
    dependencies=[Depends(require_art9_einwilligung)],
)
async def add_post(
    request: AddPostRequest,
    post_service: BaseContentService = Depends(get_post_service),
    statement_service: StatementService = Depends(get_statement_service),
    themen_service: AussageThemenService = Depends(get_aussage_themen_service),
    x_user: str = Header(...),
) -> AddPostResponse:
    try:
        if not x_user:
            raise HTTPException(status_code=400, detail="X-User header missing")

        now = utc_jetzt()
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
            cc0_wortlaut=request.cc0_wortlaut,
        )
        # Fall back to the title for the embedded text if the body is empty.
        if not entry.text:
            entry.text = entry.title

        post_id = await post_service.add(entry)
        # Mit Aussage haengt der Post danach als Antwort an ihr (#619); scheitert das,
        # bleibt er gespeichert, und verknuepft ist False.
        antwort_auf = await als_antwort_verknuepfen(
            request,
            post_id,
            ContentType.POST,
            POST_RELEVANZ,
            x_user,
            statement_service,
            themen_service,
        )
        return AddPostResponse(id=post_id, **antwort_auf.model_dump())

    except HTTPException:
        raise
    except Validierungsfehler as e:
        logger.error(f"Validation error in add_post: {type(e).__name__}")
        raise HTTPException(status_code=400, detail=e.antworttext)
    except ValueError as e:
        logger.error(f"Validation error in add_post: {type(e).__name__}")
        raise HTTPException(status_code=400, detail=UNGUELTIGE_ANFRAGE)
    except Exception as e:
        logger.error(f"Unexpected error in add_post: {type(e).__name__}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while adding the post. Please try again later.",
        )
