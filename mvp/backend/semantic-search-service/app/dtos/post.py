from uuid import UUID
from pydantic import BaseModel
from typing import List

from domain.models.post import (
    Post,
    PostDbEntry,
    PostSearchResult,
)


### AddPost ###


class AddPostRequest(BaseModel):
    post: Post


class AddPostResponse(BaseModel):
    id: UUID


### GetAll ###


class PostGetAllResponse(BaseModel):
    results_count: int
    results: List[PostDbEntry]
    total_records_count: int


### SearchPost ###


class SearchPostByTextRequest(BaseModel):
    query_text: str
    limit: int = 10


class PostSearchResponse(BaseModel):
    results: List[PostSearchResult]
