import datetime
import uuid
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Iterable, List, Optional

from domain.models.statement import Statement, StatementReplysuggestion
from domain.models.content_origin import ContentOrigin
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from domain.themen import NACH_SCHLUESSEL, themen_pruefen


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


### Hier fehlt eine Antwort ###

# Wie lang eine vorab angelegte Aussage sein darf; die Obergrenze wie bei der
# Aussagensuche (SearchStatementByTextRequest).
AUSSAGE_MIN_ZEICHEN = 3
AUSSAGE_MAX_ZEICHEN = 1000


### Themen ###


class ThemaDto(BaseModel):
    """Ein Thema aus der festen Liste: Schluessel (gespeichert) und Name (Anzeige)."""

    schluessel: str
    name: str


def themen_dtos(schluessel: Iterable[str]) -> List[ThemaDto]:
    """Die Themen als DTOs; Schluessel, die nicht (mehr) in der Liste stehen, fallen weg."""
    return [
        ThemaDto(schluessel=t.schluessel, name=t.name)
        for t in (NACH_SCHLUESSEL.get(s) for s in schluessel)
        if t is not None
    ]


class ThemenResponse(BaseModel):
    themen: List[ThemaDto]


class ThemenZuordnenRequest(BaseModel):
    statement_id: uuid.UUID
    # Hoechstens zwei aus der Liste; geprueft in AussageThemenService.zuordnen.
    themen: List[str] = Field(default_factory=list)


class ThemenZuordnenResponse(BaseModel):
    statement_id: uuid.UUID
    themen: List[ThemaDto]


class AussageMitThemenDto(BaseModel):
    statement_id: uuid.UUID
    statement_text: str
    themen: List[ThemaDto]


class AussagenMitThemenResponse(BaseModel):
    aussagen: List[AussageMitThemenDto]


class ThemenZuordnungDto(BaseModel):
    """Eine Zeile des Testsets: bewusst ohne Autor, Kennung und Zeitpunkt."""

    statement_id: uuid.UUID
    text: str
    themen: List[str]
    quelle: str


class ThemenTestsetResponse(BaseModel):
    zuordnungen: List[ThemenZuordnungDto]


class UnbeantworteteAussageDto(BaseModel):
    """
    Eine unbeantwortete Aussage: ID (fuer "Selbst beantworten") und Text, dazu wie
    viele Personen ohne Treffer danach gesucht haben (0: nur ohne Kommentar); wie
    oft gesucht wurde, sehen nur Admins.
    """

    statement_id: uuid.UUID
    statement_text: str
    personen_ohne_treffer: int
    themen: List[ThemaDto] = Field(default_factory=list)


class UnbeantworteteAussagenResponse(BaseModel):
    aussagen: List[UnbeantworteteAussageDto]


class AussageVorabRequest(BaseModel):
    text: str = Field(
        ...,
        description="Die Aussage, fuer die es absehbar eine Antwort braucht",
    )
    themen: List[str] = Field(
        default_factory=list,
        description="Optional ein bis zwei Themen aus der Liste (domain/themen.json)",
    )

    @field_validator("text")
    @classmethod
    def text_pruefen(cls, wert: str) -> str:
        wert = wert.strip()
        if not AUSSAGE_MIN_ZEICHEN <= len(wert) <= AUSSAGE_MAX_ZEICHEN:
            raise ValueError(
                f"Eine Aussage hat {AUSSAGE_MIN_ZEICHEN} bis "
                f"{AUSSAGE_MAX_ZEICHEN} Zeichen"
            )
        return wert

    @field_validator("themen")
    @classmethod
    def themen_pruefen(cls, wert: List[str]) -> List[str]:
        # Vor dem Anlegen pruefen: sonst stuende die Aussage schon, ohne Themen.
        return themen_pruefen(wert)


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
        max_length=AUSSAGE_MAX_ZEICHEN,
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
