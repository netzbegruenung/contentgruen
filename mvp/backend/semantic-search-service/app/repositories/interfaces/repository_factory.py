from abc import ABC, abstractmethod

from core.config import Settings
from repositories.interfaces.statement_repository import (
    IStatementRepository,
)
from repositories.interfaces.commentary_repository import (
    ICommentaryRepository,
)
from repositories.interfaces.reference_repository import (
    IReferenceRepository,
)
from repositories.interfaces.generic_text_repository import (
    IGenericTextRepository,
)
from repositories.interfaces.content_repository import IContentRepository
from repositories.interfaces.base_content_repository import IBaseContentRepository
from domain.models.base_content import (
    BaseContentDbEntry,
    BaseContentSearchResult,
)
from typing import Type, Optional


class IRepositoryFactory(ABC):
    """
    Abstract factory interface for creating repository instances.

    This factory abstracts the creation of repositories from specific backend implementations,
    making it easy to switch between different persistence technologies if needed
    without changing the service layer code.
    """

    @abstractmethod
    def create_statement_repository(self, settings: Settings) -> IStatementRepository:
        """
        Create a statement repository instance.

        Args:
            settings: Configuration settings for the repository

        Returns:
            Statement repository implementation
        """
        pass

    @abstractmethod
    def create_commentary_repository(self, settings: Settings) -> ICommentaryRepository:
        """
        Create a commentary repository instance.

        Args:
            settings: Configuration settings for the repository

        Returns:
            Commentary repository implementation
        """
        pass

    @abstractmethod
    def create_reference_repository(self, settings: Settings) -> IReferenceRepository:
        """
        Create a reference repository instance.

        Args:
            settings: Configuration settings for the repository

        Returns:
            Reference repository implementation
        """
        pass

    @abstractmethod
    def create_generic_text_repository(
        self, settings: Settings
    ) -> IGenericTextRepository:
        """
        Create a generic text repository instance.

        Args:
            settings: Configuration settings for the repository

        Returns:
            Generic text repository implementation
        """
        pass

    @abstractmethod
    def create_registry_repository(
        self,
        settings: Settings,
        index_name: str,
        content_type: Optional[str],
        db_entry_model_class: Type[BaseContentDbEntry],
        search_result_model_class: Type[BaseContentSearchResult],
    ) -> IBaseContentRepository:
        """
        Create a generic, registry-driven repository for a content type.

        This is the seam that lets a new content type be added as a declarative
        spec (see domain/content_registry.py) without a per-type repository clone.

        Args:
            settings: Configuration settings for the repository
            index_name: Logical index/repository name
            content_type: Content-type discriminator value (None = aggregated view)
            db_entry_model_class: Pydantic model for stored entries
            search_result_model_class: Pydantic model for scored search results

        Returns:
            A generic content repository implementation
        """
        pass

    @abstractmethod
    def create_content_repository(self, settings: Settings) -> IContentRepository:
        """
        Create an aggregated content repository instance.

        Args:
            settings: Configuration settings for the repository

        Returns:
            Aggregated content repository implementation
        """
        pass
