from typing import Optional
import uuid
import datetime

from core.config import Settings
from services.content.base_content_service import BaseContentService
from repositories.interfaces.commentary_repository import (
    ICommentaryRepository,
)
from repositories.interfaces.repository_factory import IRepositoryFactory
from domain.models.commentary import (
    Commentary,
    CommentaryDbEntry,
    CommentarySearchResult,
)
from domain.models.author_entry import AuthorEntry
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin


class CommentaryService(
    BaseContentService[ICommentaryRepository, CommentaryDbEntry, CommentarySearchResult]
):
    def __init__(
        self,
        settings: Settings,
        repository_factory: Optional[IRepositoryFactory] = None,
    ):
        """
        Initialize the CommentaryService with the provided Settings.

        Args:
        - settings: The Settings instance to be used by the Service.
        - repository_factory: Optional repository factory. Defaults to QdrantRepositoryFactory.
        """
        # Use provided factory or default to QdrantRepositoryFactory
        if repository_factory is None:
            from repositories.implementations.qdrant.qdrant_repository_factory import (
                QdrantRepositoryFactory,
            )

            repository_factory = QdrantRepositoryFactory()

        repository = repository_factory.create_commentary_repository(settings)
        content_repository = repository_factory.create_content_repository(settings)

        super().__init__(
            settings,
            repository,
            content_repository,
            CommentaryDbEntry,
            CommentarySearchResult,
        )

    async def _check_commentary_similarity(
        self, commentary_text: str
    ) -> tuple[Optional[float], Optional[uuid.UUID]]:
        """
        Check if a commentary is too similar to existing commentaries.

        Returns:
            - Tuple of (similarity_score, content_id) for most similar commentary, or (None, None)
        """
        print(f"Checking for similar existing commentaries to '{commentary_text}'")

        similar_commentaries = await self.search(commentary_text, limit=1)
        if similar_commentaries and similar_commentaries[0].score:
            return similar_commentaries[0].score, similar_commentaries[0].id
        return None, None

    async def _is_commentary_too_similar(
        self, commentary_text: str
    ) -> tuple[bool, Optional[CommentarySearchResult]]:
        """
        Determine if a commentary is too similar to existing ones based on configured threshold.

        Returns:
            - Tuple of (is_too_similar, existing_commentary_if_duplicate)
        """
        similar_commentaries = await self.search(commentary_text, limit=1)

        if similar_commentaries and similar_commentaries[0].score:
            is_duplicate = (
                similar_commentaries[0].score
                > self.settings.commentary_similarity_threshold
            )
            return is_duplicate, similar_commentaries[0] if is_duplicate else None
        return False, None

    async def add_commentary(
        self,
        commentary: Commentary,
        author: str,
        status: ContentStatus,
        origin: ContentOrigin,
        id: Optional[uuid.UUID] = None,
        created_at: Optional[datetime.datetime] = None,
    ) -> tuple[bool, uuid.UUID, str]:
        """
        Add a new commentary to the index. If no ID is provided, a new UUID is generated.

        Args:
        - commentary: The Commentary object to be added.
        - id: Optional UUID for the commentary. If None, a new UUID is generated.

        Returns:
        - The UUID of the added commentary.
        """
        # Check for similarity using extracted business logic
        most_similar_similarity_score, most_similar_content_id = (
            await self._check_commentary_similarity(commentary.text)
        )
        is_too_similar, existing_commentary = await self._is_commentary_too_similar(
            commentary.text
        )

        if is_too_similar and existing_commentary:
            print(
                f"Input commentary is too similar to existing commentary with ID {existing_commentary.id}. "
                f"Similarity score: {existing_commentary.score:.3f} > threshold: {self.settings.commentary_similarity_threshold}"
            )
            return False, existing_commentary.id, existing_commentary.text

        # Create CommentaryInput object from Commentary object
        now = created_at or datetime.datetime.now()
        commentary_input = CommentaryDbEntry(
            text=commentary.text,
            id=id or uuid.uuid4(),
            created=now,
            last_modified=now,
            original_author=author,
            last_modified_by=author,
            authors=[AuthorEntry(name=author)],
            edit_history=[],
            title=commentary.title,
            status=status,
            origin=origin,
            most_similar_similarity_score=most_similar_similarity_score,
            most_similar_content_id=most_similar_content_id,
            long_text=commentary.long_text,
            short_text=commentary.short_text,
            style=commentary.style,
            references=commentary.references,
            references_count=len(commentary.references),
        )

        # Call upsert method of base class
        await super()._upsert(commentary_input)

        return True, commentary_input.id, commentary_input.text

    async def update_commentary(
        self, id: uuid.UUID, updated_commentary: Commentary
    ) -> uuid.UUID:
        """
        Update an existing commentary in the index.

        Args:
        - id: The UUID of the commentary to be updated.
        - updated_commentary: The updated Commentary object.

        Returns:
        - The UUID of the updated commentary.
        """
        raise NotImplementedError("update_commentary method not yet implemented")
