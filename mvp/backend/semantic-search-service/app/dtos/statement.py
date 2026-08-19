import uuid
from enum import Enum
from pydantic import BaseModel, Field
from typing import List

from domain.models.statement import (
    Statement,
    StatementDbEntry,
    StatementSearchResult,
)
from domain.models.content_origin import ContentOrigin
from domain.models.content_type import ContentType

### AddStatement ###


class StatementSource(str, Enum):
    """
    Woher der Text stammt, den /addStatement anlegen soll.

    Das Frontend ruft denselben Endpunkt aus zwei Situationen auf (beide ueber
    StatementService.findOrCreateStatement):

    - SEARCH_QUERY: aus der Ergebnisansicht heraus, weil jemand gesucht hat.
      Niemand hat hier etwas verfasst, also haengt auch niemand am Statement.
    - MANUALLY_CREATED: aus "Beitrag ergaenzen", wo jemand ausdruecklich eine
      Aussage benennt, zu der er antworten will.

    Bewusst ein eigenes, zweiwertiges Enum statt ContentOrigin: ueber die API
    sollen sich weder INITIAL_DATA noch AI_GENERATED setzen lassen.
    """

    SEARCH_QUERY = "search_query"
    MANUALLY_CREATED = "manually_created"

    def to_content_origin(self) -> ContentOrigin:
        return (
            ContentOrigin.SEARCH_QUERY
            if self is StatementSource.SEARCH_QUERY
            else ContentOrigin.MANUALLY_CREATED
        )


class AddStatementRequest(BaseModel):
    statement: Statement
    source: StatementSource = Field(
        default=StatementSource.SEARCH_QUERY,
        description=(
            "Aus welcher Situation der Aufruf kommt. Voreinstellung ist die "
            "datensparsame: ein Aufrufer, der nichts angibt, bekommt kein "
            "Statement mit Personenbezug."
        ),
    )


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
