"""
Keyword overlap service for improving semantic search relevance.

This service boosts scores for results with high keyword overlap and
penalizes results with low keyword overlap, addressing the limitation
where semantically similar but topically different results get high scores.
"""

from typing import TypeVar, Protocol, Generic, Dict
from dataclasses import dataclass

from core.logging import get_logger
from utils.german_stemmer import calculate_keyword_boost, extract_keywords

logger = get_logger(__name__)


@dataclass
class KeywordOverlapResult:
    """Result of keyword overlap analysis."""

    original_score: float
    adjusted_score: float
    keyword_boost_applied: float
    query_keywords: list[str]
    result_keywords: list[str]
    matched_keywords: list[str]
    overlap_ratio: float


class HasScore(Protocol):
    """Protocol for objects that have a score attribute."""

    score: float


T = TypeVar("T", bound=HasScore)


class KeywordOverlapService:
    """
    Service for boosting/penalizing search results based on keyword overlap.

    This addresses the issue where semantically similar but topically different
    results receive high similarity scores. For example:
    - Query: "Windräder töten Vögel" vs Result: "Erneuerbare unzuverlässig"
      → High semantic similarity (0.87) but different topics → penalty applied

    - Query: "E-Autos" vs Result: "E-Autos sind nicht besser"
      → Perfect keyword match → boost applied
    """

    def __init__(
        self,
        enable_boosting: bool = True,
        boost_strength: float = 0.3,
        log_adjustments: bool = True,
    ):
        """
        Initialize the keyword overlap service.

        Args:
            enable_boosting: Whether to enable keyword overlap boosting (default: True)
            boost_strength: Strength of boost/penalty (0.0-1.0, default: 0.3)
                Higher values = stronger effect
            log_adjustments: Whether to log score adjustments (default: True)
        """
        self.enable_boosting = enable_boosting
        self.boost_strength = boost_strength
        self.log_adjustments = log_adjustments

        logger.info(
            f"KeywordOverlapService initialized "
            f"(boosting={'enabled' if enable_boosting else 'disabled'}, "
            f"strength={boost_strength})"
        )

    def analyze_and_boost_results(
        self,
        query_text: str,
        results: list[T],
        get_text_fn: callable,
    ) -> tuple[list[T], dict[str, KeywordOverlapResult]]:
        """
        Analyze and boost search results based on keyword overlap.

        Args:
            query_text: The search query text
            results: List of search results with scores
            get_text_fn: Function to extract text from a result object

        Returns:
            Tuple of (boosted_results, keyword_metadata)
            - boosted_results: Results with adjusted scores
            - keyword_metadata: Dict mapping result ID to keyword overlap metadata
        """
        if not self.enable_boosting:
            logger.debug("Keyword boosting disabled, returning unmodified results")
            return results, {}

        if not results:
            return [], {}

        # Extract query keywords once
        query_keywords = extract_keywords(query_text)

        if self.log_adjustments:
            logger.info(
                f"Query keywords: {query_keywords} (from: '{query_text[:50]}...')"
            )

        # Analyze and adjust results
        keyword_metadata = {}
        boosted_results = []

        for result in results:
            # Extract text and keywords
            result_text = get_text_fn(result)
            result_keywords = extract_keywords(result_text)

            # Calculate keyword boost
            boost_multiplier = calculate_keyword_boost(
                query_text, result_text, boost_strength=self.boost_strength
            )

            # Apply boost to score
            original_score = result.score
            adjusted_score = original_score * boost_multiplier
            result.score = adjusted_score

            # Calculate overlap info for metadata
            matched_keywords = list(
                set(query_keywords).intersection(set(result_keywords))
            )
            overlap_ratio = (
                len(matched_keywords) / len(query_keywords) if query_keywords else 1.0
            )

            # Track metadata
            keyword_metadata[getattr(result, "id", str(id(result)))] = (
                KeywordOverlapResult(
                    original_score=original_score,
                    adjusted_score=adjusted_score,
                    keyword_boost_applied=boost_multiplier,
                    query_keywords=query_keywords,
                    result_keywords=result_keywords,
                    matched_keywords=matched_keywords,
                    overlap_ratio=overlap_ratio,
                )
            )

            if self.log_adjustments and abs(boost_multiplier - 1.0) > 0.05:
                result_text_preview = (
                    result_text[:50] + "..." if len(result_text) > 50 else result_text
                )
                logger.info(
                    f"Keyword adjustment: '{result_text_preview}' | "
                    f"overlap={overlap_ratio:.1%}, "
                    f"boost={boost_multiplier:.2f}, "
                    f"score: {original_score:.3f} → {adjusted_score:.3f}, "
                    f"matched: {matched_keywords}"
                )

            boosted_results.append(result)

        # Re-sort by adjusted scores
        boosted_results.sort(key=lambda x: x.score, reverse=True)

        if self.log_adjustments:
            significant_adjustments = sum(
                1
                for m in keyword_metadata.values()
                if abs(m.keyword_boost_applied - 1.0) > 0.05
            )
            logger.info(
                f"Keyword boosting complete: {len(boosted_results)} results, "
                f"{significant_adjustments} significant adjustments"
            )

        return boosted_results, keyword_metadata

    def calculate_boost_for_pair(
        self, text1: str, text2: str
    ) -> tuple[float, KeywordOverlapResult]:
        """
        Calculate keyword boost for a pair of texts.

        Useful for testing and debugging.

        Args:
            text1: First text (query)
            text2: Second text (result)

        Returns:
            Tuple of (boost_multiplier, metadata)
        """
        query_keywords = extract_keywords(text1)
        result_keywords = extract_keywords(text2)
        matched_keywords = list(set(query_keywords).intersection(set(result_keywords)))
        overlap_ratio = (
            len(matched_keywords) / len(query_keywords) if query_keywords else 1.0
        )

        boost_multiplier = calculate_keyword_boost(
            text1, text2, boost_strength=self.boost_strength
        )

        metadata = KeywordOverlapResult(
            original_score=1.0,
            adjusted_score=boost_multiplier,
            keyword_boost_applied=boost_multiplier,
            query_keywords=query_keywords,
            result_keywords=result_keywords,
            matched_keywords=matched_keywords,
            overlap_ratio=overlap_ratio,
        )

        return boost_multiplier, metadata


# Singleton instance
_keyword_overlap_service: KeywordOverlapService | None = None


def get_keyword_overlap_service(
    enable_boosting: bool = True,
    boost_strength: float = 0.3,
) -> KeywordOverlapService:
    """
    Get the singleton keyword overlap service instance.

    Args:
        enable_boosting: Whether to enable boosting (only used on first call)
        boost_strength: Strength of boost/penalty (only used on first call)

    Returns:
        KeywordOverlapService instance
    """
    global _keyword_overlap_service
    if _keyword_overlap_service is None:
        _keyword_overlap_service = KeywordOverlapService(
            enable_boosting=enable_boosting,
            boost_strength=boost_strength,
        )
    return _keyword_overlap_service
