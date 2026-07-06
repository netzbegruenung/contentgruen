from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import numpy as np

from dependencies import get_settings
from dtos.content import ContentSearchResponse, SearchContentByTextRequest
from repositories.aggregated.content_repository import (
    ContentRepository,
)
from domain.models.content import ContentSearchResult
from core.config import Settings
from services.embeddings.qdrant_embeddings_manager import get_embeddings_manager
from services.polarity_filter_service import PolarityFilterService
from services.keyword_overlap_service import KeywordOverlapService
from utils.negation_detector import analyze_polarity, calculate_polarity_penalty
from utils.german_stemmer import extract_keywords, calculate_keyword_boost
from core.logging import get_logger

logger = get_logger(__name__)


router = APIRouter()


# Test endpoint to check if the API is running
@router.get("/")
async def read_test():
    return {"message": "This is a test endpoint"}


@router.get("/headers")
async def test_headers(request: Request):
    headers = request.headers  # Get all headers
    print("Received headers:")
    for header, value in headers.items():
        print(f"{header}: {value}")
    return {"message": "Headers logged!"}


# Test endpoint to check for content in the test index
@router.post("/test_searchContent", response_model=ContentSearchResponse)
def test_search_content(
    request: SearchContentByTextRequest, settings: Settings = Depends(get_settings)
) -> ContentSearchResponse:
    try:
        print("/test_searchContent was called, request: ", request)

        test_content_repository = ContentRepository(settings)
        test_content_index_results: List[ContentSearchResult] = (
            test_content_repository.search(request.query_text, request.limit)
        )
        print(
            "/test_searchContent test_content_index_results: ",
            test_content_index_results,
        )

        response: ContentSearchResponse = ContentSearchResponse(
            results=test_content_index_results
        )

        return response
    except Exception as e:
        print("Error in test_search_content: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# DTOs for similarity testing
class SimilarityTestRequest(BaseModel):
    text1: str = Field(..., min_length=1, description="First text to compare")
    text2: str = Field(..., min_length=1, description="Second text to compare")
    prefix_mode: Literal[
        "default", "query-query", "query-passage", "passage-passage"
    ] = Field(
        default="default",
        description=(
            "Prefix strategy: 'default' (passage-passage), "
            "'query-query', 'query-passage', or 'passage-passage'"
        ),
    )
    include_embeddings: bool = Field(
        default=False,
        description="Include embedding vectors in response (for debugging)",
    )


class SimilarityTestResponse(BaseModel):
    similarity_score: float = Field(
        ..., description="Cosine similarity score between the two texts (0-1 range)"
    )
    text1_prefix: str = Field(..., description="Prefix used for text1")
    text2_prefix: str = Field(..., description="Prefix used for text2")
    text1_length: int = Field(..., description="Character length of text1")
    text2_length: int = Field(..., description="Character length of text2")
    embedding1: Optional[List[float]] = Field(
        None, description="Embedding vector for text1 (if requested)"
    )
    embedding2: Optional[List[float]] = Field(
        None, description="Embedding vector for text2 (if requested)"
    )
    model_info: dict = Field(
        default_factory=lambda: {
            "model_name": "intfloat/multilingual-e5-base",
            "embedding_dim": 768,
            "distance_metric": "cosine",
            "normalized": True,
        },
        description="Information about the embedding model used",
    )


@router.post("/similarity", response_model=SimilarityTestResponse)
async def test_similarity(request: SimilarityTestRequest) -> SimilarityTestResponse:
    """
    Test similarity between two texts using the same embedding model and method
    used in production search.

    This endpoint helps you:
    - Understand similarity scores between different texts
    - Debug why some texts have unexpectedly similar/different scores
    - Experiment with different prefix strategies (query vs passage)
    - Validate that your embedding model is working as expected

    Note: This endpoint does not persist any data to Qdrant - it's purely
    for testing and experimentation.
    """
    try:
        logger.info(
            f"Similarity test: text1_len={len(request.text1)}, "
            f"text2_len={len(request.text2)}, mode={request.prefix_mode}"
        )

        # Get the embeddings manager
        embeddings_manager = get_embeddings_manager()

        if not embeddings_manager.is_started:
            raise HTTPException(status_code=503, detail="Embeddings service not ready")

        # Determine prefixes based on mode
        if request.prefix_mode == "default" or request.prefix_mode == "passage-passage":
            prefix1 = "passage"
            prefix2 = "passage"
        elif request.prefix_mode == "query-query":
            prefix1 = "query"
            prefix2 = "query"
        elif request.prefix_mode == "query-passage":
            prefix1 = "query"
            prefix2 = "passage"
        else:
            raise HTTPException(
                status_code=400, detail=f"Invalid prefix_mode: {request.prefix_mode}"
            )

        # Encode both texts with appropriate prefixes
        prefixed_text1 = f"{prefix1}: {request.text1}"
        prefixed_text2 = f"{prefix2}: {request.text2}"

        embedding1 = embeddings_manager.model.encode(
            prefixed_text1, normalize_embeddings=True
        )
        embedding2 = embeddings_manager.model.encode(
            prefixed_text2, normalize_embeddings=True
        )

        # Calculate cosine similarity
        # For normalized vectors, cosine similarity = dot product
        similarity = float(np.dot(embedding1, embedding2))

        # Ensure similarity is in valid range [0, 1] for cosine with normalized vectors
        # (due to floating point precision, might occasionally exceed 1.0 slightly)
        similarity = max(0.0, min(1.0, similarity))

        logger.info(
            f"Similarity calculated: {similarity:.4f} "
            f"(mode={request.prefix_mode}, {prefix1}/{prefix2})"
        )

        # Build response
        response = SimilarityTestResponse(
            similarity_score=similarity,
            text1_prefix=prefix1,
            text2_prefix=prefix2,
            text1_length=len(request.text1),
            text2_length=len(request.text2),
        )

        # Include embeddings if requested
        if request.include_embeddings:
            response.embedding1 = embedding1.tolist()
            response.embedding2 = embedding2.tolist()

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in similarity test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# DTOs for polarity testing
class PolarityTestRequest(BaseModel):
    text1: str = Field(
        ..., min_length=1, description="First text to analyze (e.g., query)"
    )
    text2: str = Field(
        ..., min_length=1, description="Second text to analyze (e.g., result)"
    )
    original_similarity_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Original similarity score to apply polarity penalty to (optional)",
    )


