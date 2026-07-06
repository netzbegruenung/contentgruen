"""
Unit tests for the negation detection utility.
"""

import pytest

from utils.negation_detector import (
    normalize_text,
    has_negation_cancelation,
    detect_negation_markers,
    detect_stance_words,
    analyze_polarity,
    polarities_match,
    calculate_polarity_penalty,
    PolarityAnalysis,
)


class TestNormalization:
    """Test text normalization."""

    def test_normalize_text_lowercase(self):
        """Test text is converted to lowercase."""
        assert normalize_text("KLIMASCHUTZ") == "klimaschutz"

    def test_normalize_text_strips_whitespace(self):
        """Test leading/trailing whitespace is removed."""
        assert normalize_text("  Klimaschutz  ") == "klimaschutz"

    def test_normalize_text_preserves_umlauts(self):
        """Test German umlauts are preserved."""
        assert normalize_text("Grüne Überzeugung") == "grüne überzeugung"


class TestNegationCancelation:
    """Test negation cancelation detection."""

    def test_nicht_nur_pattern(self):
        """Test 'nicht nur' (not only) is detected as cancelation."""
        assert has_negation_cancelation("Nicht nur Klimaschutz ist wichtig")
        assert has_negation_cancelation("nicht nur wichtig")

    def test_ohne_zweifel_pattern(self):
        """Test 'ohne Zweifel' (without doubt) is detected as cancelation."""
        assert has_negation_cancelation("Ohne Zweifel ist das richtig")
        assert has_negation_cancelation("ohne zweifel wichtig")

    def test_no_cancelation(self):
        """Test normal negations are not detected as cancelation."""
        assert not has_negation_cancelation("nicht wichtig")
        assert not has_negation_cancelation("ohne Klimaschutz")


class TestNegationMarkerDetection:
    """Test detection of negation marker words."""

    def test_detect_nicht(self):
        """Test detection of 'nicht' (not)."""
        negations = detect_negation_markers("Das ist nicht wichtig")
        assert "nicht" in negations

    def test_detect_kein_forms(self):
        """Test detection of various forms of 'kein' (no/none)."""
        assert "kein" in detect_negation_markers("Kein Klimaschutz")
        assert "keine" in detect_negation_markers("Keine Unterstützung")
        assert "keinen" in detect_negation_markers("Keinen Grund")

    def test_detect_nie_niemals(self):
        """Test detection of 'nie' and 'niemals' (never)."""
        assert "nie" in detect_negation_markers("Das kommt nie vor")
        assert "niemals" in detect_negation_markers("Niemals aufgeben")

    def test_detect_ohne(self):
        """Test detection of 'ohne' (without)."""
        negations = detect_negation_markers("Ohne Klimaschutz geht es nicht")
        assert "ohne" in negations

    def test_detect_multiple_negations(self):
        """Test detection of multiple negation markers in one text."""
        negations = detect_negation_markers("Nicht ohne Grund nie wieder")
        assert len(negations) == 3
        assert "nicht" in negations
        assert "ohne" in negations
        assert "nie" in negations

    def test_no_negations(self):
        """Test text without negation markers."""
        negations = detect_negation_markers("Klimaschutz ist wichtig")
        assert len(negations) == 0

    def test_punctuation_handling(self):
        """Test negation detection with punctuation."""
        negations = detect_negation_markers("Das ist nicht!")
        assert "nicht" in negations


class TestStanceWordDetection:
    """Test detection of positive and negative stance words."""

    def test_detect_positive_wichtig(self):
        """Test detection of 'wichtig' (important)."""
        positive, negative = detect_stance_words("Das ist wichtig")
        assert "wichtig" in positive
        assert len(negative) == 0

    def test_detect_positive_multiple(self):
        """Test detection of multiple positive words."""
        positive, negative = detect_stance_words("Das ist wichtig und notwendig")
        assert "wichtig" in positive
        assert "notwendig" in positive
        assert len(negative) == 0

    def test_detect_negative_unwichtig(self):
        """Test detection of 'unwichtig' (unimportant)."""
        positive, negative = detect_stance_words("Das ist unwichtig")
        assert len(positive) == 0
        assert "unwichtig" in negative

    def test_detect_negative_überbewertet(self):
        """Test detection of 'überbewertet' (overrated)."""
        positive, negative = detect_stance_words("Das ist überbewertet")
        assert "überbewertet" in negative

    def test_detect_action_verbs_positive(self):
        """Test detection of positive action verbs."""
        positive, negative = detect_stance_words("Klimaschutz fördern und stärken")
        assert "fördern" in positive
        assert "stärken" in positive

    def test_detect_action_verbs_negative(self):
        """Test detection of negative action verbs."""
        positive, negative = detect_stance_words("Migration verhindern und ablehnen")
        assert "verhindern" in negative
        assert "ablehnen" in negative

    def test_no_stance_words(self):
        """Test text without stance words."""
        positive, negative = detect_stance_words("Klimaschutz diskutieren")
        assert len(positive) == 0
        assert len(negative) == 0


