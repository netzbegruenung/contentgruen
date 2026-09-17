from typing import Optional
from domain.models.zeit import utc_jetzt
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

from core.logging import get_logger

logger = get_logger(__name__)


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

    async def finde_dublette(self, text: str) -> Optional[CommentarySearchResult]:
        """
        Den vorhandenen Kommentar, von dem dieser Text eine Dublette ist, sonst None.

        Dublette ist: normalisiert gleicher Text oder passage/passage-Aehnlichkeit >=
        commentary_similarity_threshold. passage, weil der Bestand so eingebettet
        ist - mit query erreicht selbst wortgleicher Text nur 0,96.
        """
        vorhandener, _ = await self._vorhandenen_finden(
            text, self.settings.commentary_similarity_threshold, praefix="passage"
        )
        return vorhandener

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

        Ist der Text eine Dublette (finde_dublette), wird nichts angelegt.

        Returns:
        - (neu angelegt, ID, Text) - bei einer Dublette ID und Text des vorhandenen.
        """
        vorhandener, bester = await self._vorhandenen_finden(
            commentary.text,
            self.settings.commentary_similarity_threshold,
            praefix="passage",
        )
        if vorhandener is not None:
            logger.debug(
                f"Input commentary is a duplicate of existing commentary with ID {vorhandener.id} "
                f"(score {vorhandener.score:.3f}, threshold {self.settings.commentary_similarity_threshold})"
            )
            return False, vorhandener.id, vorhandener.text
        most_similar_similarity_score = bester.score if bester else None
        most_similar_content_id = bester.id if bester else None

        # Create CommentaryInput object from Commentary object
        now = created_at or utc_jetzt()
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
