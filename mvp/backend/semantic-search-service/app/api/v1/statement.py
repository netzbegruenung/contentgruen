import uuid
from typing import FrozenSet, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import ValidationError

from dependencies import (
    get_aufrufer,
    get_aussage_themen_service,
    get_statement_service,
    get_suchen_ohne_treffer_service,
    get_unbeantwortete_aussagen_service,
    require_admin,
    require_user,
)
from dtos.statement import (
    AddReplysuggestionToStatementRequest,
    AddReplysuggestionToStatementResponse,
    AddStatementRequest,
    AddStatementResponse,
    AussageMitThemenDto,
    AussagenMitThemenResponse,
    AussageResponse,
    AussageTreffer,
    AussageVorabRequest,
    AussageVorabResponse,
    GetCategoriesResponse,
    GetStatementsOfCategoryRequest,
    GetStatementsOfCategoryResponse,
    GetStatementsOfTopicRequest,
    GetStatementsOfTopicResponse,
    GetStatementByIdResponse,
    GetTopicsResponse,
    SearchStatementByTextRequest,
    StatementSearchResponse,
    StatementGetAllResponse,
    StatementSource,
    ThemaDto,
    ThemenResponse,
    ThemenTestsetResponse,
    ThemenZuordnenRequest,
    ThemenZuordnenResponse,
    ThemenZuordnungDto,
    UnbeantworteteAussageDto,
    themen_dtos,
    UnbeantworteteAussagenResponse,
)
from services.beitrag_fuer_aufrufer import AUSSAGE, Aufrufer, als_responses
from services.content.statement_service import AussageNichtGefunden, StatementService
from core.logging import get_logger
from domain.models.statement import Statement
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from domain.models.content_status import NEW_CONTENT_STATUS
from domain.models.content_origin import SEARCH_QUERY_AUTHOR
from services.suchen_ohne_treffer_service import SuchenOhneTrefferService
from services.unbeantwortete_aussagen_service import UnbeantworteteAussagenService
from services.aussage_themen_service import AussageThemenService
from domain.themen import NACH_SCHLUESSEL, THEMEN, ThemaUngueltig

logger = get_logger(__name__)

router = APIRouter()


async def _ueber_der_schwelle_fuer(
    aufrufer: Aufrufer, suchen_ohne_treffer: SuchenOhneTrefferService
) -> Optional[FrozenSet[uuid.UUID]]:
    """
    Welche Aussagen aus Suchanfragen ohne Antwort der Aufrufer sehen darf (#436):
    Admins alle (None: kein Filter), alle anderen nur die ueber der Schwelle der
    Kennzahl "Suchen ohne Treffer", wie in "Hier fehlt eine Antwort". Eine leere
    Menge heisst dann: nur kuratierte Aussagen, nicht etwa kein Filter.
    """
    if aufrufer.ist_admin:
        return None
    return await suchen_ohne_treffer.ueber_der_schwelle()


# Test endpoint to check if the API is running
@router.get("/")
async def read_test():
    return {"message": "This is a test endpoint"}


