from typing import Optional, Type

from core.config import Settings
from domain.interfaces.embeddings_manager import IEmbeddingsManager
from domain.models.base_content import (
    BaseContentDbEntry,
    BaseContentSearchResult,
)
from repositories.interfaces.base_content_repository import IBaseContentRepository
from repositories.interfaces.repository_factory import IRepositoryFactory
from repositories.interfaces.statement_repository import IStatementRepository
from repositories.interfaces.commentary_repository import ICommentaryRepository
from repositories.interfaces.reference_repository import IReferenceRepository
from repositories.interfaces.generic_text_repository import IGenericTextRepository
from repositories.interfaces.content_repository import IContentRepository

# Import concrete Qdrant implementations
from repositories.implementations.qdrant.statement_repository import (
    StatementRepository,
)
from repositories.implementations.qdrant.commentary_repository import (
    CommentaryRepository,
)
from repositories.implementations.qdrant.reference_repository import (
    ReferenceRepository,
)
from repositories.implementations.qdrant.generic_text_repository import (
    GenericTextRepository,
)
from repositories.implementations.qdrant.registry_repository import (
    RegistryQdrantRepository,
)
from repositories.aggregated.content_repository import ContentRepository


class QdrantRepositoryFactory(IRepositoryFactory):
    """
    Concrete factory implementation for creating Qdrant-based repositories.

    This factory creates repository instances that use Qdrant vector database
    for semantic search and storage functionality.
    """

    def __init__(self, embeddings_manager: Optional[IEmbeddingsManager] = None):
        """
        Initialize the factory with an optional embeddings manager.

        Args:
            embeddings_manager: Optional embeddings manager for dependency injection.
                               If not provided, repositories will use the default singleton.
        """
        self._embeddings_manager = embeddings_manager

    def create_statement_repository(self, settings: Settings) -> IStatementRepository:
        """Create a Qdrant-based statement repository."""
        return StatementRepository(settings, self._embeddings_manager)

    def create_commentary_repository(self, settings: Settings) -> ICommentaryRepository:
        """Create a Qdrant-based commentary repository."""
        return CommentaryRepository(settings, self._embeddings_manager)

    def create_reference_repository(self, settings: Settings) -> IReferenceRepository:
        """Create a Qdrant-based reference repository."""
        return ReferenceRepository(settings, self._embeddings_manager)

    def create_generic_text_repository(
        self, settings: Settings
    ) -> IGenericTextRepository:
        """Create a Qdrant-based generic text repository."""
        return GenericTextRepository(settings, self._embeddings_manager)

    def create_registry_repository(
        self,
        settings: Settings,
        index_name: str,
        content_type: Optional[str],
        db_entry_model_class: Type[BaseContentDbEntry],
        search_result_model_class: Type[BaseContentSearchResult],
    ) -> IBaseContentRepository:
        """Create a generic, registry-driven Qdrant repository for a content type."""
        return RegistryQdrantRepository(
            index_name,
            content_type,
            settings,
            db_entry_model_class,
            search_result_model_class,
            self._embeddings_manager,
        )

    def create_content_repository(self, settings: Settings) -> IContentRepository:
        """Create a Qdrant-based aggregated content repository."""
        return ContentRepository(settings, self._embeddings_manager)
