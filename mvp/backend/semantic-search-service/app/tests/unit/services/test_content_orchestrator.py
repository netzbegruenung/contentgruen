"""
Test module for ContentOrchestrator using the new dependency injection architecture.

This module demonstrates clean testing patterns without complex mocking.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, call, patch
from typing import Dict, Any

from services.orchestration.content_orchestrator import (
    ContentOrchestrator,
    ProgressTracker,
    DataProcessor,
    get_content_fingerprint,
)
from domain.models.content_type import ContentType
from domain.models.statement import Statement, StatementReplysuggestion
from domain.models.commentary import Commentary, CommentaryReference
from domain.models.reference import Reference
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin
from utils.data_utils import DataSource
from tests.conftest import (
    create_base_content_fields,
    create_statement_data,
    create_commentary_data,
    create_reference_data,
)


@pytest.mark.unit
class TestFingerprintGeneration:
    """Test content fingerprint generation."""

    def test_fingerprint_length(self):
        """Test that fingerprint is exactly 32 characters."""
        fingerprint = get_content_fingerprint(
            "Test Title", "Test Content", "commentary"
        )
        assert len(fingerprint) == 32
        assert all(c in "0123456789abcdef" for c in fingerprint)

    def test_fingerprint_consistency(self):
        """Test that same input produces same fingerprint."""
        fp1 = get_content_fingerprint("Title", "Content", "type")
        fp2 = get_content_fingerprint("Title", "Content", "type")
        assert fp1 == fp2

    def test_fingerprint_uniqueness(self):
        """Test that different inputs produce different fingerprints."""
        fp1 = get_content_fingerprint("Title1", "Content", "type")
        fp2 = get_content_fingerprint("Title2", "Content", "type")
        fp3 = get_content_fingerprint("Title1", "Different", "type")
        fp4 = get_content_fingerprint("Title1", "Content", "other")

        # All should be different
        fingerprints = [fp1, fp2, fp3, fp4]
        assert len(set(fingerprints)) == 4


@pytest.mark.unit
class TestProgressTracker:
    """Test ProgressTracker helper class."""

    def test_progress_tracker_initialization(self):
        """Test progress tracker initialization."""
        callback = MagicMock()
        tracker = ProgressTracker(100, callback)

        assert tracker.total_items == 100
        assert tracker.current_progress == 0
        assert tracker.callback == callback

    def test_progress_tracker_without_callback(self):
        """Test progress tracker without callback."""
        tracker = ProgressTracker(50)

        assert tracker.total_items == 50
        assert tracker.callback is None

    def test_report_progress_with_callback(self):
        """Test reporting progress with callback."""
        callback = MagicMock()
        tracker = ProgressTracker(10, callback)

        tracker.report_progress("item1")
        tracker.report_progress("item2")

        assert tracker.current_progress == 2
        assert callback.call_count == 2
        # Extract just the relevant calls (excluding __bool__ checks)
        relevant_calls = [c for c in callback.call_args_list if c[0] and len(c[0]) == 3]
        assert len(relevant_calls) == 2
        assert relevant_calls[0] == call("item1", 1, 10)
        assert relevant_calls[1] == call("item2", 2, 10)

    def test_report_progress_without_callback(self):
        """Test reporting progress without callback."""
        tracker = ProgressTracker(10)

        tracker.report_progress("item1")

        assert tracker.current_progress == 1
        # Should not raise any errors


@pytest.mark.unit
class TestDataProcessor:
    """Test DataProcessor helper class."""

    @pytest.fixture
    def mock_orchestrator(self, test_settings):
        """Mock content orchestrator."""
        orchestrator = MagicMock()
        orchestrator.commentary_service = MagicMock()
        orchestrator.statement_service = MagicMock()
        orchestrator.reference_service = MagicMock()
        orchestrator.initial_data_author = test_settings.initial_data_author
        return orchestrator

    @pytest.fixture
    def data_processor(self, mock_orchestrator):
        """Create data processor instance."""
        return DataProcessor(mock_orchestrator)

    @pytest.mark.skip(reason="commentsuggestion functionality has been removed")
    def test_process_commentsuggestion(self, data_processor, mock_orchestrator):
        """Test processing comment suggestion."""
        comment_text = "This is a test comment suggestion that needs processing"
        expected_id = uuid.uuid4()
        mock_orchestrator.commentary_service.add_commentary.return_value = (
            True,
            expected_id,
            "Success",
        )

        result_id = data_processor.process_commentsuggestion(comment_text)

        assert result_id == expected_id
        mock_orchestrator.commentary_service.add_commentary.assert_called_once()

        # Check the commentary object passed to add_commentary
        call_args = mock_orchestrator.commentary_service.add_commentary.call_args[0]
        commentary = call_args[0]
        assert isinstance(commentary, Commentary)
        assert commentary.text == comment_text
        assert (
            commentary.title == "This is a test comment suggest..."
        )  # Truncated title
        assert commentary.references == []

    @pytest.mark.skip(reason="commentsuggestion functionality has been removed")
    def test_process_commentsuggestion_short_text(
        self, data_processor, mock_orchestrator
    ):
        """Test processing short comment suggestion."""
        comment_text = "Short comment"
        expected_id = uuid.uuid4()
        mock_orchestrator.commentary_service.add_commentary.return_value = (
            True,
            expected_id,
            "Success",
        )

        result_id = data_processor.process_commentsuggestion(comment_text)

        assert result_id == expected_id

        call_args = mock_orchestrator.commentary_service.add_commentary.call_args[0]
        commentary = call_args[0]
        assert commentary.title == "Short comment..."  # With ellipsis

    @pytest.mark.asyncio
    async def test_process_reference(self, data_processor, mock_orchestrator):
        """Test processing reference data."""
        reference_data = {
            "text": "Climate research findings",
            "reference_string": "Smith et al. (2024). Climate Study.",
        }
        expected_id = uuid.uuid4()
        # add_reference now returns a tuple (reference_id, is_new, description)
        mock_orchestrator.reference_service.add_reference = AsyncMock(
            return_value=(
                expected_id,
                True,
                "Reference added",
            )
        )

        result_id = await data_processor.process_reference(reference_data)

        assert result_id == expected_id
        mock_orchestrator.reference_service.add_reference.assert_called_once()

        # Check the reference object
        call_args = mock_orchestrator.reference_service.add_reference.call_args[0]
        reference = call_args[0]
        assert isinstance(reference, Reference)
        assert reference.text == "Climate research findings"
        assert reference.reference_string == "Smith et al. (2024). Climate Study."

    @pytest.mark.asyncio
    async def test_create_commentary_with_references(
        self, data_processor, mock_orchestrator
    ):
        """Test creating commentary with references."""
        commentary_data = {
            "text": "Analysis of climate data",
            "title": "Climate Analysis",
            "long_text": "Detailed analysis of climate data...",
            "short_text": "Climate analysis",
            "references": [
                {"text": "Reference 1", "reference_string": "Author1 (2024). Study 1."},
                {"text": "Reference 2", "reference_string": "Author2 (2024). Study 2."},
            ],
        }

        ref_ids = [uuid.uuid4(), uuid.uuid4()]
        # add_reference returns tuples (reference_id, is_new, description)
        mock_orchestrator.reference_service.add_reference = AsyncMock(
            side_effect=[
                (ref_ids[0], True, "Reference added"),
                (ref_ids[1], True, "Reference added"),
            ]
        )
        commentary_id = uuid.uuid4()
        mock_orchestrator.commentary_service.add_commentary = AsyncMock(
            return_value=(
                True,
                commentary_id,
                "Success",
            )
        )

        # Mock the idempotent seeding methods to simulate new content (not skipped)
        mock_orchestrator.is_content_processed.return_value = False
        mock_orchestrator.mark_content_processed.return_value = (
            "test_fingerprint_32_chars_hash_val"
        )

        result_id = await data_processor.create_commentary_with_references(
            commentary_data
        )

        assert result_id == commentary_id
        assert mock_orchestrator.reference_service.add_reference.call_count == 2
        mock_orchestrator.commentary_service.add_commentary.assert_called_once()

        # Check the commentary object
        call_args = mock_orchestrator.commentary_service.add_commentary.call_args[0]
        commentary = call_args[0]
        assert isinstance(commentary, Commentary)
        assert commentary.text == "Analysis of climate data"
        assert commentary.title == "Climate Analysis"
        assert len(commentary.references) == 2
        assert all(
            isinstance(ref, CommentaryReference) for ref in commentary.references
        )

        # Verify idempotent seeding methods were called
        mock_orchestrator.is_content_processed.assert_called_once_with(
            "Climate Analysis", "Analysis of climate data", "commentary"
        )
        mock_orchestrator.mark_content_processed.assert_called_once_with(
            "Climate Analysis", "Analysis of climate data", "commentary", "added"
        )

    @pytest.mark.asyncio
    async def test_create_commentary_with_references_skipped(
        self, data_processor, mock_orchestrator
    ):
        """Test creating commentary that gets skipped due to idempotent seeding."""
        commentary_data = {
            "text": "Analysis of climate data",
            "title": "Climate Analysis",
            "references": [],
        }

        # Mock the idempotent seeding methods to simulate already processed content
        mock_orchestrator.is_content_processed.return_value = True
        mock_orchestrator.mark_content_processed.return_value = (
            "existing_fingerprint_32_chars_hash"
        )

        result_id = await data_processor.create_commentary_with_references(
            commentary_data
        )

        # Should return None when skipped
        assert result_id is None

        # Commentary service should not be called when skipped
        mock_orchestrator.commentary_service.add_commentary.assert_not_called()

        # But the processed tracking methods should be called
        mock_orchestrator.is_content_processed.assert_called_once_with(
            "Climate Analysis", "Analysis of climate data", "commentary"
        )
        mock_orchestrator.mark_content_processed.assert_called_once_with(
            "Climate Analysis", "Analysis of climate data", "commentary", "skipped"
        )

    @pytest.mark.skip(reason="commentsuggestion functionality has been removed")
    def test_create_statement_with_replies(self, data_processor, mock_orchestrator):
        """Test creating statement with reply suggestions."""
        statement_text = "Climate change requires immediate action"
        reply_ids = [uuid.uuid4(), uuid.uuid4()]

        data_processor.create_statement_with_replies(statement_text, reply_ids)

        mock_orchestrator.statement_service.add_statement.assert_called_once()

        # Check the statement object
        call_args = mock_orchestrator.statement_service.add_statement.call_args[0]
        statement = call_args[0]
        assert isinstance(statement, Statement)
        assert statement.text == statement_text
        assert len(statement.replysuggestions) == 2
        assert all(
            isinstance(reply, StatementReplysuggestion)
            for reply in statement.replysuggestions
        )
        assert all(
            reply.content_type == ContentType.COMMENTARY
            for reply in statement.replysuggestions
        )


@pytest.mark.unit
class TestContentOrchestrator:
    """Test ContentOrchestrator main class."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for orchestrator."""
        return {
            "statement": MagicMock(),
            "commentary": MagicMock(),
            "reference": MagicMock(),
            "generic_text": MagicMock(),
        }

    @pytest.fixture
    def orchestrator(self, test_settings, mock_services):
        """Create content orchestrator instance with mock services."""
        return ContentOrchestrator(
            test_settings,
            commentary_service=mock_services["commentary"],
            reference_service=mock_services["reference"],
            statement_service=mock_services["statement"],
            generic_text_service=mock_services["generic_text"],
        )

    def test_orchestrator_initialization(
        self, orchestrator, test_settings, mock_services
    ):
        """Test orchestrator initialization."""
        assert orchestrator.settings == test_settings
        assert orchestrator.statement_service == mock_services["statement"]
        assert orchestrator.commentary_service == mock_services["commentary"]
        assert orchestrator.reference_service == mock_services["reference"]
        assert orchestrator.generic_text_service == mock_services["generic_text"]
        assert orchestrator.data_processor is not None
        assert len(orchestrator.services) == 4

    @pytest.mark.skip(reason="commentsuggestion functionality has been removed")
    def test_save_commentsuggestion_services(self, orchestrator):
        """Test saving services after commentsuggestions processing."""
        orchestrator._save_commentsuggestion_services()

        orchestrator.commentary_service.save.assert_called_once()
        orchestrator.statement_service.save.assert_called_once()
        # Reference and generic_text should not be saved
        orchestrator.reference_service.save.assert_not_called()
        orchestrator.generic_text_service.save.assert_not_called()

    def test_save_commentary_services(self, orchestrator):
        """Test saving services after commentaries processing."""
        orchestrator._save_commentary_services()

        orchestrator.commentary_service.save.assert_called_once()
        orchestrator.reference_service.save.assert_called_once()
        orchestrator.statement_service.save.assert_called_once()
        # Generic_text should not be saved
        orchestrator.generic_text_service.save.assert_not_called()

    def test_refresh_topics(self, orchestrator):
        """Test refreshing topics for statement service."""
        orchestrator._refresh_topics()

        orchestrator.statement_service.refresh_topics.assert_called_once()

    def test_refresh_topics_with_error(self, orchestrator):
        """Test refresh topics handles errors gracefully."""
        orchestrator.statement_service.refresh_topics.side_effect = Exception(
            "Topic error"
        )

        # Should not raise exception
        orchestrator._refresh_topics()

        orchestrator.statement_service.refresh_topics.assert_called_once()

    def test_should_stop_processing_without_callback(self, orchestrator):
        """Test stop processing check without callback."""
        result = orchestrator._should_stop_processing()
        # Without callback it should return falsy (None or False)
        assert not result

    def test_should_stop_processing_with_callback_false(self, orchestrator):
        """Test stop processing check with callback returning False."""
        orchestrator._stop_callback = MagicMock(return_value=False)
        result = orchestrator._should_stop_processing()
        assert result is False

    def test_should_stop_processing_with_callback_true(self, orchestrator):
        """Test stop processing check with callback returning True."""
        orchestrator._stop_callback = MagicMock(return_value=True)
        result = orchestrator._should_stop_processing()
        assert result is True

    @patch("services.orchestration.content_orchestrator.DataLoader")
    @patch("os.path.exists")
    @pytest.mark.skip(reason="commentsuggestion functionality has been removed")
    def test_load_commentsuggestions_data(
        self, mock_exists, mock_data_loader, orchestrator
    ):
        """Test loading commentsuggestions data."""
        mock_exists.return_value = True
        mock_data = [
            {
                "statement": "Test statement",
                "commentsuggestions": ["Comment 1", "Comment 2"],
            }
        ]
        mock_data_loader.load_json_data_files.return_value = mock_data

        result = orchestrator._load_commentsuggestions_data()

        assert result == mock_data
        mock_data_loader.load_json_data_files.assert_called_once()

    @patch("os.path.exists")
    @pytest.mark.skip(reason="commentsuggestion functionality has been removed")
    def test_load_commentsuggestions_data_no_path(self, mock_exists, orchestrator):
        """Test loading commentsuggestions when path doesn't exist."""
        mock_exists.return_value = False

        result = orchestrator._load_commentsuggestions_data()

        assert result == []

    @patch("services.orchestration.content_orchestrator.DataLoader")
    @patch("os.path.exists")
    def test_load_commentaries_data(self, mock_exists, mock_data_loader, orchestrator):
        """Test loading commentaries data."""
        mock_exists.return_value = True
        mock_data = [
            {
                "statement": "Test statement",
                "commentaries": [
                    {
                        "text": "Commentary text",
                        "title": "Commentary title",
                        "references": [],
                    }
                ],
            }
        ]
        mock_data_loader.load_json_data_files.return_value = mock_data

        result = orchestrator._load_commentaries_data()

        assert result == mock_data
        mock_data_loader.load_json_data_files.assert_called_once()

    @patch("services.orchestration.content_orchestrator.DataLoader")
    @patch("os.path.exists")
    def test_calculate_total_work_items(
        self, mock_exists, mock_data_loader, orchestrator
    ):
        """Test calculating total work items."""
        mock_exists.return_value = True
        # Mock data for both datasets
        mock_data_loader.load_json_data_files.side_effect = [
            [
                {"statement": "S1", "commentsuggestions": ["C1"]},
                {"statement": "S2", "commentsuggestions": ["C2"]},
            ],  # 2 items
            [
                {"statement": "S3", "commentaries": [{"text": "C3", "title": "T3"}]},
                {"statement": "S4", "commentaries": [{"text": "C4", "title": "T4"}]},
                {"statement": "S5", "commentaries": [{"text": "C5", "title": "T5"}]},
            ],  # 3 items
        ]

        total = orchestrator._calculate_total_work_items()

        assert total == 5  # 2 + 3

    @pytest.mark.skip(reason="commentsuggestion functionality has been removed")
    def test_process_single_commentsuggestion_item(self, orchestrator):
        """Test processing a single commentsuggestion item."""
        item = {
            "statement": "Test statement",
            "commentsuggestions": ["Comment 1", "Comment 2"],
        }

        comment_ids = [uuid.uuid4(), uuid.uuid4()]
        orchestrator.data_processor.process_commentsuggestion = MagicMock(
            side_effect=comment_ids
        )
        orchestrator.data_processor.create_statement_with_replies = MagicMock()

        orchestrator._process_single_commentsuggestion_item(item)

        assert orchestrator.data_processor.process_commentsuggestion.call_count == 2
        orchestrator.data_processor.create_statement_with_replies.assert_called_once_with(
            "Test statement", comment_ids
        )

    @pytest.mark.skip(reason="commentsuggestion functionality has been removed")
    def test_process_single_commentary_item(self, orchestrator):
        """Test processing a single commentary item."""
        item = {
            "statement": "Test statement",
            "commentaries": [
                {"text": "Commentary 1", "title": "Title 1"},
                {"text": "Commentary 2", "title": "Title 2"},
            ],
        }

        commentary_ids = [uuid.uuid4(), uuid.uuid4()]
        orchestrator.data_processor.create_commentary_with_references = MagicMock(
            side_effect=commentary_ids
        )
        orchestrator.data_processor.create_statement_with_replies = MagicMock()

        orchestrator._process_single_commentary_item(item)

        assert (
            orchestrator.data_processor.create_commentary_with_references.call_count
            == 2
        )
        orchestrator.data_processor.create_statement_with_replies.assert_called_once_with(
            "Test statement", commentary_ids
        )