# Alle Aussagen, seitenweise; was Nicht-Admins sehen: _ueber_der_schwelle_fuer.
@router.get("/getAll", response_model=StatementGetAllResponse)
async def get_all(
    statement_service: StatementService = Depends(get_statement_service),
    suchen_ohne_treffer: SuchenOhneTrefferService = Depends(
        get_suchen_ohne_treffer_service
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    aufrufer: Aufrufer = Depends(get_aufrufer),
) -> StatementGetAllResponse:
    try:
        logger.debug("/getAll was called")

        offset = (page - 1) * page_size
        ueber_der_schwelle = await _ueber_der_schwelle_fuer(
            aufrufer, suchen_ohne_treffer
        )
        if ueber_der_schwelle is None:
            statement_index_results = await statement_service.get_all(
                limit=page_size, offset=offset
            )
            total_records_count = await statement_service.count()
        else:
            statement_index_results = await statement_service.get_all_curated(
                limit=page_size, offset=offset, ueber_der_schwelle=ueber_der_schwelle
            )
            total_records_count = await statement_service.count_curated(
                ueber_der_schwelle=ueber_der_schwelle
            )

        logger.debug(f"/getAll got {len(statement_index_results)} results")

        response = StatementGetAllResponse(
            results_count=len(statement_index_results),
            results=als_responses(
                AussageResponse, statement_index_results, aufrufer, AUSSAGE
            ),
            total_records_count=total_records_count,
        )

        return response
    except Exception as e:
        logger.error(f"Error in /getAll: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Eine Aussage per ID - fuer Beitragsformulare, die mit ?aussage=<id> geoeffnet
# werden. Liefert bewusst nur ID und Text, nicht die Antwortvorschlaege.
@router.get("/getById", response_model=GetStatementByIdResponse)
async def get_by_id(
    statement_id: uuid.UUID = Query(..., description="ID der Aussage"),
    statement_service: StatementService = Depends(get_statement_service),
) -> GetStatementByIdResponse:
    try:
        statement = await statement_service.get(statement_id)
    except ValidationError as e:
        # Vor ValueError: Pydantics ValidationError ist eine Unterklasse davon. Ein
        # Datensatz, der sich nicht lesen laesst, ist kaputt, nicht abwesend - das
        # gehoert ins Log und als 500 zum Aufrufer, nicht als 404 unter den Teppich.
        logger.error(f"Statement {statement_id} ist nicht lesbar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Statement not readable")
    except ValueError:
        # Das Repository meldet "nicht gefunden" und "anderer Inhaltstyp unter
        # dieser ID" als ValueError - beides heisst: diese Aussage gibt es nicht.
        raise HTTPException(status_code=404, detail="Statement not found")
    except Exception as e:
        logger.error(f"Error in /getById: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return GetStatementByIdResponse(
        statement_id=statement.id, statement_text=statement.text
    )


# "Hier fehlt eine Antwort": unbeantwortete Aussagen fuer Mitwirkende. Nur
# Aussagen, dazu aus der Kennzahl "Suchen ohne Treffer" die Zahl der Personen, nicht
# die der Suchen; eine Aussage aus einer Suchanfrage erst ab der Schwelle der
# Kennzahl, nie die einer einzelnen Person
# (services/unbeantwortete_aussagen_service.py).
@router.get("/unbeantwortet", response_model=UnbeantworteteAussagenResponse)
async def unbeantwortet(
    thema: Optional[str] = Query(
        default=None, description="Nur Aussagen mit diesem Thema (Schluessel)"
    ),
    user_id: str = Depends(require_user),
    service: UnbeantworteteAussagenService = Depends(
        get_unbeantwortete_aussagen_service
    ),
) -> UnbeantworteteAussagenResponse:
    if thema is not None and thema not in NACH_SCHLUESSEL:
        raise HTTPException(status_code=422, detail="Unknown Thema")
    try:
        aussagen = await service.liste(thema=thema)
    except Exception as e:
        logger.error(f"Error in /unbeantwortet: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to fetch unanswered statements"
        )
    return UnbeantworteteAussagenResponse(
        aussagen=[
            UnbeantworteteAussageDto(
                statement_id=a.statement_id,
                statement_text=a.text,
                personen_ohne_treffer=a.personen_ohne_treffer,
                themen=themen_dtos(a.themen),
            )
            for a in aussagen
        ]
    )


# Eine Aussage vorab anlegen, fuer ein absehbares Thema, bevor jemand danach sucht.
# Die Person ist Autorin; dieselbe vorhandene Aussage wird nicht doppelt angelegt,
# sondern zurueckgegeben (statement_was_new = false, StatementService.vorab_anlegen).
# Die gewaehlten Themen bekommt die neue Aussage; eine vorhandene nur, wenn sie noch
# keine hat, damit das Anlegen eine vorhandene Zuordnung nicht nebenbei ersetzt.
# (Pruefen und Setzen sind zwei Schritte; legen zwei Personen dieselbe Aussage im
# selben Moment an, gilt die zweite Zuordnung. Aendern geht ohnehin ueber
# /themen/zuordnen.) Die Antwort nennt die Themen, die die Aussage jetzt hat.
# Schlaegt das Zuordnen fehl, bleibt die Aussage angelegt und die Antwort ohne
# Themen: Die Aussage gibt es dann, und die Seite sagt das.
@router.post("/vorab", response_model=AussageVorabResponse)
async def vorab_anlegen(
    request: AussageVorabRequest,
    user_id: str = Depends(require_user),
    statement_service: StatementService = Depends(get_statement_service),
    themen_service: AussageThemenService = Depends(get_aussage_themen_service),
) -> AussageVorabResponse:
    try:
        statement_was_new, statement_id, statement_text = (
            await statement_service.vorab_anlegen(request.text, user_id)
        )
    except Exception as e:
        logger.error(f"Error in /vorab: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add statement")
    themen = await _themen_beim_vorab_anlegen(
        themen_service, statement_id, statement_was_new, request.themen
    )
    return AussageVorabResponse(
        statement_was_new=statement_was_new,
        statement_id=statement_id,
        statement_text=statement_text,
        themen=themen_dtos(themen),
    )


async def _themen_beim_vorab_anlegen(
    themen_service: AussageThemenService,
    statement_id: uuid.UUID,
    neu: bool,
    gewaehlt: List[str],
) -> List[str]:
    """Die Themen der Aussage nach dem Vorab-Anlegen; [] wenn das Zuordnen scheitert."""
    try:
        if not neu:
            bisher = themen_service.themen_von([statement_id]).get(statement_id)
            if bisher:
                return bisher
        if gewaehlt:
            return await themen_service.zuordnen(statement_id, gewaehlt)
        return []
    except Exception as e:
        logger.warning(f"/vorab: Themen nicht zugeordnet: {type(e).__name__}")
        return []


# Die feste Themenliste (domain/themen.json), fuer die Auswahl beim Zuordnen.
@router.get("/themen", response_model=ThemenResponse)
async def themen_liste() -> ThemenResponse:
    return ThemenResponse(
        themen=[ThemaDto(schluessel=t.schluessel, name=t.name) for t in THEMEN]
    )


# Die Themen einer Aussage von Hand setzen: ersetzt die bisherigen, eine leere
# Liste entfernt alle. Jede angemeldete Person darf zuordnen; gespeichert wird
# nicht, wer es war (services/aussage_themen_service.py).
@router.put("/themen/zuordnen", response_model=ThemenZuordnenResponse)
async def themen_zuordnen(
    request: ThemenZuordnenRequest,
    user_id: str = Depends(require_user),
    themen_service: AussageThemenService = Depends(get_aussage_themen_service),
) -> ThemenZuordnenResponse:
    try:
        themen = await themen_service.zuordnen(request.statement_id, request.themen)
    except ThemaUngueltig as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AussageNichtGefunden:
        raise HTTPException(status_code=404, detail="Statement not found")
    except Exception as e:
        logger.error(f"Error in /themen/zuordnen: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to assign Themen")
    return ThemenZuordnenResponse(
        statement_id=request.statement_id, themen=themen_dtos(themen)
    )


# Admin: alle Aussagen ohne die unbeantworteten Suchanfragen, mit ihren Themen,
# zum nachtraeglichen Zuordnen; die ohne Thema zuerst.
@router.get("/themen/aussagen", response_model=AussagenMitThemenResponse)
async def themen_aussagen(
    admin_id: str = Depends(require_admin),
    themen_service: AussageThemenService = Depends(get_aussage_themen_service),
) -> AussagenMitThemenResponse:
    try:
        aussagen = await themen_service.aussagen_zum_zuordnen()
    except Exception as e:
        logger.error(f"Error in /themen/aussagen: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch statements")
    return AussagenMitThemenResponse(
        aussagen=[
            AussageMitThemenDto(
                statement_id=a.statement_id,
                statement_text=a.text,
                themen=themen_dtos(a.themen),
                im_testset=a.im_testset,
            )
            for a in aussagen
        ]
    )


# Admin: die Zuordnungen von Hand als Testset fuer spaetere Themenvorschlaege,
# ohne Personendaten (kein Autor, keine Kennung, kein Zeitpunkt).
@router.get("/themen/testset", response_model=ThemenTestsetResponse)
async def themen_testset(
    admin_id: str = Depends(require_admin),
    themen_service: AussageThemenService = Depends(get_aussage_themen_service),
) -> ThemenTestsetResponse:
    try:
        zuordnungen = await themen_service.testset()
    except Exception as e:
        logger.error(f"Error in /themen/testset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export Themen-Testset")
    return ThemenTestsetResponse(
        zuordnungen=[
            ThemenZuordnungDto(
                statement_id=z.statement_id,
                text=z.text,
                themen=z.themen,
                zuordnungsart=z.zuordnungsart,
            )
            for z in zuordnungen
        ]
    )


# Aehnliche Aussagen. Fuer Nicht-Admins dieselbe Auswahl wie in getAll (#436);
# nur_kuratiert laesst fuer alle auch die Suchanfragen ueber der Schwelle weg
# (Vorschlaege im Antwort-auf-Feld).
@router.post("/searchStatements", response_model=StatementSearchResponse)
async def search_statements(
    request: SearchStatementByTextRequest,
    statement_service: StatementService = Depends(get_statement_service),
    suchen_ohne_treffer: SuchenOhneTrefferService = Depends(
        get_suchen_ohne_treffer_service
    ),
    aufrufer: Aufrufer = Depends(get_aufrufer),
) -> StatementSearchResponse:
    try:
        logger.debug("/searchStatements was called")

        # nur_kuratiert: fuer jede Rolle ohne Suchanfragen ohne Antwort, auch ohne
        # die ueber der Schwelle; die Kennzahl wird dann nicht abgefragt.
        if request.nur_kuratiert:
            ueber_der_schwelle = frozenset()
        else:
            ueber_der_schwelle = await _ueber_der_schwelle_fuer(
                aufrufer, suchen_ohne_treffer
            )

        if ueber_der_schwelle is None and request.min_similarity is None:
            statement_index_results = await statement_service.search(
                request.query_text, request.limit
            )
        else:
            statement_index_results = await statement_service.search_filtered(
                request.query_text,
                request.limit,
                nur_kuratiert=ueber_der_schwelle is not None,
                min_similarity=request.min_similarity,
                ueber_der_schwelle=ueber_der_schwelle or frozenset(),
            )
        logger.debug(f"/searchStatements got {len(statement_index_results)} results")

        response: StatementSearchResponse = StatementSearchResponse(
            results=als_responses(
                AussageTreffer, statement_index_results, aufrufer, AUSSAGE
            )
        )

        return response
    except Exception as e:
        logger.error(f"Error in /searchStatements: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Adds a new statement to the statement_index
@router.post("/addStatement", response_model=AddStatementResponse)
async def add_statement(
    request: AddStatementRequest,
    statement_service: StatementService = Depends(get_statement_service),
    x_user: str = Header(...),
) -> AddStatementResponse:
    try:
        logger.debug("/addStatement was called")

        if not x_user:
            raise HTTPException(status_code=400, detail="X-User header missing")

        # TODO: Validate ReplySuggestions

        # Create StatementInput object from the statement in the request
        statement: Statement = Statement(
            text=request.statement.text,
            replysuggestions=request.statement.replysuggestions,
        )

        # Suchanfragen bekommen einen Systemautor: sie fallen automatisch an,
        # sobald jemand sucht, und sind keine Autorenleistung. Nur der
        # ausdrueckliche Weg ueber "Beitrag ergaenzen" nennt die Person.
        author = (
            SEARCH_QUERY_AUTHOR
            if request.source is StatementSource.SEARCH_QUERY
            else x_user
        )

        # Aussagen sind sofort sichtbar.
        statement_was_new, statement_id, statement_text = (
            await statement_service.add_statement(
                statement,
                author,
                NEW_CONTENT_STATUS,
                request.source.to_content_origin(),
            )
        )

        # Create response object
        response = AddStatementResponse(
            statement_was_new=statement_was_new,
            statement_id=statement_id,
            statement_text=statement_text,
        )

        return response

    except Exception as e:
        # Improve error handling by returning specific exception types
        logger.error(f"Error in /addStatement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Adds a reply suggestion to a statement
@router.post(
    "/addReplysuggestionToStatement",
    response_model=AddReplysuggestionToStatementResponse,
)
async def add_replysuggestion_to_statement(
    request: AddReplysuggestionToStatementRequest,
    statement_service: StatementService = Depends(get_statement_service),
) -> AddReplysuggestionToStatementResponse:
    try:
        logger.debug("/addReplysuggestionToStatement was called")

        # Use content_type directly from the request - no need to look it up
        success = await statement_service.add_statementreplysuggestion_to_statement(
            statement_id=request.statement_id,
            replysuggestion_id=request.replysuggestion_id,
            content_type=request.content_type,  # Now coming from request
            relevance=request.relevance,
        )

        # Create response object
        response = AddReplysuggestionToStatementResponse(success=success)

        return response

    except AussageNichtGefunden:
        # Nur "gibt es nicht" ist 404; alles andere (nicht lesbar, Speicherfehler,
        # andere ValueErrors) ist ein echter Fehler.
        raise HTTPException(status_code=404, detail="Statement not found")
    except Exception as e:
        logger.error(f"Error in /addReplysuggestionToStatement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Retrieves the topics of the statement_index
@router.get("/getTopics", response_model=GetTopicsResponse)
def get_topics(
    statement_service: StatementService = Depends(get_statement_service),
) -> GetTopicsResponse:
    try:
        logger.debug("statement/getTopics was called")

        statement_index_topics = statement_service.get_topics()

        response: GetTopicsResponse = GetTopicsResponse(topics=statement_index_topics)

        return response
    except Exception as e:
        logger.error(f"Error in get_statement_topics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Retrieves the statements of a specific topic from the statement_index
@router.post("/getStatementsOfTopic", response_model=GetStatementsOfTopicResponse)
def get_statement_topics(
    request: GetStatementsOfTopicRequest,
    statement_service: StatementService = Depends(get_statement_service),
    aufrufer: Aufrufer = Depends(get_aufrufer),
) -> GetStatementsOfTopicResponse:
    try:
        logger.debug("/getStatementsOfTopic was called")

        statement_index_results = statement_service.get_items_of_topic(
            request.topic, request.limit
        )

        response: GetStatementsOfTopicResponse = GetStatementsOfTopicResponse(
            results=als_responses(
                AussageResponse, statement_index_results, aufrufer, AUSSAGE
            )
        )

        return response
    except Exception as e:
        logger.error(f"Error in get_statement_topics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Retrieves the categories of the statement_index
@router.get("/getCategories", response_model=GetCategoriesResponse)
def get_categories(
    statement_service: StatementService = Depends(get_statement_service),
) -> GetCategoriesResponse:
    try:
        logger.debug("statement/getTopics was called")

        statement_index_categories = statement_service.get_categories()

        response: GetCategoriesResponse = GetCategoriesResponse(
            categories=statement_index_categories
        )

        return response
    except Exception as e:
        logger.error(f"Error in get_statement_topics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Retrieves the statements of a specific category from the statement_index
@router.post("/getStatementsOfCategory", response_model=GetStatementsOfCategoryResponse)
def get_statements_of_category(
    request: GetStatementsOfCategoryRequest,
    statement_service: StatementService = Depends(get_statement_service),
    aufrufer: Aufrufer = Depends(get_aufrufer),
) -> GetStatementsOfCategoryResponse:
    try:
        logger.debug("/getStatementsOfCategory was called")

        statement_index_results = statement_service.get_items_of_category(
            request.category, request.limit
        )

        response: GetStatementsOfCategoryResponse = GetStatementsOfCategoryResponse(
            results=als_responses(
                AussageResponse, statement_index_results, aufrufer, AUSSAGE
            )
        )

        return response
    except Exception as e:
        logger.error(f"Error in get_statements_of_category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
