from pydantic import BaseModel
from typing import List

from domain.models.content import ContentDbEntry, ContentSearchResult


### GetAll ###


class ContentGetAllResponse(BaseModel):
    results_count: int
    results: List[ContentDbEntry]
    total_records_count: int


### SearchContent ###


class SearchContentByTextRequest(BaseModel):
    query_text: str
    limit: int = 10
    # TODO: Add a field to specify the search type (content, statement, reply_suggestion, reply_suggestion_candidate)
    # TODO: Add a field to specify minimum score


class ContentSearchResponse(BaseModel):
    results: List[ContentSearchResult]