@pytest.mark.unit
class TestContentOrchestratorIntegration:
    """Test ContentOrchestrator with real services using dependency injection."""

    @pytest.fixture
    def orchestrator(self, test_settings, repository_factory):
        """Create content orchestrator with real services and test repository factory."""
        from services.content.statement_service import StatementService
        from services.content.commentary_service import CommentaryService
        from services.content.reference_service import ReferenceService
        from services.content.generic_text_service import GenericTextService

        # Create services with test repository factory
        statement_service = StatementService(test_settings, repository_factory)
        commentary_service = CommentaryService(test_settings, repository_factory)
        reference_service = ReferenceService(test_settings, repository_factory)
        generic_text_service = GenericTextService(test_settings, repository_factory)

        return ContentOrchestrator(
            test_settings,
            commentary_service=commentary_service,
            reference_service=reference_service,
            statement_service=statement_service,
            generic_text_service=generic_text_service,
        )

    @pytest.mark.skip(reason="commentsuggestion functionality has been removed")
    def test_orchestrator_with_real_services(
        self, orchestrator, test_embeddings_manager
    ):
        """Test orchestrator with real services integration."""
        # Clear test data
        test_embeddings_manager.clear()

        # Process a comment suggestion
        comment_id = orchestrator.data_processor.process_commentsuggestion(
            "Test comment"
        )

        # Verify it was added
        assert isinstance(comment_id, uuid.UUID)
        stored_data = test_embeddings_manager.get_data()
        assert str(comment_id) in stored_data
        assert stored_data[str(comment_id)]["text"] == "Test comment"

    @pytest.mark.skip(reason="commentsuggestion functionality has been removed")
    def test_full_workflow_with_statements_and_replies(
        self, orchestrator, test_embeddings_manager
    ):
        """Test full workflow of creating statements with reply suggestions."""
        # Clear test data
        test_embeddings_manager.clear()

        # Create some comment suggestions
        reply_ids = []
        for i in range(3):
            comment_id = orchestrator.data_processor.process_commentsuggestion(
                f"Reply suggestion {i}"
            )
            reply_ids.append(comment_id)

        # Create statement with replies
        orchestrator.data_processor.create_statement_with_replies(
            "Important climate statement", reply_ids
        )

        # Verify data was created
        stored_data = test_embeddings_manager.get_data()

        # Should have 3 commentaries + 1 statement
        assert len(stored_data) == 4

        # Find the statement
        statement_data = None
        for data in stored_data.values():
            if data.get("content_type") == "statement":
                statement_data = data
                break

        assert statement_data is not None
        assert statement_data["text"] == "Important climate statement"
        assert len(statement_data.get("replysuggestions", [])) == 3