class PolarityAnalysisDetail(BaseModel):
    text: str = Field(..., description="The analyzed text")
    polarity: Literal["positive", "negative", "neutral"] = Field(
        ..., description="Detected polarity"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in polarity detection"
    )
    negation_detected: bool = Field(..., description="Whether negation was detected")
    negative_stance_words: List[str] = Field(
        default_factory=list, description="List of negative stance words found"
    )
    explanation: str = Field(..., description="Explanation of polarity detection")


class PolarityTestResponse(BaseModel):
    text1_analysis: PolarityAnalysisDetail = Field(
        ..., description="Polarity analysis of text1"
    )
    text2_analysis: PolarityAnalysisDetail = Field(
        ..., description="Polarity analysis of text2"
    )
    polarities_match: bool = Field(
        ..., description="Whether the polarities are compatible (not contradictory)"
    )
    polarity_mismatch_detected: bool = Field(
        ..., description="Whether contradictory polarity was detected"
    )
    polarity_penalty: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Penalty multiplier (1.0 = no penalty, lower = stronger penalty)",
    )
    original_score: Optional[float] = Field(
        None, description="Original similarity score (if provided)"
    )
    adjusted_score: Optional[float] = Field(
        None, description="Score after applying polarity penalty (if original provided)"
    )
    score_reduction_percent: Optional[float] = Field(
        None,
        description="Percentage of score reduction due to polarity (if applicable)",
    )


@router.post("/polarity", response_model=PolarityTestResponse)
async def test_polarity(request: PolarityTestRequest) -> PolarityTestResponse:
    """
    Test polarity analysis and filtering between two texts.

    This endpoint helps you:
    - Understand how polarity detection works for German political statements
    - See if two texts have matching or contradictory polarities
    - Calculate the penalty applied to search results with mismatched polarity
    - Debug why certain results are being filtered or downranked
    - Test the impact of polarity filtering on similarity scores

    Example use cases:
    - Query: "Klimaschutz ist wichtig" vs Result: "Klimaschutz ist nicht wichtig"
      → Should detect negative polarity in result and apply penalty
    - Query: "Migration fördern" vs Result: "Migration verhindern"
      → Should detect contradictory action verbs and apply penalty
    - Query: "Erneuerbare Energien" vs Result: "Erneuerbare Energien sind wichtig"
      → Should detect neutral query + positive result = no penalty

    Note: This endpoint does not modify any data - it's purely for testing.
    """
    try:
        logger.info(
            f"Polarity test: text1_len={len(request.text1)}, text2_len={len(request.text2)}"
        )

        # Analyze both texts
        analysis1 = analyze_polarity(request.text1)
        analysis2 = analyze_polarity(request.text2)

        logger.debug(
            f"Text1 polarity: {analysis1.polarity} (confidence: {analysis1.confidence:.2f})"
        )
        logger.debug(
            f"Text2 polarity: {analysis2.polarity} (confidence: {analysis2.confidence:.2f})"
        )

        # Calculate penalty
        penalty = calculate_polarity_penalty(
            analysis1.polarity,
            analysis2.polarity,
            analysis1.confidence,
            analysis2.confidence,
        )

        # Check if polarities match
        polarities_match = penalty >= 1.0
        mismatch_detected = penalty < 1.0

        # Calculate adjusted score if original score provided
        adjusted_score = None
        score_reduction = None
        if request.original_similarity_score is not None:
            adjusted_score = request.original_similarity_score * penalty
            score_reduction = (1.0 - penalty) * 100

        logger.info(
            f"Polarity comparison: {analysis1.polarity} vs {analysis2.polarity}, "
            f"penalty={penalty:.2f}, mismatch={mismatch_detected}"
        )

        # Build response
        response = PolarityTestResponse(
            text1_analysis=PolarityAnalysisDetail(
                text=request.text1,
                polarity=analysis1.polarity,
                confidence=analysis1.confidence,
                negation_detected=analysis1.negation_detected,
                negative_stance_words=analysis1.negative_stance_words,
                explanation=analysis1.explanation,
            ),
            text2_analysis=PolarityAnalysisDetail(
                text=request.text2,
                polarity=analysis2.polarity,
                confidence=analysis2.confidence,
                negation_detected=analysis2.negation_detected,
                negative_stance_words=analysis2.negative_stance_words,
                explanation=analysis2.explanation,
            ),
            polarities_match=polarities_match,
            polarity_mismatch_detected=mismatch_detected,
            polarity_penalty=penalty,
            original_score=request.original_similarity_score,
            adjusted_score=adjusted_score,
            score_reduction_percent=score_reduction,
        )

        return response

    except Exception as e:
        logger.error(f"Error in polarity test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# DTOs for keyword overlap testing
class KeywordOverlapTestRequest(BaseModel):
    text1: str = Field(
        ..., min_length=1, description="First text to analyze (e.g., query)"
    )
    text2: str = Field(
        ..., min_length=1, description="Second text to analyze (e.g., result)"
    )
    original_similarity_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Original similarity score to apply keyword boost to (optional)",
    )
    boost_strength: Optional[float] = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="Strength of keyword boost/penalty (default: 0.3)",
    )


