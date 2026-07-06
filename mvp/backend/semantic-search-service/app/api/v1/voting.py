from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, Dict, List
import uuid

from core.logging import get_logger
from auth.authorization import validate_user_id, require_auth
from domain.models.vote import VoteCreate, VoteResponse
from services.voting_service import VotingService
from dependencies import get_voting_service
from middleware.rate_limiter import check_voting_rate_limit

logger = get_logger(__name__)

router = APIRouter()


def get_current_user(x_user: Optional[str] = Header(None)) -> str:
    """Dependency to get and validate the current user from X-User header."""
    if not x_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return require_auth(x_user, operation="write")


@router.put(
    "/content/{content_id}/like",
    response_model=VoteResponse,
    dependencies=[Depends(check_voting_rate_limit)],
)
def set_like(
    content_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    voting_service: VotingService = Depends(get_voting_service),
) -> VoteResponse:
    """
    Set a like for a content item. Idempotent operation.
    If user already liked, returns success with current state.
    If user had disliked, replaces with like.
    """
    logger.info(f"Setting like for content {content_id} by user {user_id}")
    try:
        result = voting_service.set_like(user_id, content_id)
        logger.info(f"Like set successfully: {result}")
        return result
    except ValueError as e:
        logger.warning(f"Like validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting like: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to set like")


@router.delete(
    "/content/{content_id}/like",
    response_model=VoteResponse,
    dependencies=[Depends(check_voting_rate_limit)],
)
def remove_like(
    content_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    voting_service: VotingService = Depends(get_voting_service),
) -> VoteResponse:
    """
    Remove a like for a content item. Idempotent operation.
    If no like exists, returns success with current state.
    """
    logger.info(f"Removing like for content {content_id} by user {user_id}")
    try:
        result = voting_service.remove_like(user_id, content_id)
        logger.info(f"Like removed successfully: {result}")
        return result
    except ConnectionError as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing like: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to remove like")


@router.put(
    "/content/{content_id}/dislike",
    response_model=VoteResponse,
    dependencies=[Depends(check_voting_rate_limit)],
)
def set_dislike(
    content_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    voting_service: VotingService = Depends(get_voting_service),
) -> VoteResponse:
    """
    Set a dislike for a content item. Idempotent operation.
    If user already disliked, returns success with current state.
    If user had liked, replaces with dislike.
    """
    logger.info(f"Setting dislike for content {content_id} by user {user_id}")
    try:
        result = voting_service.set_dislike(user_id, content_id)
        logger.info(f"Dislike set successfully: {result}")
        return result
    except ValueError as e:
        logger.warning(f"Dislike validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting dislike: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to set dislike")


@router.delete(
    "/content/{content_id}/dislike",
    response_model=VoteResponse,
    dependencies=[Depends(check_voting_rate_limit)],
)
def remove_dislike(
    content_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    voting_service: VotingService = Depends(get_voting_service),
) -> VoteResponse:
    """
    Remove a dislike for a content item. Idempotent operation.
    If no dislike exists, returns success with current state.
    """
    logger.info(f"Removing dislike for content {content_id} by user {user_id}")
    try:
        result = voting_service.remove_dislike(user_id, content_id)
        logger.info(f"Dislike removed successfully: {result}")
        return result
    except ConnectionError as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing dislike: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to remove dislike")


@router.get("/content/{content_id}")
def get_user_vote(
    content_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    voting_service: VotingService = Depends(get_voting_service),
) -> dict:
    """Get the current user's vote for a specific content item."""
    try:
        vote_type = voting_service.get_user_vote(user_id, content_id)
        return {
            "content_id": str(content_id),
            "vote_type": vote_type,  # Can be "like", "dislike", or None
        }
    except Exception as e:
        logger.error(f"Error getting user vote: {e}")
        # Return None vote_type if error occurs
        return {"content_id": str(content_id), "vote_type": None}


@router.post("/votes/batch")
def get_user_votes_batch(
    content_ids: List[uuid.UUID],
    user_id: str = Depends(get_current_user),
    voting_service: VotingService = Depends(get_voting_service),
) -> Dict[str, str]:
    """Get the current user's votes for multiple content items."""
    return voting_service.get_user_votes_for_contents(user_id, content_ids)


@router.get("/content/{content_id}/stats")
def get_vote_stats(
    content_id: uuid.UUID, voting_service: VotingService = Depends(get_voting_service)
) -> dict:
    """Get voting statistics for a content item (likes, dislikes, score)."""
    return voting_service.get_content_vote_stats(content_id)


# Legacy endpoint removed - use DELETE /content/{id}/like or /content/{id}/dislike instead
