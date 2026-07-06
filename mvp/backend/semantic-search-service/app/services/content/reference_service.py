import datetime
import logging
from typing import Optional, List, Tuple
import uuid

from core.config import Settings
from utils.url_validator import validate_url_security, sanitize_url
from services.content.base_content_service import BaseContentService
from repositories.interfaces.reference_repository import (
    IReferenceRepository,
)
from repositories.interfaces.repository_factory import IRepositoryFactory
from domain.models.reference import (
    Reference,
    ReferenceDbEntry,
    ReferenceSearchResult,
)
from domain.models.author_entry import AuthorEntry
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin

logger = logging.getLogger(__name__)


class ReferenceService(
    BaseContentService[IReferenceRepository, ReferenceDbEntry, ReferenceSearchResult]
):
    def __init__(
        self,
        settings: Settings,
        repository_factory: Optional[IRepositoryFactory] = None,
    ):
        """
        Initialize the ReferenceService with the provided Settings.

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

        repository = repository_factory.create_reference_repository(settings)
        content_repository = repository_factory.create_content_repository(settings)

        super().__init__(
            settings,
            repository,
            content_repository,
            ReferenceDbEntry,
            ReferenceSearchResult,
        )

    async def find_exact_match(
        self, reference_string: str
    ) -> Optional[ReferenceDbEntry]:
        """
        Find reference by exact string match - MVP simplified version.
        No normalization, no semantic search, just exact match.

        Args:
        - reference_string: The exact reference string to find

        Returns:
        - The reference if found, None otherwise
        """
        try:
            # Direct exact match query
            results = await self._repository.search(f'"{reference_string}"', limit=1)

            # Check for exact string match
            for result in results:
                if result.reference_string == reference_string:
                    # Get the full db entry
                    return await self.get(result.id)

            return None
        except Exception as e:
            logger.warning(f"Error in find_exact_match: {e}")
            return None

    async def add_reference(
        self,
        reference: Reference,
        author: str,
        status: ContentStatus,
        origin: ContentOrigin,
        id: Optional[uuid.UUID] = None,
    ) -> Tuple[uuid.UUID, bool, Optional[str]]:
        """
        Add a new reference to the index with duplicate checking.

        Args:
        - reference: The Reference object to be added.
        - author: The author adding the reference
        - status: Content status
        - origin: Content origin
        - id: Optional UUID for the reference. If None, a new UUID is generated.

        Returns:
        - Tuple of (reference_id, was_new, message)
        """
        # Validate URL security
        is_valid, error_msg = validate_url_security(reference.reference_string)
        if not is_valid:
            logger.warning(f"Rejected reference URL for security: {error_msg}")
            raise ValueError(f"Invalid reference URL: {error_msg}")

        # Sanitize the URL
        reference.reference_string = sanitize_url(reference.reference_string)

        # Create a new ID if id is None
        if id is None:
            id = uuid.uuid4()

        # Create ReferenceDbEntry object from Reference object
        now = datetime.datetime.now()
        reference_input = ReferenceDbEntry(
            text=reference.text,
            id=id,
            created=now,
            last_modified=now,
            original_author=author,
            last_modified_by=author,
            authors=[AuthorEntry(name=author)],
            edit_history=[],
            reference_string=reference.reference_string,
            status=status,
            origin=origin,
            usage_count=1,
        )

        # Call upsert method of base class
        await super()._upsert(reference_input)
        return id, True, "New reference created successfully"

    async def _increment_usage_count(self, reference_id: uuid.UUID) -> None:
        """Increment the usage count for a reference"""
        try:
            reference = await self.get(reference_id)
            if reference:
                reference.usage_count = (reference.usage_count or 0) + 1
                await super()._upsert(reference)
        except Exception as e:
            logger.warning(
                f"Error incrementing usage count for reference {reference_id}: {e}"
            )
