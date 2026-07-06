from repositories.interfaces.base_content_repository import (
    IBaseContentRepository,
)
from domain.models.content import ContentDbEntry, ContentSearchResult


class IContentRepository(IBaseContentRepository[ContentDbEntry, ContentSearchResult]):
    """
    Interface for aggregated content repository operations.

    This repository provides a unified view across all content types, allowing searches
    and operations that span statements, commentaries, references, and generic text.
    """

    pass
