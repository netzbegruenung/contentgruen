import datetime
import uuid
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional

from domain.models.statement import Statement, StatementReplysuggestion
from domain.models.content_origin import ContentOrigin
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType


### Aussage nach aussen ###


class AussageResponse(BaseModel):
    """
    Eine Aussage, wie die lesenden Routen sie ausliefern (#385, Muster aus #333).

    Bewusst eine Auswahl aus dem DbEntry: keine Kennung (``last_modified_by``,
    ``authors``, ``edit_history``), keine Felder der Moderation und
    Dublettenpruefung. ``original_author`` ist nur unterwegs belegt:
    ``fuer_aufrufer`` (services/beitrag_fuer_aufrufer.py, ``AUSSAGE``) setzt
    daraus Anzeigename und ``ist_eigene_aussage`` und leert es fuer alle ausser
    Admins.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_type: ContentType
    text: str
    created: datetime.datetime
    status: ContentStatus
    replysuggestions: List[StatementReplysuggestion] = []
    replysuggestions_count: int = 0
    # Anzeigename zu original_author; nur fuer angemeldete Aufrufer, sonst None.
    autor_name: Optional[str] = None
    # Ob die aufrufende Person die Aussage angelegt hat; nur angemeldet, sonst None.
    ist_eigene_aussage: Optional[bool] = None
    # Die Kennung der Person, die die Aussage angelegt hat, nur fuer Admins.
    original_author: Optional[str] = None


class AussageTreffer(AussageResponse):
    score: float


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


### GetStatementById ###


class GetStatementByIdResponse(BaseModel):
    """Nur ID und Text: das Beitragsformular zeigt damit, worauf es antwortet."""

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
    nur_kuratiert: bool = Field(
        default=False,
        description=(
            "Unbeantwortete Suchanfragen weglassen - dasselbe Kriterium wie der "
            "Aussagen-Zaehler der Startseite."
        ),
    )
    min_similarity: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nur Treffer mit mindestens diesem Aehnlichkeitswert",
    )
    # TODO: Add a field to specify the search type (content, statement, reply_suggestion, reply_suggestion_candidate)


class StatementSearchResponse(BaseModel):
    results: List[AussageTreffer]


### GetAllStatements ###


class StatementGetAllResponse(BaseModel):
    results_count: int
    results: List[AussageResponse]
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
    results: List[AussageResponse]


### GetCategories ###


class GetCategoriesResponse(BaseModel):
    categories: List[str]


### GetStatementsOfCategory ###


class GetStatementsOfCategoryRequest(BaseModel):
    category: str
    limit: int = 10


class GetStatementsOfCategoryResponse(BaseModel):
    results: List[AussageResponse]
