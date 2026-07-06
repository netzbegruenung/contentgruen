from pydantic import BaseModel, Field
from typing import List, Optional

from domain.models.commentary import CommentaryDbEntry
from domain.models.generic_text import GenericTextDbEntry
from domain.models.post import PostDbEntry
from domain.models.image import ImageDbEntry

# TODO: Evaluate usage of camelize


###   Requests   ###


class SearchByTextRequest(BaseModel):
    query_text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query text",
        example="climate change policy",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return",
        example=10,
    )
    # TODO: Add a field to specify minimum similarity score of statements
    # TODO: Add a field to specify minimum rating of reply suggestions

    # class Config:
    #     alias_generator = camelize
    #     populate_by_name = True


###   Entities   ###


class CommentarySearchResult(BaseModel):
    score: float
    statement_text: str
    statement_similarity_score: float
    reply_relevance: float
    commentary_result: CommentaryDbEntry
    user_vote: Optional[str] = None  # "like", "dislike", or None
    # Polarity filtering metadata
    polarity_mismatch_detected: Optional[bool] = None
    original_score: Optional[float] = None  # Score before polarity adjustment


class GenericTextSearchResult(BaseModel):
    score: float
    statement_text: str
    statement_similarity_score: float
    reply_relevance: float
    generictext_result: GenericTextDbEntry
    user_vote: Optional[str] = None  # "like", "dislike", or None
    # Polarity filtering metadata
    polarity_mismatch_detected: Optional[bool] = None
    original_score: Optional[float] = None  # Score before polarity adjustment


class PostSearchResult(BaseModel):
    score: float
    statement_text: str
    statement_similarity_score: float
    reply_relevance: float
    post_result: PostDbEntry
    user_vote: Optional[str] = None  # "like", "dislike", or None
    # Polarity filtering metadata
    polarity_mismatch_detected: Optional[bool] = None
    original_score: Optional[float] = None  # Score before polarity adjustment


class ImageSearchResult(BaseModel):
    score: float
    statement_text: Optional[str] = None
    statement_similarity_score: Optional[float] = None
    reply_relevance: Optional[float] = None
    image_result: ImageDbEntry
    user_vote: Optional[str] = None
    polarity_mismatch_detected: Optional[bool] = None
    original_score: Optional[float] = None


###   Responses   ###


class SearchResponse(BaseModel):
    query_was_newly_added_as_statement: bool
    statement_id: str
    statement_text: str
    commentary_search_results_count: int
    commentary_search_results: List[CommentarySearchResult]
    generictext_search_results_count: int
    generictext_search_results: List[GenericTextSearchResult]
    post_search_results_count: int = 0
    post_search_results: List[PostSearchResult] = []
    image_search_results_count: int = 0
    image_search_results: List[ImageSearchResult] = []

    # class Config:
    #     alias_generator = camelize
    #     populate_by_name = True
