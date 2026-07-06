import uuid
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy import text

from core.logging import get_logger
from domain.models.vote import Vote, VoteType
from infrastructure.database.connection import get_app_database

logger = get_logger(__name__)


class VoteRepository:
    """Repository for managing user votes on content items."""

    def __init__(self):
        """Initialize repository with app database connection."""
        self.db = get_app_database()

    def create_votes_table(self):
        """Create the votes table if it doesn't exist."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS votes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(255) NOT NULL,
            content_id UUID NOT NULL,
            vote_type VARCHAR(20) NOT NULL CHECK (vote_type IN ('like', 'dislike')),
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, content_id)
        );

        CREATE INDEX IF NOT EXISTS idx_votes_user_id ON votes(user_id);
        CREATE INDEX IF NOT EXISTS idx_votes_content_id ON votes(content_id);
        CREATE INDEX IF NOT EXISTS idx_votes_user_content ON votes(user_id, content_id);
        """

        with self.db.engine.connect() as conn:
            conn.execute(text(create_table_query))
            conn.commit()
            logger.info("Votes table created or verified")

    def upsert_vote(self, user_id: str, content_id: uuid.UUID, vote_type: str) -> Vote:
        """
        Create or update a vote for a user on a content item.
        If a vote already exists, it will be updated with the new vote type.
        Uses transaction isolation to prevent race conditions.
        """
        query = """
        INSERT INTO votes (user_id, content_id, vote_type, created)
        VALUES (:user_id, :content_id, :vote_type, :created)
        ON CONFLICT (user_id, content_id)
        DO UPDATE SET
            vote_type = EXCLUDED.vote_type,
            created = EXCLUDED.created
        RETURNING id, user_id, content_id, vote_type, created
        """

        with self.db.get_session() as session:
            # Begin transaction with appropriate isolation level
            trans = session.begin()
            try:
                # Set transaction isolation to prevent concurrent modification issues
                session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))

                result = session.execute(
                    text(query),
                    {
                        "user_id": user_id,
                        "content_id": str(content_id),
                        "vote_type": vote_type,
                        "created": datetime.utcnow(),
                    },
                )
                row = result.fetchone()

                if row:
                    trans.commit()
                    return Vote(
                        id=row.id,
                        user_id=row.user_id,
                        content_id=row.content_id,
                        vote_type=row.vote_type,
                        created=row.created,
                    )
                else:
                    trans.rollback()
                    raise Exception("Failed to create or update vote")
            except Exception as e:
                trans.rollback()
                logger.error(f"Transaction failed in upsert_vote: {e}")
                raise

    def delete_vote(self, user_id: str, content_id: uuid.UUID) -> bool:
        """Delete a vote for a user on a content item."""
        query = """
        DELETE FROM votes
        WHERE user_id = :user_id AND content_id = :content_id
        """

        with self.db.get_session() as session:
            result = session.execute(
                text(query), {"user_id": user_id, "content_id": str(content_id)}
            )
            return result.rowcount > 0

    def get_user_vote(self, user_id: str, content_id: uuid.UUID) -> Optional[Vote]:
        """Get a user's vote for a specific content item."""
        query = """
        SELECT id, user_id, content_id, vote_type, created
        FROM votes
        WHERE user_id = :user_id AND content_id = :content_id
        """

        with self.db.get_session() as session:
            result = session.execute(
                text(query), {"user_id": user_id, "content_id": str(content_id)}
            )
            row = result.fetchone()

            if row:
                return Vote(
                    id=row.id,
                    user_id=row.user_id,
                    content_id=row.content_id,
                    vote_type=row.vote_type,
                    created=row.created,
                )
            return None

    def get_user_votes(self, user_id: str, content_ids: List[uuid.UUID]) -> List[Vote]:
        """Get all votes for a user for a list of content items."""
        if not content_ids:
            return []

        # Build IN clause with individual parameters for each UUID
        # This avoids array type issues with SQLAlchemy's text()
        placeholders = [f":content_id_{i}" for i in range(len(content_ids))]
        in_clause = f"({', '.join(placeholders)})"

        query = f"""
        SELECT id, user_id, content_id, vote_type, created
        FROM votes
        WHERE user_id = :user_id AND content_id IN {in_clause}
        """

        # Build parameters dict with individual content_ids
        params = {"user_id": user_id}
        for i, cid in enumerate(content_ids):
            params[f"content_id_{i}"] = str(cid)

        with self.db.get_session() as session:
            result = session.execute(
                text(query),
                params,
            )

            votes = []
            for row in result:
                votes.append(
                    Vote(
                        id=row.id,
                        user_id=row.user_id,
                        content_id=row.content_id,
                        vote_type=row.vote_type,
                        created=row.created,
                    )
                )
            return votes

    def get_vote_counts(self, content_id: uuid.UUID) -> Dict[str, int]:
        """Get the count of likes and dislikes for a content item."""
        query = """
        SELECT
            vote_type,
            COUNT(*) as count
        FROM votes
        WHERE content_id = :content_id
        GROUP BY vote_type
        """

        with self.db.get_session() as session:
            result = session.execute(text(query), {"content_id": str(content_id)})

            counts = {"likes": 0, "dislikes": 0}
            for row in result:
                if row.vote_type == VoteType.LIKE.value:
                    counts["likes"] = row.count
                elif row.vote_type == VoteType.DISLIKE.value:
                    counts["dislikes"] = row.count

            return counts

    def get_content_score(self, content_id: uuid.UUID) -> float:
        """
        Calculate a score for a content item based on votes.
        Returns a value between 0 and 1, where:
        - 0.5 = neutral (no votes or equal likes/dislikes)
        - > 0.5 = more likes than dislikes
        - < 0.5 = more dislikes than likes
        """
        counts = self.get_vote_counts(content_id)
        total_votes = counts["likes"] + counts["dislikes"]

        if total_votes == 0:
            return 0.5

        # Simple ratio: likes / total_votes
        return counts["likes"] / total_votes
