from uuid import UUID
from pydantic import BaseModel
from typing import List

from domain.cc0_hinweis import Cc0Wortlaut
from domain.models.post import Post
from dtos.beitrag import PostResponse, PostTreffer


### AddPost ###


class AddPostRequest(BaseModel):
    post: Post
    # Kennung des CC0-Hinweises, den die Person beim Speichern gesehen hat (#431,
    # domain/cc0_hinweis.py).
    cc0_wortlaut: Cc0Wortlaut = None


class AddPostResponse(BaseModel):
    id: UUID


### GetAll ###


class PostGetAllResponse(BaseModel):
    results_count: int
    results: List[PostResponse]
    total_records_count: int


### SearchPost ###


class SearchPostByTextRequest(BaseModel):
    query_text: str
    limit: int = 10


class PostSearchResponse(BaseModel):
    results: List[PostTreffer]
