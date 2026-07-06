"""
Polarity filtering service for search results.

This service filters and adjusts search results based on polarity mismatch
between query and results to reduce contradictory content in search results.
"""

from typing import TypeVar, Generic, Protocol
from dataclasses import dataclass

from core.logging import get_logger
from utils.negation_detector import (
    analyze_polarity,
    PolarityAnalysis,
    calculate_polarity_penalty,
)

logger = get_logger(__name__)


@dataclass
class PolarityFilterResult:
    """Result of polarity filtering including metadata."""

    original_score: float
    adjusted_score: float
    polarity_penalty_applied: float
    polarity_mismatch_detected: bool
    query_polarity: str
    result_polarity: str
    explanation: str


class HasScore(Protocol):
    """Protocol for objects that have a score attribute."""

    score: float


T = TypeVar("T", bound=HasScore)


class PolarityFilterService:
    """
    Service for filtering search results based on polarity matching.

    This helps reduce contradictory results where the query has opposite
    polarity to the result (e.g., query: "Climate protection is important",
    result: "Climate protection is not important").
    """

    def __init__(self, enable_filtering: bool = True):
        """
        Initialize the polarity filter service.

        Args:
            enable_filtering: Whether to enable polarity filtering (default: True)
        """
        self.enable_filtering = enable_filtering
        logger.info(
            f"PolarityFilterService initialized (filtering={'enabled' if enable_filtering else 'disabled'})"
        )

    def analyze_and_filter_statement_results(
        self,
        query_text: str,
        statement_results: list[T],
        get_text_fn: callable,
    ) -> tuple[list[T], dict[str, PolarityFilterResult]]:
        """
        Analyze and filter statement search results based on polarity.

        Args:
            query_text: The search query text
            statement_results: List of statement search results with scores
            get_text_fn: Function to extract text from a result object

        Returns:
            Tuple of (filtered_results, polarity_metadata)
            - filtered_results: Results with adjusted scores
            - polarity_metadata: Dict mapping result ID to polarity filter metadata
        """
        if not self.enable_filtering:
            logger.debug("Polarity filtering disabled, returning unfiltered results")
            return statement_results, {}

        if not statement_results:
            return [], {}

        # Analyze query polarity
        query_analysis = analyze_polarity(query_text)
        logger.info(
            f"Query polarity: {query_analysis.polarity} "
            f"(confidence: {query_analysis.confidence:.2f}, "
            f"explanation: {query_analysis.explanation})"
        )

        # Filter and adjust results
        polarity_metadata = {}
        filtered_results = []

        for result in statement_results:
            # Extract text and analyze
            result_text = get_text_fn(result)
            result_analysis = analyze_polarity(result_text)

            # Calculate penalty
            penalty = calculate_polarity_penalty(
                query_analysis.polarity,
                result_analysis.polarity,
                query_analysis.confidence,
                result_analysis.confidence,
            )

            # Apply penalty to score
            original_score = result.score
            adjusted_score = original_score * penalty
            result.score = adjusted_score

            # Track metadata
            mismatch_detected = penalty < 1.0
            polarity_metadata[getattr(result, "id", str(id(result)))] = (
                PolarityFilterResult(
                    original_score=original_score,
                    adjusted_score=adjusted_score,
                    polarity_penalty_applied=penalty,
                    polarity_mismatch_detected=mismatch_detected,
                    query_polarity=query_analysis.polarity,
                    result_polarity=result_analysis.polarity,
                    explanation=(
                        f"Query: {query_analysis.explanation} | "
                        f"Result: {result_analysis.explanation}"
                    ),
                )
            )

            if mismatch_detected:
                logger.debug(
                    f"Polarity mismatch: query={query_analysis.polarity}, "
                    f"result={result_analysis.polarity}, "
                    f"penalty={penalty:.2f}, "
                    f"score: {original_score:.3f} → {adjusted_score:.3f}"
                )

            filtered_results.append(result)

        # Re-sort by adjusted scores
        filtered_results.sort(key=lambda x: x.score, reverse=True)

        logger.info(
            f"Polarity filtering complete: {len(filtered_results)} results, "
            f"{sum(1 for m in polarity_metadata.values() if m.polarity_mismatch_detected)} mismatches detected"
        )

        return filtered_results, polarity_metadata

    def check_polarity_mismatch(
        self, text1: str, text2: str
    ) -> tuple[bool, PolarityFilterResult]:
        """
        Check if two texts have mismatched polarity.

        Useful for quick polarity comparison without full result filtering.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Tuple of (has_mismatch, polarity_metadata)
        """
        analysis1 = analyze_polarity(text1)
        analysis2 = analyze_polarity(text2)

        penalty = calculate_polarity_penalty(
            analysis1.polarity,
            analysis2.polarity,
            analysis1.confidence,
            analysis2.confidence,
        )

        mismatch = penalty < 1.0

        metadata = PolarityFilterResult(
            original_score=1.0,
            adjusted_score=penalty,
            polarity_penalty_applied=penalty,
            polarity_mismatch_detected=mismatch,
            query_polarity=analysis1.polarity,
            result_polarity=analysis2.polarity,
            explanation=f"Text1: {analysis1.explanation} | Text2: {analysis2.explanation}",
        )

        return mismatch, metadata


# Singleton instance
_polarity_filter_service: PolarityFilterService | None = None


def get_polarity_filter_service(
    enable_filtering: bool = True,
) -> PolarityFilterService:
    """
    Get the singleton polarity filter service instance.

    Args:
        enable_filtering: Whether to enable filtering (only used on first call)

    Returns:
        PolarityFilterService instance
    """
    global _polarity_filter_service
    if _polarity_filter_service is None:
        _polarity_filter_service = PolarityFilterService(
            enable_filtering=enable_filtering
        )
    return _polarity_filter_service