class TestPolarityAnalysis:
    """Test comprehensive polarity analysis."""

    def test_positive_statement_simple(self):
        """Test simple positive statement."""
        result = analyze_polarity("Klimaschutz ist wichtig")
        assert result.polarity == "positive"
        assert result.confidence >= 0.7
        assert not result.negation_detected

    def test_negative_statement_with_negation(self):
        """Test negative statement with negation + positive word."""
        result = analyze_polarity("Klimaschutz ist nicht wichtig")
        assert result.polarity == "negative"
        assert result.confidence >= 0.8
        assert result.negation_detected
        assert "nicht" in result.explanation.lower()

    def test_negative_statement_with_negative_word(self):
        """Test negative statement with explicit negative word."""
        result = analyze_polarity("Klimaschutz ist überbewertet")
        assert result.polarity == "negative"
        assert result.confidence >= 0.8
        assert "überbewertet" in result.negative_stance_words

    def test_neutral_statement(self):
        """Test neutral statement without clear polarity."""
        result = analyze_polarity("Klimaschutz diskutieren")
        assert result.polarity == "neutral"

    def test_empty_text(self):
        """Test analysis of empty text."""
        result = analyze_polarity("")
        assert result.polarity == "neutral"
        assert result.confidence == 1.0

    def test_negation_cancelation_nicht_nur(self):
        """Test negation cancelation with 'nicht nur'."""
        result = analyze_polarity("Nicht nur Klimaschutz ist wichtig")
        assert result.polarity == "neutral"
        assert "canceled" in result.explanation.lower()

    def test_complex_negative_kein_with_noun(self):
        """Test 'kein' + noun construction."""
        result = analyze_polarity("Kein Klimaschutz notwendig")
        assert result.polarity == "negative"
        assert result.negation_detected

    def test_action_verb_positive(self):
        """Test positive action verb."""
        result = analyze_polarity("Klimaschutz fördern")
        assert result.polarity == "positive"

    def test_action_verb_negative(self):
        """Test negative action verb."""
        result = analyze_polarity("Klimaschutz verhindern")
        assert result.polarity == "negative"

    def test_multiple_positive_words(self):
        """Test statement with multiple positive indicators."""
        result = analyze_polarity("Klimaschutz ist wichtig und notwendig")
        assert result.polarity == "positive"
        assert result.confidence >= 0.7

    def test_contradictory_statement(self):
        """Test statement with both positive and negative words (negative wins)."""
        result = analyze_polarity("Klimaschutz ist wichtig aber überbewertet")
        assert result.polarity == "negative"
        # Negative stance words trump positive ones


class TestPolarityMatching:
    """Test polarity matching logic."""

    def test_same_polarity_positive(self):
        """Test matching of two positive polarities."""
        assert polarities_match("positive", "positive")

    def test_same_polarity_negative(self):
        """Test matching of two negative polarities."""
        assert polarities_match("negative", "negative")

    def test_same_polarity_neutral(self):
        """Test matching of two neutral polarities."""
        assert polarities_match("neutral", "neutral")

    def test_mismatch_positive_negative(self):
        """Test mismatch between positive and negative."""
        assert not polarities_match("positive", "negative")
        assert not polarities_match("negative", "positive")

    def test_neutral_matches_anything(self):
        """Test neutral is compatible with any polarity."""
        assert polarities_match("neutral", "positive")
        assert polarities_match("neutral", "negative")
        assert polarities_match("positive", "neutral")
        assert polarities_match("negative", "neutral")


