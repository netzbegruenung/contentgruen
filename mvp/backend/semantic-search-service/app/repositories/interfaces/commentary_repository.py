from repositories.interfaces.base_content_repository import (
    IBaseContentRepository,
)
from domain.models.commentary import CommentaryDbEntry, CommentarySearchResult


class ICommentaryRepository(
    IBaseContentRepository[CommentaryDbEntry, CommentarySearchResult]
):
    """
    Interface for commentary-specific repository operations.

    Extends the base content repository interface with commentary-specific functionality.
    Currently uses only the base functionality, but can be extended with commentary-specific
    methods in the future (e.g., searching by referenced statement, filtering by source types).
    """

    pass
