from typing import Optional
import uuid
import datetime

from core.config import Settings
from services.content.base_content_service import BaseContentService
from repositories.interfaces.generic_text_repository import (
    IGenericTextRepository,
)
from repositories.interfaces.repository_factory import IRepositoryFactory
from domain.models.generic_text import (
    GenericText,
    GenericTextDbEntry,
    GenericTextSearchResult,
)
from domain.models.author_entry import AuthorEntry
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin


class GenericTextService(
    BaseContentService[
        IGenericTextRepository, GenericTextDbEntry, GenericTextSearchResult
    ]
):
    def __init__(
        self,
        settings: Settings,
        repository_factory: Optional[IRepositoryFactory] = None,
    ):
        """
        Initialize the GenericTextService with the provided Settings.

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

        repository = repository_factory.create_generic_text_repository(settings)
        content_repository = repository_factory.create_content_repository(settings)

        super().__init__(
            settings,
            repository,
            content_repository,
            GenericTextDbEntry,
            GenericTextSearchResult,
        )

    async def add_generic_text(
        self,
        generic_text: GenericText,
        author: str,
        status: ContentStatus,
        origin: ContentOrigin,
        id: Optional[uuid.UUID] = None,
        created_at: Optional[datetime.datetime] = None,
    ) -> tuple[bool, uuid.UUID, str]:
        """
        Add a new generic text to the index. If no ID is provided, a new UUID is generated.

        Args:
        - generic_text: The GenericText object to be added.
        - author: The author adding the generic text
        - status: Content status
        - origin: Content origin
        - id: Optional UUID for the generic text. If None, a new UUID is generated.

        Returns:
        - Tuple of (success: bool, id: UUID, text: str)
        """
        # TODO: Perform similarity check (see StatementService for example)

        print(f"Adding generic text '{generic_text.title}'")

        # Default description text to title if not provided
        if not generic_text.text:
            generic_text.text = generic_text.title

        # Create GenericTextDbEntry object from GenericText object
        now = created_at or datetime.datetime.now()
        generic_text_input = GenericTextDbEntry(
            text=generic_text.text,
            id=id or uuid.uuid4(),
            created=now,
            last_modified=now,
            original_author=author,
            last_modified_by=author,
            authors=[AuthorEntry(name=author)],
            edit_history=[],
            title=generic_text.title,
            references=generic_text.references,
            references_count=len(generic_text.references),
            status=status,
            origin=origin,
        )

        # Call upsert method of base class
        generic_text_id = await super()._upsert(generic_text_input)
        return True, generic_text_id, generic_text_input.text

    def update_generic_text(
        self, id: uuid.UUID, updated_generic_text: GenericText
    ) -> uuid.UUID:
        """
        Update an existing generic text in the index.

        Args:
        - id: The UUID of the generic text to be updated.
        - updated_generic_text: The updated GenericText object.

        Returns:
        - The UUID of the updated generic text.
        """
        raise NotImplementedError("update_generic_text method not yet implemented")
