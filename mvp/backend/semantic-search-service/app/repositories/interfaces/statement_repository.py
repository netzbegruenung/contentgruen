from abc import abstractmethod
from typing import List

from repositories.interfaces.base_content_repository import (
    IBaseContentRepository,
)
from domain.models.statement import StatementDbEntry, StatementSearchResult


class IStatementRepository(
    IBaseContentRepository[StatementDbEntry, StatementSearchResult]
):
    """
    Interface for statement-specific repository operations.

    Extends the base content repository interface with statement-specific functionality.
    """

    @abstractmethod
    def search_with_reply_filter(
        self, query_text: str, limit: int = 10, min_replysuggestions_count: int = 0
    ) -> List[StatementSearchResult]:
        """
        Search for statements with a minimum number of reply suggestions.

        Args:
            query_text: The text to search for
            limit: Maximum number of results to return
            min_replysuggestions_count: Minimum number of reply suggestions required

        Returns:
            List of statement search results that meet the criteria
        """
        pass
