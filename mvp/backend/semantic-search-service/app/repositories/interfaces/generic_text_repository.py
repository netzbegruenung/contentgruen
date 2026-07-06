from repositories.interfaces.base_content_repository import (
    IBaseContentRepository,
)
from domain.models.generic_text import (
    GenericTextDbEntry,
    GenericTextSearchResult,
)


class IGenericTextRepository(
    IBaseContentRepository[GenericTextDbEntry, GenericTextSearchResult]
):
    """
    Interface for generic text-specific repository operations.

    Extends the base content repository interface with generic text-specific functionality.
    Currently uses only the base functionality, but can be extended with generic text-specific
    methods in the future (e.g., searching by text categories, filtering by snippet length).
    """

    pass