class TestPolarityPenalty:
    """Test polarity penalty calculation."""

    def test_no_penalty_for_matching_polarities(self):
        """Test no penalty when polarities match."""
        penalty = calculate_polarity_penalty("positive", "positive", 0.9, 0.9)
        assert penalty == 1.0

    def test_no_penalty_for_neutral(self):
        """Test no penalty when one polarity is neutral."""
        penalty = calculate_polarity_penalty("positive", "neutral", 0.9, 0.9)
        assert penalty == 1.0

    def test_penalty_for_contradictory_polarities(self):
        """Test penalty applied for contradictory polarities."""
        penalty = calculate_polarity_penalty("positive", "negative", 0.9, 0.9)
        assert penalty < 1.0
        assert penalty >= 0.2  # Penalty is at least 80% reduction max

    def test_higher_confidence_means_higher_penalty(self):
        """Test penalty increases with confidence."""
        low_conf_penalty = calculate_polarity_penalty("positive", "negative", 0.5, 0.5)
        high_conf_penalty = calculate_polarity_penalty("positive", "negative", 0.9, 0.9)
        assert high_conf_penalty < low_conf_penalty

    def test_penalty_clamped_to_minimum(self):
        """Test penalty is clamped to minimum value."""
        penalty = calculate_polarity_penalty("positive", "negative", 1.0, 1.0)
        assert penalty >= 0.2  # Minimum penalty

    def test_penalty_clamped_to_maximum(self):
        """Test penalty is clamped to maximum value."""
        penalty = calculate_polarity_penalty("positive", "positive", 0.0, 0.0)
        assert penalty <= 1.0  # Maximum penalty (no penalty)


class TestRealWorldExamples:
    """Test with real-world political statement examples."""

    def test_climate_protection_positive(self):
        """Test positive climate protection statement."""
        result = analyze_polarity("Klimaschutz ist sehr wichtig für unsere Zukunft")
        assert result.polarity == "positive"

    def test_climate_protection_negative(self):
        """Test negative climate protection statement."""
        result = analyze_polarity("Klimaschutz ist nicht wichtig")
        assert result.polarity == "negative"

    def test_climate_protection_denial(self):
        """Test climate protection denial."""
        result = analyze_polarity("Klimaschutz ist überbewertet")
        assert result.polarity == "negative"

    def test_renewable_energy_positive(self):
        """Test positive renewable energy statement."""
        result = analyze_polarity("Erneuerbare Energien sind wichtig")
        assert result.polarity == "positive"

    def test_renewable_energy_negative(self):
        """Test negative renewable energy statement."""
        result = analyze_polarity("Erneuerbare Energien sind nicht wichtig")
        assert result.polarity == "negative"

    def test_migration_positive(self):
        """Test positive migration statement."""
        result = analyze_polarity("Migration fördern")
        assert result.polarity == "positive"

    def test_migration_negative(self):
        """Test negative migration statement."""
        result = analyze_polarity("Migration verhindern")
        assert result.polarity == "negative"

    def test_digitalization_positive(self):
        """Test positive digitalization statement."""
        result = analyze_polarity("Digitalisierung in Schulen ist sinnvoll")
        assert result.polarity == "positive"

    def test_digitalization_negative(self):
        """Test negative digitalization statement."""
        result = analyze_polarity("Digitalisierung in Schulen ist unsinnig")
        assert result.polarity == "negative"

    def test_comparison_matching_pair(self):
        """Test analysis of a matching query-result pair."""
        query_result = analyze_polarity("Klimaschutz ist wichtig")
        result_result = analyze_polarity("Klimaschutz fördern ist notwendig")

        assert query_result.polarity == "positive"
        assert result_result.polarity == "positive"
        assert polarities_match(query_result.polarity, result_result.polarity)

    def test_comparison_contradictory_pair(self):
        """Test analysis of contradictory query-result pair."""
        query_result = analyze_polarity("Klimaschutz ist wichtig")
        result_result = analyze_polarity("Klimaschutz ist nicht wichtig")

        assert query_result.polarity == "positive"
        assert result_result.polarity == "negative"
        assert not polarities_match(query_result.polarity, result_result.polarity)

        penalty = calculate_polarity_penalty(
            query_result.polarity,
            result_result.polarity,
            query_result.confidence,
            result_result.confidence,
        )
        assert penalty < 1.0  # Penalty should be applied
