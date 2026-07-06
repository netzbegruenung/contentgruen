"""
Lightweight German stemmer using CISTEM algorithm.

CISTEM (Context-Independent Stemmer) is optimized for German text
and provides good performance without requiring external dependencies.
"""

import re
from typing import List, Set


def stem_german(word: str) -> str:
    """
    Stem a German word using the CISTEM algorithm.

    Args:
        word: The word to stem

    Returns:
        Stemmed version of the word
    """
    word = word.lower().strip()

    if len(word) <= 2:
        return word

    # Replace umlauts
    word = word.replace("ä", "a")
    word = word.replace("ö", "o")
    word = word.replace("ü", "u")
    word = word.replace("ß", "ss")

    # Remove genitiv-s
    if word.endswith("s") and len(word) >= 3:
        # Check if it's likely a genitiv-s (preceded by consonant)
        if word[-2] not in "aeiou":
            word = word[:-1]

    # Strip common suffixes
    suffixes = [
        "ern",
        "em",
        "er",
        "en",
        "es",
        "e",
        "s",
    ]

    for suffix in suffixes:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            break

    return word


def extract_keywords(
    text: str, min_length: int = 3, stop_words: Set[str] = None
) -> List[str]:
    """
    Extract meaningful keywords from German text.

    Args:
        text: The text to extract keywords from
        min_length: Minimum word length to consider (default: 3)
        stop_words: Set of stop words to exclude (optional)

    Returns:
        List of stemmed keywords
    """
    if stop_words is None:
        stop_words = GERMAN_STOP_WORDS

    # Lowercase and split into words
    text = text.lower()

    # Extract words (alphanumeric with hyphens)
    words = re.findall(r"[\w-]+", text)

    # Filter and stem
    keywords = []
    for word in words:
        # Skip if too short
        if len(word) < min_length:
            continue

        # Skip stop words
        if word in stop_words:
            continue

        # Skip if it's just numbers
        if word.isdigit():
            continue

        # Handle hyphenated compounds (e.g., "Vogel-Schredder" → ["vogel", "schredder"])
        if "-" in word:
            # Split by hyphen and process each part
            parts = word.split("-")
            for part in parts:
                # Skip very short parts (like "e" in "e-auto")
                if len(part) >= min_length:
                    if part not in stop_words and not part.isdigit():
                        stemmed = stem_german(part)
                        if stemmed and len(stemmed) >= min_length:
                            keywords.append(stemmed)
        else:
            # Stem the word normally
            stemmed = stem_german(word)
            if stemmed and len(stemmed) >= min_length:
                keywords.append(stemmed)

    return keywords


def calculate_keyword_overlap(
    query_keywords: List[str], result_keywords: List[str]
) -> float:
    """
    Calculate keyword overlap ratio between query and result.

    Args:
        query_keywords: Keywords from the query
        result_keywords: Keywords from the result

    Returns:
        Overlap ratio between 0.0 and 1.0
    """
    if not query_keywords:
        return 1.0  # Neutral if no keywords in query

    query_set = set(query_keywords)
    result_set = set(result_keywords)

    # Count matches
    matches = len(query_set.intersection(result_set))

    # Calculate ratio
    overlap = matches / len(query_set)

    return overlap


def calculate_keyword_boost(
    query_text: str, result_text: str, boost_strength: float = 0.3
) -> float:
    """
    Calculate a multiplier to boost/penalize similarity scores based on keyword overlap.

    Args:
        query_text: The search query
        result_text: The result text
        boost_strength: How strong the boost/penalty should be (0.0-1.0)
            Higher = stronger effect (default: 0.3)

    Returns:
        Multiplier between (1.0 - boost_strength) and (1.0 + boost_strength)
        - 1.0 = no change
        - >1.0 = boost (high keyword overlap)
        - <1.0 = penalty (low keyword overlap)

    Examples:
        overlap=100%, boost_strength=0.3 → 1.3 (30% boost)
        overlap=50%, boost_strength=0.3 → 1.0 (no change)
        overlap=0%, boost_strength=0.3 → 0.7 (30% penalty)
    """
    # Extract keywords
    query_keywords = extract_keywords(query_text)
    result_keywords = extract_keywords(result_text)

    # Calculate overlap
    overlap_ratio = calculate_keyword_overlap(query_keywords, result_keywords)

    # Convert overlap to multiplier
    # overlap=0.0 → multiplier=(1.0 - boost_strength)
    # overlap=0.5 → multiplier=1.0
    # overlap=1.0 → multiplier=(1.0 + boost_strength)
    multiplier = 1.0 + ((overlap_ratio - 0.5) * 2 * boost_strength)

    # Clamp to reasonable range
    min_multiplier = 1.0 - boost_strength
    max_multiplier = 1.0 + boost_strength
    multiplier = max(min_multiplier, min(max_multiplier, multiplier))

    return multiplier


# Common German stop words (function words with little semantic meaning)
GERMAN_STOP_WORDS = {
    "der",
    "die",
    "das",
    "den",
    "dem",
    "des",
    "ein",
    "eine",
    "einer",
    "eines",
    "einem",
    "einen",
    "und",
    "oder",
    "aber",
    "doch",
    "sondern",
    "als",
    "wenn",
    "weil",
    "da",
    "damit",
    "dass",
    "obwohl",
    "ist",
    "sind",
    "war",
    "waren",
    "wird",
    "werden",
    "wurde",
    "wurden",
    "hat",
    "haben",
    "hatte",
    "hatten",
    "sein",
    "seine",
    "seiner",
    "seinem",
    "seinen",
    "ihr",
    "ihre",
    "ihrer",
    "ihrem",
    "ihren",
    "mein",
    "meine",
    "meiner",
    "meinem",
    "meinen",
    "dein",
    "deine",
    "deiner",
    "deinem",
    "deinen",
    "von",
    "zu",
    "bei",
    "mit",
    "nach",
    "vor",
    "auf",
    "fur",
    "für",
    "an",
    "in",
    "aus",
    "uber",
    "über",
    "unter",
    "durch",
    "um",
    "gegen",
    "ohne",
    "bis",
    "ich",
    "du",
    "er",
    "sie",
    "es",
    "wir",
    "ihr",
    "sie",
    "man",
    "sich",
    "nicht",
    "kein",
    "keine",
    "keiner",
    "keinem",
    "keinen",
    "auch",
    "noch",
    "nur",
    "schon",
    "mehr",
    "sehr",
    "so",
    "wie",
    "was",
    "wer",
    "wo",
    "wann",
    "warum",
    "hier",
    "da",
    "dort",
    "nun",
    "dann",
    "denn",
    "also",
    "etwa",
}
