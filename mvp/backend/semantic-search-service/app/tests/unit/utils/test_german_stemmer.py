"""
Unit tests for the German stemmer utility.
"""

import pytest

from utils.german_stemmer import (
    stem_german,
    extract_keywords,
    calculate_keyword_overlap,
    calculate_keyword_boost,
)


class TestGermanStemmer:
    """Test German word stemming."""

    def test_stem_basic_word(self):
        """Test stemming of basic word."""
        assert stem_german("laufen") == "lauf"

    def test_stem_removes_en_suffix(self):
        """Test removal of 'en' suffix."""
        assert stem_german("spielen") == "spiel"

    def test_stem_removes_er_suffix(self):
        """Test removal of 'er' suffix."""
        assert stem_german("spieler") == "spiel"

    def test_stem_umlaut_replacement(self):
        """Test umlaut replacement."""
        assert stem_german("über") == "uber"
        assert stem_german("schön") == "schon"
        assert stem_german("grün") == "grun"

    def test_stem_eszett_replacement(self):
        """Test eszett (ß) replacement."""
        assert stem_german("Straße") == "strass"

    def test_stem_preserves_short_words(self):
        """Test that short words are not over-stemmed."""
        assert stem_german("ab") == "ab"
        assert stem_german("am") == "am"

    def test_stem_auto_variations(self):
        """Test that Auto variations stem to same root."""
        assert stem_german("Auto") == stem_german("Autos")
        # Autoindustrie contains "auto" stem
        assert "aut" in stem_german("Autoindustrie")

    def test_stem_lowercase_conversion(self):
        """Test lowercase conversion."""
        assert stem_german("KLIMASCHUTZ") == stem_german("klimaschutz")

    def test_stem_whitespace_stripping(self):
        """Test whitespace is stripped."""
        assert stem_german("  wichtig  ") == stem_german("wichtig")


class TestKeywordExtraction:
    """Test keyword extraction from German text."""

    def test_extract_basic_keywords(self):
        """Test extraction of basic keywords."""
        keywords = extract_keywords("Klimaschutz ist wichtig")
        assert "klimaschutz" in keywords
        assert "wichtig" in keywords

    def test_extract_removes_stop_words(self):
        """Test that stop words are removed."""
        keywords = extract_keywords("Der Klimaschutz ist sehr wichtig")
        assert "klimaschutz" in keywords
        assert "wichtig" in keywords
        assert "der" not in keywords  # stop word
        assert "ist" not in keywords  # stop word
        assert "sehr" not in keywords  # stop word

    def test_extract_min_length(self):
        """Test minimum length filtering."""
        keywords = extract_keywords("Ich mag es", min_length=3)
        assert "mag" in keywords
        assert "ich" not in keywords  # too short
        assert "es" not in keywords  # too short

    def test_extract_with_hyphens(self):
        """Test extraction of hyphenated words."""
        keywords = extract_keywords("E-Autos sind umweltfreundlich")
        # E-Autos should be split and "auto" extracted
        assert any("aut" in kw for kw in keywords)
        # "e" should be skipped (too short)
        assert "e" not in keywords

    def test_extract_hyphenated_compounds(self):
        """Test extraction from hyphenated compounds like Vogel-Schredder."""
        keywords = extract_keywords("Vogel-Schredder sind gefährlich")
        # Both parts should be extracted
        assert any("vogel" in kw or "vog" in kw for kw in keywords)
        assert any("schredd" in kw for kw in keywords)

    def test_extract_handles_punctuation(self):
        """Test that punctuation is handled correctly."""
        keywords = extract_keywords("Windräder töten Vögel!")
        assert any("windr" in kw for kw in keywords)
        assert any("tot" in kw or "toten" in kw for kw in keywords)
        assert any("vog" in kw or "vogel" in kw for kw in keywords)

    def test_extract_empty_text(self):
        """Test extraction from empty text."""
        keywords = extract_keywords("")
        assert len(keywords) == 0

    def test_extract_only_stop_words(self):
        """Test extraction when only stop words present."""
        keywords = extract_keywords("der die das")
        assert len(keywords) == 0


class TestKeywordOverlap:
    """Test keyword overlap calculation."""

    def test_overlap_perfect_match(self):
        """Test 100% overlap."""
        query_kw = ["klimaschutz", "wichtig"]
        result_kw = ["klimaschutz", "wichtig", "zukunft"]
        overlap = calculate_keyword_overlap(query_kw, result_kw)
        assert overlap == 1.0

    def test_overlap_partial_match(self):
        """Test 50% overlap."""
        query_kw = ["klimaschutz", "wichtig"]
        result_kw = ["klimaschutz", "unwichtig"]
        overlap = calculate_keyword_overlap(query_kw, result_kw)
        assert overlap == 0.5

    def test_overlap_no_match(self):
        """Test 0% overlap."""
        query_kw = ["klimaschutz", "wichtig"]
        result_kw = ["digitalisierung", "schulen"]
        overlap = calculate_keyword_overlap(query_kw, result_kw)
        assert overlap == 0.0

    def test_overlap_empty_query(self):
        """Test overlap with empty query keywords."""
        query_kw = []
        result_kw = ["klimaschutz", "wichtig"]
        overlap = calculate_keyword_overlap(query_kw, result_kw)
        assert overlap == 1.0  # Neutral for empty query

    def test_overlap_empty_result(self):
        """Test overlap with empty result keywords."""
        query_kw = ["klimaschutz", "wichtig"]
        result_kw = []
        overlap = calculate_keyword_overlap(query_kw, result_kw)
        assert overlap == 0.0


