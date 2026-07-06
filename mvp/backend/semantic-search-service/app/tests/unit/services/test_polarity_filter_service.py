"""
Unit tests for the polarity filter service.
"""

from unittest.mock import Mock
import pytest
from dataclasses import dataclass

from services.polarity_filter_service import (
    PolarityFilterService,
    PolarityFilterResult,
    get_polarity_filter_service,
)


@dataclass
class MockSearchResult:
    """Mock search result for testing."""

    id: str
    text: str
    score: float


class TestPolarityFilterService:
    """Test suite for PolarityFilterService."""

    @pytest.fixture
    def service_enabled(self):
        """Create service instance with filtering enabled."""
        return PolarityFilterService(enable_filtering=True)

    @pytest.fixture
    def service_disabled(self):
        """Create service instance with filtering disabled."""
        return PolarityFilterService(enable_filtering=False)

    def test_initialization_enabled(self):
        """Test service initialization with filtering enabled."""
        service = PolarityFilterService(enable_filtering=True)
        assert service.enable_filtering is True

    def test_initialization_disabled(self):
        """Test service initialization with filtering disabled."""
        service = PolarityFilterService(enable_filtering=False)
        assert service.enable_filtering is False

    def test_filtering_disabled_returns_unmodified_results(self, service_disabled):
        """Test that disabled filtering returns results unmodified."""
        results = [
            MockSearchResult(id="1", text="Test", score=0.9),
            MockSearchResult(id="2", text="Test 2", score=0.8),
        ]

        filtered, metadata = service_disabled.analyze_and_filter_statement_results(
            query_text="Test query",
            statement_results=results,
            get_text_fn=lambda r: r.text,
        )

        assert len(filtered) == 2
        assert filtered[0].score == 0.9
        assert filtered[1].score == 0.8
        assert len(metadata) == 0

    def test_empty_results_returns_empty(self, service_enabled):
        """Test filtering empty results list."""
        filtered, metadata = service_enabled.analyze_and_filter_statement_results(
            query_text="Test query", statement_results=[], get_text_fn=lambda r: r.text
        )

        assert len(filtered) == 0
        assert len(metadata) == 0

    def test_matching_polarity_no_penalty(self, service_enabled):
        """Test that matching polarity applies no penalty."""
        results = [
            MockSearchResult(
                id="1", text="Klimaschutz ist wichtig", score=0.9
            ),  # Positive
        ]

        filtered, metadata = service_enabled.analyze_and_filter_statement_results(
            query_text="Klimaschutz ist notwendig",  # Also positive
            statement_results=results,
            get_text_fn=lambda r: r.text,
        )

        assert len(filtered) == 1
        assert filtered[0].score == 0.9  # No penalty applied
        assert metadata["1"].polarity_mismatch_detected is False
        assert metadata["1"].polarity_penalty_applied == 1.0

    def test_contradictory_polarity_applies_penalty(self, service_enabled):
        """Test that contradictory polarity applies penalty."""
        results = [
            MockSearchResult(
                id="1", text="Klimaschutz ist nicht wichtig", score=0.9
            ),  # Negative
        ]

        filtered, metadata = service_enabled.analyze_and_filter_statement_results(
            query_text="Klimaschutz ist wichtig",  # Positive
            statement_results=results,
            get_text_fn=lambda r: r.text,
        )

        assert len(filtered) == 1
        assert filtered[0].score < 0.9  # Penalty applied
        assert metadata["1"].polarity_mismatch_detected is True
        assert metadata["1"].polarity_penalty_applied < 1.0
        assert metadata["1"].original_score == 0.9

    def test_neutral_query_no_penalty(self, service_enabled):
        """Test that neutral query applies no penalty."""
        results = [
            MockSearchResult(id="1", text="Klimaschutz ist wichtig", score=0.9),
        ]

        filtered, metadata = service_enabled.analyze_and_filter_statement_results(
            query_text="Klimaschutz",  # Neutral - just the term
            statement_results=results,
            get_text_fn=lambda r: r.text,
        )

        assert len(filtered) == 1
        assert filtered[0].score == 0.9  # No penalty for neutral
        assert metadata["1"].polarity_mismatch_detected is False

    def test_neutral_result_no_penalty(self, service_enabled):
        """Test that neutral result gets no penalty."""
        results = [
            MockSearchResult(id="1", text="Klimaschutz diskutieren", score=0.9),
        ]

        filtered, metadata = service_enabled.analyze_and_filter_statement_results(
            query_text="Klimaschutz ist wichtig",  # Positive
            statement_results=results,
            get_text_fn=lambda r: r.text,
        )

        assert len(filtered) == 1
        assert filtered[0].score == 0.9  # No penalty for neutral result
        assert metadata["1"].polarity_mismatch_detected is False

    def test_multiple_results_sorted_by_adjusted_score(self, service_enabled):
        """Test that results are re-sorted by adjusted scores."""
        results = [
            MockSearchResult(
                id="1", text="Klimaschutz ist nicht wichtig", score=0.95
            ),  # High score, negative
            MockSearchResult(
                id="2", text="Klimaschutz ist sehr wichtig", score=0.85
            ),  # Lower score, positive
            MockSearchResult(
                id="3", text="Klimaschutz fördern", score=0.80
            ),  # Lowest score, positive
        ]

        filtered, metadata = service_enabled.analyze_and_filter_statement_results(
            query_text="Klimaschutz ist wichtig",  # Positive query
            statement_results=results,
            get_text_fn=lambda r: r.text,
        )

        # Result 1 should be penalized and move down
        # Results 2 and 3 should maintain their scores and move up
        assert len(filtered) == 3
        assert filtered[0].id == "2"  # Positive, should be first now
        assert filtered[1].id == "3"  # Positive, should be second
        assert filtered[2].id == "1"  # Negative (penalized), should be last

    def test_metadata_contains_all_info(self, service_enabled):
        """Test that metadata contains complete information."""
        results = [
            MockSearchResult(id="1", text="Klimaschutz ist nicht wichtig", score=0.9),
        ]

        filtered, metadata = service_enabled.analyze_and_filter_statement_results(
            query_text="Klimaschutz ist wichtig",
            statement_results=results,
            get_text_fn=lambda r: r.text,
        )

        assert "1" in metadata
        meta = metadata["1"]
        assert isinstance(meta, PolarityFilterResult)
        assert meta.original_score == 0.9
        assert meta.adjusted_score < 0.9
        assert meta.polarity_penalty_applied < 1.0
        assert meta.polarity_mismatch_detected is True
        assert meta.query_polarity == "positive"
        assert meta.result_polarity == "negative"
        assert len(meta.explanation) > 0

    def test_custom_text_extractor(self, service_enabled):
        """Test with custom text extraction function."""

        @dataclass
        class CustomResult:
            id: str
            content: str  # Different field name
            score: float

        results = [
            CustomResult(id="1", content="Klimaschutz ist wichtig", score=0.9),
        ]

        filtered, metadata = service_enabled.analyze_and_filter_statement_results(
            query_text="Klimaschutz ist wichtig",
            statement_results=results,
            get_text_fn=lambda r: r.content,  # Custom extractor
        )

        assert len(filtered) == 1
        assert "1" in metadata


