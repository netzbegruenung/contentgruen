from abc import abstractmethod
import uuid
from typing import AbstractSet, List

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

    @abstractmethod
    async def count_curated(self, auch: AbstractSet[uuid.UUID] = frozenset()) -> int:
        """
        Count statements, leaving out search queries nobody has answered yet,
        except those in auch (search queries above the threshold, #436).

        Returns:
            Number of statements that carry curated substance
        """
        pass

    @abstractmethod
    async def search_curated(
        self,
        query_text: str,
        limit: int,
        auch: AbstractSet[uuid.UUID] = frozenset(),
    ) -> List[StatementSearchResult]:
        """
        Search statements, leaving out search queries nobody has answered yet
        (same criterion as count_curated, including auch).
        """
        pass

    @abstractmethod
    async def get_all_curated(
        self, limit: int, offset: int, auch: AbstractSet[uuid.UUID] = frozenset()
    ) -> List[StatementDbEntry]:
        """
        List statements page by page, leaving out search queries nobody has
        answered yet (same criterion as count_curated, including auch).
        """
        pass

    @abstractmethod
    async def ohne_kommentar(self) -> List[StatementDbEntry]:
        """
        Visible statements without a visible Kommentar among their reply
        suggestions, leaving out search queries nobody has answered yet (as
        count_curated). Blocked or deleted Kommentare do not count as an answer.
        """
        pass
