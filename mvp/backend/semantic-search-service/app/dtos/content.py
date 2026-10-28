from pydantic import BaseModel
from typing import List

from dtos.beitrag import BeitragResponse, BeitragTreffer


### GetAll ###


class ContentGetAllResponse(BaseModel):
    results_count: int
    results: List[BeitragResponse]
    total_records_count: int


### SearchContent ###


class SearchContentByTextRequest(BaseModel):
    query_text: str
    limit: int = 10
    # TODO: Add a field to specify the search type (content, statement, reply_suggestion, reply_suggestion_candidate)
    # TODO: Add a field to specify minimum score


class ContentSearchResponse(BaseModel):
    results: List[BeitragTreffer]