class TestPolarityMismatchCheck:
    """Test the check_polarity_mismatch convenience method."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return PolarityFilterService(enable_filtering=True)

    def test_check_matching_texts(self, service):
        """Test checking two matching texts."""
        text1 = "Klimaschutz ist wichtig"
        text2 = "Klimaschutz fördern"

        has_mismatch, metadata = service.check_polarity_mismatch(text1, text2)

        assert has_mismatch is False
        assert metadata.polarity_mismatch_detected is False
        assert metadata.query_polarity == "positive"
        assert metadata.result_polarity == "positive"

    def test_check_contradictory_texts(self, service):
        """Test checking two contradictory texts."""
        text1 = "Klimaschutz ist wichtig"
        text2 = "Klimaschutz ist nicht wichtig"

        has_mismatch, metadata = service.check_polarity_mismatch(text1, text2)

        assert has_mismatch is True
        assert metadata.polarity_mismatch_detected is True
        assert metadata.query_polarity == "positive"
        assert metadata.result_polarity == "negative"
        assert metadata.polarity_penalty_applied < 1.0

    def test_check_neutral_text(self, service):
        """Test checking with neutral text."""
        text1 = "Klimaschutz ist wichtig"
        text2 = "Klimaschutz"

        has_mismatch, metadata = service.check_polarity_mismatch(text1, text2)

        assert has_mismatch is False  # Neutral is compatible


class TestSingletonPattern:
    """Test singleton pattern for service instance."""

    def test_get_service_returns_instance(self):
        """Test getting service instance."""
        service = get_polarity_filter_service(enable_filtering=True)
        assert isinstance(service, PolarityFilterService)

    def test_get_service_returns_same_instance(self):
        """Test singleton returns same instance on multiple calls."""
        service1 = get_polarity_filter_service(enable_filtering=True)
        service2 = get_polarity_filter_service(
            enable_filtering=False
        )  # Should be ignored
        assert service1 is service2


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return PolarityFilterService(enable_filtering=True)

    def test_climate_protection_query_filters_denial(self, service):
        """Test climate protection query filters out denial statements."""
        results = [
            MockSearchResult(id="1", text="Klimaschutz ist wichtig", score=0.95),
            MockSearchResult(id="2", text="Klimaschutz ist nicht wichtig", score=0.92),
            MockSearchResult(id="3", text="Klimaschutz ist überbewertet", score=0.90),
            MockSearchResult(id="4", text="Klimaschutz fördern", score=0.88),
        ]

        filtered, metadata = service.analyze_and_filter_statement_results(
            query_text="Klimaschutz ist wichtig",
            statement_results=results,
            get_text_fn=lambda r: r.text,
        )

        # Positive statements (1, 4) should rank higher than negative (2, 3)
        assert len(filtered) == 4
        positive_ids = {r.id for r in filtered[:2]}
        assert "1" in positive_ids
        assert "4" in positive_ids

        # Check penalties were applied to negative statements
        assert metadata["2"].polarity_mismatch_detected is True
        assert metadata["3"].polarity_mismatch_detected is True
        assert metadata["1"].polarity_mismatch_detected is False
        assert metadata["4"].polarity_mismatch_detected is False

    def test_renewable_energy_positive_vs_negative(self, service):
        """Test renewable energy query handling."""
        results = [
            MockSearchResult(
                id="1", text="Erneuerbare Energien sind wichtig", score=0.90
            ),
            MockSearchResult(
                id="2", text="Erneuerbare Energien sind nicht wichtig", score=0.89
            ),
        ]

        filtered, metadata = service.analyze_and_filter_statement_results(
            query_text="Erneuerbare Energien sind wichtig",
            statement_results=results,
            get_text_fn=lambda r: r.text,
        )

        assert filtered[0].id == "1"  # Positive should rank first
        assert filtered[1].id == "2"  # Negative should be penalized and rank lower

    def test_migration_positive_vs_negative_actions(self, service):
        """Test migration query with opposing action verbs."""
        results = [
            MockSearchResult(id="1", text="Migration fördern", score=0.85),
            MockSearchResult(id="2", text="Migration verhindern", score=0.87),
        ]

        filtered, metadata = service.analyze_and_filter_statement_results(
            query_text="Migration fördern",
            statement_results=results,
            get_text_fn=lambda r: r.text,
        )

        # Despite higher original score, "verhindern" should be penalized
        assert filtered[0].id == "1"  # "fördern" should rank first
        assert metadata["2"].polarity_mismatch_detected is True

    def test_neutral_query_no_filtering(self, service):
        """Test neutral query doesn't filter anything."""
        results = [
            MockSearchResult(id="1", text="Klimaschutz ist wichtig", score=0.90),
            MockSearchResult(id="2", text="Klimaschutz ist nicht wichtig", score=0.85),
            MockSearchResult(id="3", text="Klimaschutz diskutieren", score=0.80),
        ]

        filtered, metadata = service.analyze_and_filter_statement_results(
            query_text="Klimaschutz",  # Neutral query
            statement_results=results,
            get_text_fn=lambda r: r.text,
        )

        # Order should remain the same (by original scores)
        assert filtered[0].id == "1"
        assert filtered[1].id == "2"
        assert filtered[2].id == "3"

        # No penalties should be applied
        assert metadata["1"].polarity_mismatch_detected is False
        assert metadata["2"].polarity_mismatch_detected is False
        assert metadata["3"].polarity_mismatch_detected is False

    def test_mixed_results_comprehensive(self, service):
        """Test comprehensive scenario with mixed polarities."""
        results = [
            MockSearchResult(
                id="1", text="Digitalisierung ist sinnvoll", score=0.92
            ),  # Positive
            MockSearchResult(
                id="2", text="Digitalisierung ist unsinnig", score=0.90
            ),  # Negative
            MockSearchResult(
                id="3", text="Digitalisierung fördern", score=0.88
            ),  # Positive
            MockSearchResult(
                id="4", text="Digitalisierung ablehnen", score=0.86
            ),  # Negative
            MockSearchResult(
                id="5", text="Digitalisierung diskutieren", score=0.84
            ),  # Neutral
        ]

        filtered, metadata = service.analyze_and_filter_statement_results(
            query_text="Digitalisierung ist sinnvoll",  # Positive query
            statement_results=results,
            get_text_fn=lambda r: r.text,
        )

        assert len(filtered) == 5

        # Positive results should rank higher
        top_three_ids = {r.id for r in filtered[:3]}
        assert "1" in top_three_ids  # Positive
        assert "3" in top_three_ids  # Positive
        assert "5" in top_three_ids  # Neutral (compatible)

        # Negative results should be penalized
        assert metadata["2"].polarity_mismatch_detected is True
        assert metadata["4"].polarity_mismatch_detected is True