class TestKeywordBoost:
    """Test keyword boost calculation."""

    def test_boost_high_overlap(self):
        """Test boost for high keyword overlap."""
        boost = calculate_keyword_boost(
            "Klimaschutz ist wichtig", "Klimaschutz fördern ist wichtig"
        )
        assert boost > 1.0  # Should boost

    def test_boost_low_overlap(self):
        """Test penalty for low keyword overlap."""
        boost = calculate_keyword_boost(
            "Klimaschutz ist wichtig", "Digitalisierung in Schulen"
        )
        assert boost < 1.0  # Should penalize

    def test_boost_medium_overlap(self):
        """Test neutral boost for medium overlap."""
        boost = calculate_keyword_boost("Klimaschutz fördern", "Klimaschutz stoppen")
        assert 0.9 <= boost <= 1.1  # Should be near neutral (50% overlap)

    def test_boost_strength_parameter(self):
        """Test that boost strength parameter affects result."""
        text1 = "Klimaschutz wichtig"
        text2 = "Digitalisierung Schulen"

        weak_boost = calculate_keyword_boost(text1, text2, boost_strength=0.1)
        strong_boost = calculate_keyword_boost(text1, text2, boost_strength=0.5)

        # Both should penalize (no overlap)
        assert weak_boost < 1.0
        assert strong_boost < 1.0
        # Strong boost should have stronger effect
        assert strong_boost < weak_boost

    def test_boost_clamping(self):
        """Test that boost is clamped to reasonable range."""
        # Perfect overlap with high boost strength
        boost = calculate_keyword_boost(
            "Klimaschutz", "Klimaschutz", boost_strength=0.3
        )
        assert boost <= 1.3  # Should not exceed max

        # No overlap with high boost strength
        boost = calculate_keyword_boost(
            "Klimaschutz", "Digitalisierung", boost_strength=0.3
        )
        assert boost >= 0.7  # Should not go below min


class TestRealWorldExamples:
    """Test with real-world examples."""

    def test_birds_vs_reliability(self):
        """Test the problematic case: birds vs reliability."""
        query = "Windräder töten die Vögel!"
        result = "Erneuerbare Energien sind total unzuverlässig!"

        boost = calculate_keyword_boost(query, result)
        # Should penalize - different topics
        assert boost < 1.0

    def test_e_autos_perfect_match(self):
        """Test E-Autos perfect match."""
        query = "E-Autos"
        result = "E-Autos sind auch nicht besser für die Umwelt"

        boost = calculate_keyword_boost(query, result)
        # Should boost - high overlap
        assert boost > 1.0

    def test_verbrenner_partial_match(self):
        """Test Verbrenner-Aus partial match."""
        query = "E-Autos"
        result = "Das Verbrenner-Aus killt unsere Autoindustrie!"

        boost = calculate_keyword_boost(query, result)
        # Should penalize slightly - low direct keyword overlap
        # (even though "Auto" stem appears in "Autoindustrie")
        assert boost < 1.0

    def test_klimaschutz_variations(self):
        """Test Klimaschutz variations."""
        query = "Klimaschutz ist wichtig"
        result = "Der Klimaschutz ist sehr wichtig für unsere Zukunft"

        boost = calculate_keyword_boost(query, result)
        # Should boost - high overlap
        assert boost > 1.0

    def test_different_topics(self):
        """Test completely different topics."""
        query = "Klimaschutz fördern"
        result = "Digitalisierung in Schulen ist wichtig"

        boost = calculate_keyword_boost(query, result)
        # Should penalize - no overlap
        assert boost < 1.0

    def test_auto_stemming(self):
        """Test that Auto variations are recognized as similar."""
        query = "Auto kaufen"
        result = "Die Autoindustrie produziert viele Autos"

        query_kw = extract_keywords(query)
        result_kw = extract_keywords(result)

        # Check that stemmed versions match
        query_stems = set(query_kw)
        result_stems = set(result_kw)
        assert len(query_stems.intersection(result_stems)) > 0

    def test_renewable_energy_variations(self):
        """Test renewable energy variations."""
        query = "Erneuerbare Energien ausbauen"
        result = "Erneuerbare Energien sind unzuverlässig"

        boost = calculate_keyword_boost(query, result)
        # Should boost - high overlap on key terms
        assert boost > 1.0

    def test_wind_power_variations(self):
        """Test wind power variations."""
        query = "Windräder sind laut"
        result = "Windkraft ist eine gute Energiequelle"

        query_kw = extract_keywords(query)
        result_kw = extract_keywords(result)

        # Both should contain wind-related stems
        # "Windräder" → "windr..." and "Windkraft" → "windkraft"
        assert any("wind" in kw for kw in query_kw)
        assert any("wind" in kw for kw in result_kw)
