import uuid
from pydantic import BaseModel, Field
from typing import List

from domain.models.statement import (
    Statement,
    StatementDbEntry,
    StatementSearchResult,
)
from domain.models.content_type import ContentType


### AddStatement ###


class AddStatementRequest(BaseModel):
    statement: Statement


class AddStatementResponse(BaseModel):
    statement_was_new: bool
    statement_id: uuid.UUID
    statement_text: str


### SearchStatement ###


class SearchStatementByTextRequest(BaseModel):
    query_text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query text for statements",
        example="renewable energy transition",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return",
        example=10,
    )
    # TODO: Add a field to specify the search type (content, statement, reply_suggestion, reply_suggestion_candidate)
    # TODO: Add a field to specify minimum score


class StatementSearchResponse(BaseModel):
    results: List[StatementSearchResult]


### GetAllStatements ###


class StatementGetAllResponse(BaseModel):
    results_count: int
    results: List[StatementDbEntry]
    total_records_count: int


### AddReplysuggestionToStatement ###


class AddReplysuggestionToStatementRequest(BaseModel):
    statement_id: uuid.UUID
    replysuggestion_id: uuid.UUID
    content_type: ContentType
    relevance: float


class AddReplysuggestionToStatementResponse(BaseModel):
    success: bool


### GetTopics ###


class GetTopicsResponse(BaseModel):
    topics: List[str]


### GetStatementsOfTopic ###


class GetStatementsOfTopicRequest(BaseModel):
    topic: str
    limit: int = 10


class GetStatementsOfTopicResponse(BaseModel):
    results: List[StatementDbEntry]


### GetCategories ###


class GetCategoriesResponse(BaseModel):
    categories: List[str]


### GetStatementsOfCategory ###


class GetStatementsOfCategoryRequest(BaseModel):
    category: str
    limit: int = 10


class GetStatementsOfCategoryResponse(BaseModel):
    results: List[StatementDbEntry]
