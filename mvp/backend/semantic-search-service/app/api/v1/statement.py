from fastapi import APIRouter, Depends, HTTPException, Header, Query

from dependencies import get_statement_service
from dtos.statement import (
    AddReplysuggestionToStatementRequest,
    AddReplysuggestionToStatementResponse,
    AddStatementRequest,
    AddStatementResponse,
    GetCategoriesResponse,
    GetStatementsOfCategoryRequest,
    GetStatementsOfCategoryResponse,
    GetStatementsOfTopicRequest,
    GetStatementsOfTopicResponse,
    GetTopicsResponse,
    SearchStatementByTextRequest,
    StatementSearchResponse,
    StatementGetAllResponse,
    StatementSource,
)
from services.content.statement_service import StatementService
from domain.models.statement import Statement
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from domain.models.content_status import ContentStatus
from domain.models.content_origin import SEARCH_QUERY_AUTHOR

router = APIRouter()


# Test endpoint to check if the API is running
@router.get("/")
async def read_test():
    return {"message": "This is a test endpoint"}


# Retrieves all statements from the index
@router.get("/getAll", response_model=StatementGetAllResponse)
async def get_all(
    statement_service: StatementService = Depends(get_statement_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> StatementGetAllResponse:
    try:
        print("/getAll was called")

        offset = (page - 1) * page_size
        statement_index_results = await statement_service.get_all(
            limit=page_size, offset=offset
        )

        print(
            f"/getAll got {len(statement_index_results)} results from statement_index"
        )

        response = StatementGetAllResponse(
            results_count=len(statement_index_results),
            results=statement_index_results,
            total_records_count=await statement_service.count(),
        )

        return response
    except Exception as e:
        print("Error in /getAll: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# Searches for statements in the statement_index using similarity search
@router.post("/searchStatements", response_model=StatementSearchResponse)
async def search_statements(
    request: SearchStatementByTextRequest,
    statement_service: StatementService = Depends(get_statement_service),
) -> StatementSearchResponse:
    try:
        print("/searchStatements was called, request: ", request)

        statement_index_results = await statement_service.search(
            request.query_text, request.limit
        )
        print("/searchStatements statement_index_results: ", statement_index_results)

        response: StatementSearchResponse = StatementSearchResponse(
            results=statement_index_results
        )

        return response
    except Exception as e:
        print("Error in /searchStatements: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# Adds a new statement to the statement_index
@router.post("/addStatement", response_model=AddStatementResponse)
async def add_statement(
    request: AddStatementRequest,
    statement_service: StatementService = Depends(get_statement_service),
    x_user: str = Header(...),
) -> AddStatementResponse:
    try:
        print("/addStatement was called, request: ", request)

        if not x_user:
            raise HTTPException(status_code=400, detail="X-User header missing")

        print(f"X-User header: {x_user}")

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

        # Add statement to the statement index - statements don't require review and are released directly
        statement_was_new, statement_id, statement_text = (
            await statement_service.add_statement(
                statement,
                author,
                ContentStatus.RELEASED_INTERNAL,  # TODO add moderation system
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
        print("Error in /addStatement: ", e)
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
        print("/addReplysuggestionToStatement was called, request: ", request)

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

    except Exception as e:
        # Improve error handling by returning specific exception types
        print("Error in /addReplysuggestionToStatement: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# Retrieves the topics of the statement_index
@router.get("/getTopics", response_model=GetTopicsResponse)
def get_topics(
    statement_service: StatementService = Depends(get_statement_service),
) -> GetTopicsResponse:
    try:
        print("statement/getTopics was called")

        statement_index_topics = statement_service.get_topics()

        response: GetTopicsResponse = GetTopicsResponse(topics=statement_index_topics)

        return response
    except Exception as e:
        print("Error in get_statement_topics: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# Retrieves the statements of a specific topic from the statement_index
@router.post("/getStatementsOfTopic", response_model=GetStatementsOfTopicResponse)
def get_statement_topics(
    request: GetStatementsOfTopicRequest,
    statement_service: StatementService = Depends(get_statement_service),
) -> GetStatementsOfTopicResponse:
    try:
        print("/getStatementsOfTopic was called, request: ", request)

        statement_index_results = statement_service.get_items_of_topic(
            request.topic, request.limit
        )

        response: GetStatementsOfTopicResponse = GetStatementsOfTopicResponse(
            results=statement_index_results
        )

        return response
    except Exception as e:
        print("Error in get_statement_topics: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# Retrieves the categories of the statement_index
@router.get("/getCategories", response_model=GetCategoriesResponse)
def get_categories(
    statement_service: StatementService = Depends(get_statement_service),
) -> GetCategoriesResponse:
    try:
        print("statement/getTopics was called")

        statement_index_categories = statement_service.get_categories()

        response: GetCategoriesResponse = GetCategoriesResponse(
            categories=statement_index_categories
        )

        return response
    except Exception as e:
        print("Error in get_statement_topics: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# Retrieves the statements of a specific category from the statement_index
@router.post("/getStatementsOfCategory", response_model=GetStatementsOfCategoryResponse)
def get_statements_of_category(
    request: GetStatementsOfCategoryRequest,
    statement_service: StatementService = Depends(get_statement_service),
) -> GetStatementsOfCategoryResponse:
    try:
        print("/getStatementsOfCategory was called, request: ", request)

        statement_index_results = statement_service.get_items_of_category(
            request.category, request.limit
        )

        response: GetStatementsOfCategoryResponse = GetStatementsOfCategoryResponse(
            results=statement_index_results
        )

        return response
    except Exception as e:
        print("Error in get_statements_of_category: ", e)
        raise HTTPException(status_code=500, detail=str(e))