class KeywordOverlapTestResponse(BaseModel):
    text1_keywords: List[str] = Field(..., description="Stemmed keywords from text1")
    text2_keywords: List[str] = Field(..., description="Stemmed keywords from text2")
    matched_keywords: List[str] = Field(
        ..., description="Keywords that appear in both texts"
    )
    overlap_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Ratio of query keywords found in result (0.0-1.0)",
    )
    keyword_boost: float = Field(
        ...,
        description="Keyword overlap boost multiplier (0.7-1.3 typically)",
    )
    original_score: Optional[float] = Field(
        None, description="Original similarity score (if provided)"
    )
    adjusted_score: Optional[float] = Field(
        None, description="Score after applying keyword boost (if original provided)"
    )
    score_change_percent: Optional[float] = Field(
        None, description="Percentage of score change due to keywords (if applicable)"
    )


@router.post("/keyword-overlap", response_model=KeywordOverlapTestResponse)
async def test_keyword_overlap(
    request: KeywordOverlapTestRequest,
) -> KeywordOverlapTestResponse:
    """
    Test keyword overlap analysis and boosting between two texts.

    This endpoint helps you:
    - See which keywords are extracted from each text
    - Understand keyword matching and stemming
    - Calculate the keyword overlap boost/penalty
    - Test the impact of keyword overlap on similarity scores

    The keyword overlap system:
    - Extracts meaningful words (removes stop words)
    - Stems words using German CISTEM algorithm (Auto → Aut, Autos → Aut)
    - Calculates overlap ratio
    - Applies boost (high overlap) or penalty (low overlap)

    Example use cases:
    - Query: "E-Autos" vs Result: "E-Autos sind nicht besser"
      → High keyword overlap → boost score
    - Query: "Windräder töten Vögel" vs Result: "Erneuerbare unzuverlässig"
      → Low keyword overlap → penalize score

    Note: This endpoint does not modify any data - it's purely for testing.
    """
    try:
        logger.info(
            f"Keyword overlap test: text1_len={len(request.text1)}, text2_len={len(request.text2)}"
        )

        # Extract keywords
        text1_keywords = extract_keywords(request.text1)
        text2_keywords = extract_keywords(request.text2)

        # Calculate matched keywords
        matched_keywords = list(set(text1_keywords).intersection(set(text2_keywords)))

        # Calculate overlap ratio
        overlap_ratio = (
            len(matched_keywords) / len(text1_keywords) if text1_keywords else 1.0
        )

        # Calculate keyword boost
        keyword_boost = calculate_keyword_boost(
            request.text1, request.text2, boost_strength=request.boost_strength
        )

        logger.info(
            f"Keyword overlap: {overlap_ratio:.1%}, "
            f"boost={keyword_boost:.2f}, "
            f"matched: {matched_keywords}"
        )

        # Calculate adjusted score if original provided
        adjusted_score = None
        score_change = None
        if request.original_similarity_score is not None:
            adjusted_score = request.original_similarity_score * keyword_boost
            score_change = (keyword_boost - 1.0) * 100

        # Build response
        response = KeywordOverlapTestResponse(
            text1_keywords=text1_keywords,
            text2_keywords=text2_keywords,
            matched_keywords=matched_keywords,
            overlap_ratio=overlap_ratio,
            keyword_boost=keyword_boost,
            original_score=request.original_similarity_score,
            adjusted_score=adjusted_score,
            score_change_percent=score_change,
        )

        return response

    except Exception as e:
        logger.error(f"Error in keyword overlap test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
