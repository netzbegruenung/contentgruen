from pydantic import BaseModel
from typing import List

from domain.models.commentary import CommentarySearchResult


###   Requests   ###


class GetReplySuggestionCandidatesByStatementIdRequest(BaseModel):
    statement_id: str
    limit: int = 10
    # TODO: Add a field to specify minimum similarity score of statements
    # TODO: Add a field to specify minimum relevance of reply suggestions
    # TODO: Add a field to specify minimum similarity score of content


###   Responses   ###


class ReplySuggestionCandidatesResponse(BaseModel):
    commentary_results: List[CommentarySearchResult]
