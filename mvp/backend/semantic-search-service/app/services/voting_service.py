import uuid
from typing import List, Optional, Dict
from sqlalchemy.exc import IntegrityError, OperationalError

from core.logging import get_logger
from domain.models.vote import Vote, VoteCreate, VoteResponse, VoteType
from repositories.vote_repository import VoteRepository

logger = get_logger(__name__)


class VotingService:
    """Service for managing user votes on content items."""

    def __init__(self):
        self.vote_repository = VoteRepository()
        # Ensure the votes table exists
        self.vote_repository.create_votes_table()

    def set_like(self, user_id: str, content_id: uuid.UUID) -> VoteResponse:
        """
        Set a like for a content item. Idempotent operation.
        If user already liked, returns current state.
        If user had disliked, replaces with like.
        """
        try:
            # Always upsert a like - this handles both new and existing votes
            vote = self.vote_repository.upsert_vote(
                user_id=user_id,
                content_id=content_id,
                vote_type=VoteType.LIKE.value,
            )

            logger.info(f"Set like from user {user_id} for content {content_id}")

            return VoteResponse(
                content_id=content_id,
                vote_type=VoteType.LIKE.value,
                message="Like set successfully",
            )

        except IntegrityError as e:
            logger.error(f"Database integrity error setting like: {e}")
            raise ValueError("Vote conflict detected. Please try again.")
        except OperationalError as e:
            logger.error(f"Database connection error setting like: {e}")
            raise ConnectionError("Database temporarily unavailable.")
        except Exception as e:
            logger.error(f"Unexpected error setting like: {e}")
            raise RuntimeError(f"Failed to set like: {str(e)}")

    def remove_like(self, user_id: str, content_id: uuid.UUID) -> VoteResponse:
        """
        Remove a like for a content item. Idempotent operation.
        Only removes if the current vote is a like.
        """
        try:
            existing_vote = self.vote_repository.get_user_vote(user_id, content_id)

            if existing_vote and existing_vote.vote_type == VoteType.LIKE.value:
                self.vote_repository.delete_vote(user_id, content_id)
                logger.info(
                    f"Removed like from user {user_id} for content {content_id}"
                )

            return VoteResponse(
                content_id=content_id,
                vote_type=None,
                message="Like removed successfully",
            )

        except OperationalError as e:
            logger.error(f"Database connection error removing like: {e}")
            raise ConnectionError("Database temporarily unavailable.")
        except Exception as e:
            logger.error(f"Unexpected error removing like: {e}")
            raise RuntimeError(f"Failed to remove like: {str(e)}")

    def set_dislike(self, user_id: str, content_id: uuid.UUID) -> VoteResponse:
        """
        Set a dislike for a content item. Idempotent operation.
        If user already disliked, returns current state.
        If user had liked, replaces with dislike.
        """
        try:
            # Always upsert a dislike - this handles both new and existing votes
            vote = self.vote_repository.upsert_vote(
                user_id=user_id,
                content_id=content_id,
                vote_type=VoteType.DISLIKE.value,
            )

            logger.info(f"Set dislike from user {user_id} for content {content_id}")

            return VoteResponse(
                content_id=content_id,
                vote_type=VoteType.DISLIKE.value,
                message="Dislike set successfully",
            )

        except IntegrityError as e:
            logger.error(f"Database integrity error setting dislike: {e}")
            raise ValueError("Vote conflict detected. Please try again.")
        except OperationalError as e:
            logger.error(f"Database connection error setting dislike: {e}")
            raise ConnectionError("Database temporarily unavailable.")
        except Exception as e:
            logger.error(f"Unexpected error setting dislike: {e}")
            raise RuntimeError(f"Failed to set dislike: {str(e)}")

    def remove_dislike(self, user_id: str, content_id: uuid.UUID) -> VoteResponse:
        """
        Remove a dislike for a content item. Idempotent operation.
        Only removes if the current vote is a dislike.
        """
        try:
            existing_vote = self.vote_repository.get_user_vote(user_id, content_id)

            if existing_vote and existing_vote.vote_type == VoteType.DISLIKE.value:
                self.vote_repository.delete_vote(user_id, content_id)
                logger.info(
                    f"Removed dislike from user {user_id} for content {content_id}"
                )

            return VoteResponse(
                content_id=content_id,
                vote_type=None,
                message="Dislike removed successfully",
            )

        except OperationalError as e:
            logger.error(f"Database connection error removing dislike: {e}")
            raise ConnectionError("Database temporarily unavailable.")
        except Exception as e:
            logger.error(f"Unexpected error removing dislike: {e}")
            raise RuntimeError(f"Failed to remove dislike: {str(e)}")

    def get_user_vote(self, user_id: str, content_id: uuid.UUID) -> Optional[str]:
        """Get the user's vote type for a specific content item."""
        try:
            vote = self.vote_repository.get_user_vote(user_id, content_id)
            return vote.vote_type if vote else None
        except OperationalError as e:
            logger.error(f"Database error getting user vote: {e}")
            return None  # Return None on error to allow graceful degradation
        except Exception as e:
            logger.error(f"Unexpected error getting user vote: {e}")
            return None

    def get_user_votes_for_contents(
        self, user_id: str, content_ids: List[uuid.UUID]
    ) -> Dict[str, str]:
        """
        Get all user votes for a list of content items.
        Returns a dictionary mapping content_id to vote_type.
        """
        try:
            votes = self.vote_repository.get_user_votes(user_id, content_ids)
            return {str(vote.content_id): vote.vote_type for vote in votes}
        except OperationalError as e:
            logger.error(f"Database error getting user votes batch: {e}")
            return {}  # Return empty dict on error to allow graceful degradation
        except Exception as e:
            logger.error(f"Unexpected error getting user votes batch: {e}")
            return {}

    def get_content_vote_stats(self, content_id: uuid.UUID) -> dict:
        """Get voting statistics for a content item."""
        try:
            counts = self.vote_repository.get_vote_counts(content_id)
            score = self.vote_repository.get_content_score(content_id)

            return {
                "content_id": str(content_id),
                "likes": counts["likes"],
                "dislikes": counts["dislikes"],
                "score": score,
            }
        except OperationalError as e:
            logger.error(f"Database error getting vote stats: {e}")
            # Return default stats on error
            return {
                "content_id": str(content_id),
                "likes": 0,
                "dislikes": 0,
                "score": 0.5,
            }
        except Exception as e:
            logger.error(f"Unexpected error getting vote stats: {e}")
            return {
                "content_id": str(content_id),
                "likes": 0,
                "dislikes": 0,
                "score": 0.5,
            }

    def remove_vote(self, user_id: str, content_id: uuid.UUID) -> bool:
        """Remove a user's vote for a content item."""
        try:
            return self.vote_repository.delete_vote(user_id, content_id)
        except OperationalError as e:
            logger.error(f"Database error removing vote: {e}")
            raise ConnectionError(
                "Database temporarily unavailable. Please try again later."
            )
        except Exception as e:
            logger.error(f"Unexpected error removing vote: {e}")
            raise RuntimeError(f"Failed to remove vote: {str(e)}")
