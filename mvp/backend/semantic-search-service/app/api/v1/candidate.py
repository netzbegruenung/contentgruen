import random
from typing import List
import uuid
from fastapi import APIRouter, HTTPException, Depends

from dependencies import (
    get_commentary_service,
    get_settings,
    get_statement_service,
)
from dtos.candidate import ReplySuggestionCandidatesResponse
from services.content.commentary_service import CommentaryService
from domain.models.commentary import CommentarySearchResult
from domain.models.statement import StatementDbEntry
from services.content.statement_service import StatementService
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from domain.models.content import ContentDbEntry
from core.config import Settings

router = APIRouter()


# Test endpoint to check if the API is running
@router.get("/")
async def read_test():
    return {"message": "This is a test endpoint"}


# TODO: Refactor this to properly split responsiblity between api, models and index manager
@router.get(
    "/replysuggestionCandidates", response_model=ReplySuggestionCandidatesResponse
)
async def get_replysuggestion_candidates(
    statement_id: str,
    limit: int = 10,
    settings: Settings = Depends(get_settings),
    statement_service: StatementService = Depends(get_statement_service),
    commentary_service: CommentaryService = Depends(get_commentary_service),
) -> ReplySuggestionCandidatesResponse:
    try:
        print(
            f"/replysuggestionCandidates was called, statement_id: {statement_id}, limit: {limit}"
        )

        # get requested statement from statement index
        try:
            parsed_statement_id = uuid.UUID(statement_id)
            statement_result: StatementDbEntry = await statement_service.get(
                parsed_statement_id
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail="Statement not found")

        good_reply_suggestions = [
            suggestion
            for suggestion in statement_result.replysuggestions
            if suggestion.relevance > 0.6  # TODO: Make this a parameter
        ]
        print("good_reply_suggestions: ", good_reply_suggestions)

        # choose a random good reply suggestion
        if len(good_reply_suggestions) > 0:
            randomindex = random.randint(0, len(good_reply_suggestions) - 1)
            chosen_reply_suggestion = good_reply_suggestions[randomindex]
            print("Chosen good reply suggestion: ", chosen_reply_suggestion)

        else:
            chosen_reply_suggestion = None
            print("No good existing reply suggestion found")

        if chosen_reply_suggestion:
            print("Retrieving commentarys similar to the chosen reply suggestion")

            # get text of the replysuggestions by getting from the content index
            repository_factory = QdrantRepositoryFactory()
            content_repository = repository_factory.create_content_repository(settings)
            chosen_reply_suggestion_content: ContentDbEntry = (
                await content_repository.get(chosen_reply_suggestion.id)
            )  # TODO introduce index managers for aggregated indexes

            # search for similar commentaries from commentary index
            commentary_results: List[CommentarySearchResult] = (
                await commentary_service.search(
                    chosen_reply_suggestion_content.text, limit
                )
            )
            print("commentary_result: ", commentary_results)

        # ### Approach 2: Find similar statements and TBD

        # # get similar statements from statement index
        # statement_index_results = statement_index.search(statement["text"], 5)
        # print("statement_index_results: ", statement_index_results)

        # existing_reply_suggestions_of_similar_statements = []

        # for statement_result in statement_index_results:
        #     reply_suggestions = json.loads(statement_result["reply_suggestions"])
        #     existing_reply_suggestions_of_similar_statements.extend(reply_suggestions)

        # print("Existing reply suggestions of similar statements: ",existing_reply_suggestions_of_similar_statements)

        # # filter for only reply suggestion with a rating over 0.6 and extract texts
        # reply_suggestion_texts = [
        #     reply_suggestion["text"]
        #     for reply_suggestion in existing_reply_suggestions_of_similar_statements
        #     if reply_suggestion["rating"] > 0.6 #TODO: Make this a parameter
        # ]

        # # choose a random reply suggestion
        # if len(reply_suggestion_texts) > 0:
        #     randomindex = random.randint(0, len(reply_suggestion_texts) - 1)
        #     chosen_reply_suggestion_text = (reply_suggestion_texts[randomindex])
        #     print("Chosen reply suggestion: ", chosen_reply_suggestion_text)
        # else:
        #     chosen_existing_reply_suggestion_of_similar_statement = None
        #     print("No existing reply suggestion with rating over 0.6 found")#TODO: Make this a parameter

        # if chosen_existing_reply_suggestion_of_similar_statement != None:
        #     print("Retrieving content similar to the chosen existing reply suggestion")

        #     # search for similar content in content index
        #     content_index_results_two = content_repository.search(query_text=chosen_reply_suggestion_text, limit=10)
        #     print("content_index_results_two: ", content_index_results_two)

        #     # convert results into custom Dto Response
        #     results_two: List[ReplySuggestionCandidate] = [
        #         ReplySuggestionCandidate(
        #             content_id=res["id"],
        #             score=res["score"], #TODO: Improve this to make it meaningful
        #             text=res["text"],
        #             type=res["type"],
        #             created=res["created"],
        #             last_modified=res["last_modified"],
        #         )
        #         for res in content_index_results_two
        #     ]
        #     results.extend(results_two)

        # ### Combine results one and two

        # # deduplicate results
        # results = list({result.content_id: result for result in results}.values())

        # # sort results by score
        # results.sort(key=lambda x: x.score, reverse=True)

        # # filter out already existing reply candidates
        # results = [
        #     result
        #     for result in results
        #     if result.content_id not in reply_suggestion_texts
        # ]
        # print("results: ", results)

        response: ReplySuggestionCandidatesResponse = ReplySuggestionCandidatesResponse(
            commentary_results=commentary_results
        )

        return response

    except Exception as e:
        # TODO Improve error handling be returning specific expection types for e.g. not found
        print("Error: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# getSourceCandidates()


# getSummaryCandidates()
