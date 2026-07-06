from repositories.interfaces.base_content_repository import (
    IBaseContentRepository,
)
from domain.models.reference import ReferenceDbEntry, ReferenceSearchResult


class IReferenceRepository(
    IBaseContentRepository[ReferenceDbEntry, ReferenceSearchResult]
):
    """
    Interface for reference-specific repository operations.

    Extends the base content repository interface with reference-specific functionality.
    Currently uses only the base functionality, but can be extended with reference-specific
    methods in the future (e.g., searching by URL domain, filtering by reference type).
    """

    pass
