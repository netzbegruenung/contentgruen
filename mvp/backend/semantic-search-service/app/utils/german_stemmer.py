"""
Schlagwoerter fuer die Schlagwort-Ueberlappung der Suche (keyword_overlap_service).

Der Stemmer ist CISTEM (Weissweiler & Fraser 2017, "Developing a Stemmer for German
Based on a Comparative Analysis of Publicly Available Stemmers"), umgesetzt nach der
Referenzimplementierung (https://github.com/LeonieWeissweiler/CISTEM, MIT-Lizenz,
Text in CISTEM-LIZENZ.txt), ohne Abhaengigkeit. Gewaehlt am Suchtestset (#392,
tests/regression/SUCHTESTSET.md): CISTEM, Snowball German und die spaCy-Lemmata aus
dem Gegenlesen messen gleich; nur Kleinschreibung und Umlaute (ohne Stemmer) verliert
einen Fall. CISTEM ist der kleinste der drei und kostet keine Rechenzeit fuer ein
Sprachmodell.

Staemme werden nirgends gespeichert; eine Aenderung wirkt ab dem naechsten Start.
"""

import re
from typing import List, Set

_GE_PRAEFIX = re.compile(r"^ge(.{4,})")
_DOPPELT = re.compile(r"(.)\1")
_DOPPELT_ZURUECK = re.compile(r"(.)\*")
_EM_ER = re.compile(r"e[mr]$")
_ND = re.compile(r"nd$")
_T = re.compile(r"t$")
_E_S_N = re.compile(r"[esn]$")
_PLATZHALTER_RAUS = re.compile(r"[$%&*]")


def stem_german(word: str) -> str:
    """
    Stamm eines deutschen Worts nach CISTEM.

    Kleinschreibung, Umlaute werden zu a/o/u, ss statt ß, ein ge- am Anfang faellt weg
    (wenn mindestens vier Zeichen bleiben). Dann werden vom Ende -em/-er/-nd (bei mehr
    als fuenf Zeichen), -t und -e/-s/-n abgeschnitten, solange das Wort laenger als
    drei Zeichen ist (ein Stamm kann also drei Zeichen haben: gruen -> gru). sch, ei,
    ie und Doppelbuchstaben bleiben dabei ganz.

    Variante ohne Gross-/Kleinschreibung (case_insensitive der Referenz): Die
    Grundvariante schneidet -t nur bei kleingeschriebenen Woertern ab. Suchanfragen
    sind aber oft kleingeschrieben ("grüne nur großstadt"), und dann faenden
    "großstadt" und "Großstädte" nicht zusammen.

    Beispiele: Windraeder und Windrad -> windrad, toetet und toeten -> tot.
    """
    word = word.strip().lower()
    if not word:
        return word
    word = word.replace("ä", "a").replace("ö", "o").replace("ü", "u")
    word = word.replace("ß", "ss")

    # Zeichen, die als Platzhalter dienen, kommen in Woertern nicht vor.
    word = _PLATZHALTER_RAUS.sub("", word)
    word = _GE_PRAEFIX.sub(r"\1", word)
    # Platzhalter, damit die Regeln unten diese Buchstabenfolgen nicht zerlegen.
    word = word.replace("sch", "$").replace("ei", "%").replace("ie", "&")
    word = _DOPPELT.sub(r"\1*", word)

    while len(word) > 3:
        if len(word) > 5:
            word, n = _EM_ER.subn("", word)
            if n:
                continue
            word, n = _ND.subn("", word)
            if n:
                continue
        word, n = _T.subn("", word)
        if n:
            continue
        word, n = _E_S_N.subn("", word)
        if not n:
            break

    word = _DOPPELT_ZURUECK.sub(r"\1\1", word)
    return word.replace("%", "ei").replace("&", "ie").replace("$", "sch")


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
                        if len(stemmed) >= min_length:
                            keywords.append(stemmed)
        else:
            # Stem the word normally
            stemmed = stem_german(word)
            if len(stemmed) >= min_length:
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


# Common German stop words (function words with little semantic meaning).
# "nicht", "kein", "keine" und "ohne" bleiben drin: Die Verneinung prueft der
# Polaritaetsfilter (negation_detector), spaeter die NLI-Stufe (#387). Am Suchtestset
# aendert ihr Wegfall nichts (#392). Pronomen wie "uns" und "mir" verbinden sonst
# Aussagen ueber verschiedene Themen ("Die Gruenen wollen uns ... verbieten").
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
    "uns",
    "unser",
    "unsere",
    "unserer",
    "unserem",
    "unseren",
    "mir",
    "mich",
    "dir",
    "dich",
    "euch",
    "euer",
    "eure",
    "ihm",
    "ihn",
    "ihnen",
    "alle",
    "alles",
    "allen",
    "aller",
    "allem",
    "unsrer",
    "unsren",
    "unsrem",
    "euren",
    "eurem",
    "eurer",
    "nichts",
}
