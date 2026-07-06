from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional

from domain.models.commentary import Commentary, CommentarySearchResult


### AddCommentary ###


class ReferenceInput(BaseModel):
    reference_string: str
    description: Optional[str] = None


class AddCommentaryRequest(BaseModel):
    commentary: Commentary
    references: List[ReferenceInput]


class AddCommentaryResponse(BaseModel):
    id: UUID


### SearchCommentary ###


class SearchCommentaryByTextRequest(BaseModel):
    query_text: str
    limit: int = 10
    # TODO: Add a field to specify the search type (content, commentary, etc.)
    # TODO: Add a field to specify minimum score


class CommentarySearchResponse(BaseModel):
    results: List[CommentarySearchResult]
