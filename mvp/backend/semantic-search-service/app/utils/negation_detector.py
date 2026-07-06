"""
Negation detection utility for German text.

This module provides lightweight, rule-based detection of negations and
sentiment polarity in German political statements and content.
"""

import re
from typing import Literal, Dict
from dataclasses import dataclass

from core.logging import get_logger

logger = get_logger(__name__)

# German negation markers
NEGATION_MARKERS = {
    "nicht",  # not
    "kein",
    "keine",
    "keinen",
    "keiner",
    "keines",  # no/none
    "niemals",
    "nie",  # never
    "nichts",  # nothing
    "weder",  # neither
    "ohne",  # without
    "kaum",  # hardly
}

# Context words that might indicate negation is not actually negating the main statement
NEGATION_CANCELATION_PATTERNS = [
    r"nicht\s+nur",  # not only (positive context)
    r"ohne\s+zweifel",  # without doubt (positive context)
]

# Words that indicate importance/positive stance
POSITIVE_INDICATORS = {
    "wichtig",
    "wesentlich",
    "bedeutsam",
    "entscheidend",
    "notwendig",
    "unerlässlich",
    "gut",
    "richtig",
    "sinnvoll",
    "fördern",
    "unterstützen",
    "stärken",
}

# Words that indicate negative stance/dismissal
NEGATIVE_INDICATORS = {
    "unwichtig",
    "unbedeutend",
    "überbewertet",
    "übertrieben",
    "falsch",
    "schlecht",
    "unsinnig",
    "ablehnen",
    "verhindern",
    "schwächen",
}


@dataclass
class PolarityAnalysis:
    """Result of polarity analysis."""

    polarity: Literal["positive", "negative", "neutral"]
    confidence: float  # 0.0 to 1.0
    negation_detected: bool
    negative_stance_words: list[str]
    explanation: str


def normalize_text(text: str) -> str:
    """Normalize text for analysis (lowercase, basic cleanup)."""
    return text.lower().strip()


def has_negation_cancelation(text: str) -> bool:
    """Check if negation is canceled by context (e.g., 'nicht nur')."""
    text_normalized = normalize_text(text)
    for pattern in NEGATION_CANCELATION_PATTERNS:
        if re.search(pattern, text_normalized):
            return True
    return False


def detect_negation_markers(text: str) -> list[str]:
    """Detect negation marker words in text."""
    text_normalized = normalize_text(text)
    words = text_normalized.split()

    found_negations = []
    for word in words:
        # Remove punctuation for matching
        clean_word = re.sub(r"[^\w]", "", word)
        if clean_word in NEGATION_MARKERS:
            found_negations.append(clean_word)

    return found_negations


def detect_stance_words(
    text: str,
) -> tuple[list[str], list[str]]:
    """Detect positive and negative stance indicator words."""
    text_normalized = normalize_text(text)
    words = text_normalized.split()

    positive_words = []
    negative_words = []

    for word in words:
        # Remove punctuation for matching
        clean_word = re.sub(r"[^\w]", "", word)

        if clean_word in POSITIVE_INDICATORS:
            positive_words.append(clean_word)
        elif clean_word in NEGATIVE_INDICATORS:
            negative_words.append(clean_word)

    return positive_words, negative_words


def analyze_polarity(text: str) -> PolarityAnalysis:
    """
    Analyze the polarity (positive/negative/neutral stance) of a text.

    This uses simple rule-based heuristics:
    1. Detect negation markers (nicht, kein, etc.)
    2. Detect stance words (wichtig, unwichtig, etc.)
    3. Combine to determine overall polarity

    Args:
        text: The text to analyze

    Returns:
        PolarityAnalysis with polarity classification and metadata
    """
    if not text or len(text.strip()) == 0:
        return PolarityAnalysis(
            polarity="neutral",
            confidence=1.0,
            negation_detected=False,
            negative_stance_words=[],
            explanation="Empty text",
        )

    # Check for negation cancelation first
    if has_negation_cancelation(text):
        logger.debug(f"Negation cancelation detected in: {text}")
        # Treat as if no negation
        return PolarityAnalysis(
            polarity="neutral",
            confidence=0.5,
            negation_detected=False,
            negative_stance_words=[],
            explanation="Negation canceled by context (e.g., 'nicht nur')",
        )

    # Detect components
    negations = detect_negation_markers(text)
    positive_words, negative_words = detect_stance_words(text)

    # Determine polarity
    has_negation = len(negations) > 0
    has_positive_stance = len(positive_words) > 0
    has_negative_stance = len(negative_words) > 0

    # Decision logic
    if has_negative_stance:
        # Explicit negative words trump everything
        polarity = "negative"
        confidence = 0.9
        explanation = f"Negative stance words: {', '.join(negative_words)}"

    elif has_negation and has_positive_stance:
        # Negation + positive word = negative ("nicht wichtig" = negative)
        polarity = "negative"
        confidence = 0.85
        explanation = (
            f"Negation ({', '.join(negations)}) + "
            f"positive word ({', '.join(positive_words)}) = negative stance"
        )

    elif has_positive_stance:
        # Positive word without negation = positive
        polarity = "positive"
        confidence = 0.8
        explanation = f"Positive stance words: {', '.join(positive_words)}"

    elif has_negation:
        # Negation alone (without stance words) = likely negative
        polarity = "negative"
        confidence = 0.6
        explanation = f"Negation detected: {', '.join(negations)}"

    else:
        # No clear indicators
        polarity = "neutral"
        confidence = 0.7
        explanation = "No clear polarity indicators"

    return PolarityAnalysis(
        polarity=polarity,
        confidence=confidence,
        negation_detected=has_negation,
        negative_stance_words=negative_words,
        explanation=explanation,
    )


def polarities_match(
    polarity1: Literal["positive", "negative", "neutral"],
    polarity2: Literal["positive", "negative", "neutral"],
) -> bool:
    """
    Check if two polarities are compatible (not contradictory).

    Returns:
        True if polarities match or are compatible, False if contradictory
    """
    # If either is neutral, they're compatible
    if polarity1 == "neutral" or polarity2 == "neutral":
        return True

    # Otherwise they must be the same
    return polarity1 == polarity2


def calculate_polarity_penalty(
    query_polarity: Literal["positive", "negative", "neutral"],
    result_polarity: Literal["positive", "negative", "neutral"],
    query_confidence: float,
    result_confidence: float,
) -> float:
    """
    Calculate a penalty multiplier for polarity mismatch.

    Args:
        query_polarity: Polarity of the search query
        result_polarity: Polarity of the search result
        query_confidence: Confidence in query polarity (0-1)
        result_confidence: Confidence in result polarity (0-1)

    Returns:
        Multiplier between 0.0 and 1.0 to apply to similarity score
        - 1.0 = no penalty (polarities match)
        - 0.8 = light penalty (one is neutral)
        - 0.3 = heavy penalty (polarities contradict)
    """
    # If polarities match, no penalty
    if polarities_match(query_polarity, result_polarity):
        return 1.0

    # Contradictory polarities (positive vs negative)
    # Penalty strength depends on confidence in both polarities
    avg_confidence = (query_confidence + result_confidence) / 2

    # Higher confidence = stronger penalty
    # Low confidence (0.5): penalty = 0.65 (35% reduction)
    # Medium confidence (0.7): penalty = 0.45 (55% reduction)
    # High confidence (0.9): penalty = 0.25 (75% reduction)
    penalty = 1.0 - (avg_confidence * 0.7)

    return max(0.2, min(1.0, penalty))  # Clamp between 0.2 and 1.0
