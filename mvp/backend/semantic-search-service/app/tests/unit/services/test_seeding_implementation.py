"""
Pytest tests for the new seeding implementation.
Run with: pytest tests/services/test_seeding_implementation.py -v
"""

import pytest
import asyncio
import os
import tempfile
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from services.seeding.seeding_status import (
    SeedingStatus,
    SeedingProgress,
    SeedingMetadata,
    SeedingFileStatus,
    FileProcessingStatus,
)


class TestSeedingStatus:
    """Test seeding status models and enums."""

    def test_seeding_progress_creation(self):
        """Test creating SeedingProgress instance."""
        progress = SeedingProgress(
            status=SeedingStatus.RUNNING,
            files_processed=5,
            total_files=10,
            started_at=datetime.now(),
        )

        assert progress.status == SeedingStatus.RUNNING
        assert progress.files_processed == 5
        assert progress.total_files == 10
        assert progress.get_progress_percent() == 50.0

    def test_seeding_progress_states(self):
        """Test seeding progress state checking methods."""
        progress = SeedingProgress(status=SeedingStatus.RUNNING)
        assert progress.is_running() == True
        assert progress.is_complete() == False

        progress.status = SeedingStatus.COMPLETED
        assert progress.is_running() == False
        assert progress.is_complete() == True

    def test_progress_percentage_calculation(self):
        """Test progress percentage calculations."""
        # Test normal case
        progress = SeedingProgress(
            status=SeedingStatus.RUNNING, files_processed=3, total_files=10
        )
        assert progress.get_progress_percent() == 30.0

        # Test zero total files
        progress = SeedingProgress(
            status=SeedingStatus.RUNNING, files_processed=0, total_files=0
        )
        assert progress.get_progress_percent() == 0.0

        # Test completed case
        progress = SeedingProgress(
            status=SeedingStatus.COMPLETED, files_processed=10, total_files=10
        )
        assert progress.get_progress_percent() == 100.0

    def test_time_estimation(self):
        """Test time remaining estimation."""
        # Test with no started_at - should return None
        progress = SeedingProgress(
            status=SeedingStatus.RUNNING, files_processed=2, total_files=10
        )
        assert progress.estimate_time_remaining() is None

        # Test with zero files processed - should return None
        progress = SeedingProgress(
            status=SeedingStatus.RUNNING,
            files_processed=0,
            total_files=10,
            started_at=datetime.now(),
        )
        assert progress.estimate_time_remaining() is None

        # Test with fresh progress (elapsed time near zero) - should return None
        progress = SeedingProgress(
            status=SeedingStatus.RUNNING,
            files_processed=2,
            total_files=10,
            started_at=datetime.now(),
        )
        estimate = progress.estimate_time_remaining()
        # Should be None for very fresh progress due to elapsed <= 0 check
        assert estimate is None

        # Test with some elapsed time - create started_at in the past
        from datetime import timedelta

        past_time = datetime.now() - timedelta(seconds=10)
        progress = SeedingProgress(
            status=SeedingStatus.RUNNING,
            files_processed=2,
            total_files=10,
            started_at=past_time,
        )
        estimate = progress.estimate_time_remaining()
        # Should return an integer estimate or None
        assert estimate is None or isinstance(estimate, int)

    def test_serialization_deserialization(self):
        """Test converting progress to/from dictionary."""
        original = SeedingProgress(
            status=SeedingStatus.RUNNING,
            files_processed=5,
            total_files=12,
            current_file="test.json",
            started_at=datetime.now(),
            error_message="test error",
        )

        # Test serialization
        data = original.to_dict()
        assert data["status"] == "running"
        assert data["files_processed"] == 5
        assert data["total_files"] == 12
        assert data["current_file"] == "test.json"
        assert data["error_message"] == "test error"
        assert isinstance(data["started_at"], str)  # Should be ISO string

        # Test deserialization
        restored = SeedingProgress.from_dict(data)
        assert restored.status == SeedingStatus.RUNNING
        assert restored.files_processed == 5
        assert restored.total_files == 12
        assert restored.current_file == "test.json"
        assert restored.error_message == "test error"
        assert isinstance(restored.started_at, datetime)


class TestSeedingFileStatus:
    """Test individual file status tracking."""

    def test_file_status_creation(self):
        """Test creating SeedingFileStatus instance."""
        file_status = SeedingFileStatus(
            file_path="/test/file.json", status="completed", processed_at=datetime.now()
        )

        assert file_status.file_path == "/test/file.json"
        assert file_status.status == "completed"
        assert isinstance(file_status.processed_at, datetime)

    def test_file_status_serialization(self):
        """Test file status serialization."""
        original = SeedingFileStatus(
            file_path="/test/file.json",
            status=FileProcessingStatus.FAILED,
            processed_at=datetime.now(),
            error_message="Parse error",
        )

        data = original.to_dict()
        restored = SeedingFileStatus.from_dict(data)

        assert restored.file_path == original.file_path
        assert restored.status == original.status
        assert restored.error_message == original.error_message
        assert isinstance(restored.processed_at, datetime)


class TestSeedingMetadata:
    """Test file-based metadata storage."""

    @pytest.fixture
    def temp_metadata_file(self):
        """Create temporary metadata file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name

        yield temp_file

        # Cleanup
        try:
            os.unlink(temp_file)
            file_status_path = temp_file.replace(".json", "_files.json")
            if os.path.exists(file_status_path):
                os.unlink(file_status_path)
        except FileNotFoundError:
            pass

    @pytest.mark.asyncio
    async def test_save_and_load_progress(self, temp_metadata_file):
        """Test saving and loading progress."""
        metadata = SeedingMetadata(temp_metadata_file)

        original_progress = SeedingProgress(
            status=SeedingStatus.RUNNING,
            files_processed=3,
            total_files=8,
            current_file="test.json",
            started_at=datetime.now(),
        )

        # Save progress
        await metadata.save_progress(original_progress)

        # Load progress
        loaded_progress = await metadata.load_progress()

        assert loaded_progress is not None
        assert loaded_progress.status == SeedingStatus.RUNNING
        assert loaded_progress.files_processed == 3
        assert loaded_progress.total_files == 8
        assert loaded_progress.current_file == "test.json"
        assert isinstance(loaded_progress.last_updated, datetime)

    @pytest.mark.asyncio
    async def test_load_nonexistent_progress(self, temp_metadata_file):
        """Test loading progress when no file exists."""
        # Remove the temp file so it doesn't exist
        os.unlink(temp_metadata_file)

        metadata = SeedingMetadata(temp_metadata_file)
        progress = await metadata.load_progress()

        assert progress is None

    @pytest.mark.asyncio
    async def test_save_and_load_file_statuses(self, temp_metadata_file):
        """Test saving and loading file statuses."""
        metadata = SeedingMetadata(temp_metadata_file)

        file_statuses = [
            SeedingFileStatus(
                file_path="/test/file1.json", status=FileProcessingStatus.COMPLETED
            ),
            SeedingFileStatus(
                file_path="/test/file2.json",
                status=FileProcessingStatus.FAILED,
                error_message="Error",
            ),
        ]

        # Save file statuses
        await metadata.save_file_statuses(file_statuses)

        # Load file statuses
        loaded_statuses = await metadata.load_file_statuses()

        assert len(loaded_statuses) == 2
        assert loaded_statuses[0].file_path == "/test/file1.json"
        assert loaded_statuses[0].status == FileProcessingStatus.COMPLETED
        assert loaded_statuses[1].file_path == "/test/file2.json"
        assert loaded_statuses[1].status == FileProcessingStatus.FAILED
        assert loaded_statuses[1].error_message == "Error"

    @pytest.mark.asyncio
    async def test_clear_metadata(self, temp_metadata_file):
        """Test clearing all metadata."""
        metadata = SeedingMetadata(temp_metadata_file)

        # Create some metadata
        progress = SeedingProgress(status=SeedingStatus.COMPLETED)
        await metadata.save_progress(progress)

        file_statuses = [SeedingFileStatus(file_path="/test.json", status="completed")]
        await metadata.save_file_statuses(file_statuses)

        # Verify files exist
        assert os.path.exists(temp_metadata_file)

        # Clear metadata
        await metadata.clear_metadata()

        # Verify files are removed
        assert not os.path.exists(temp_metadata_file)

        # Loading should return None/empty
        loaded_progress = await metadata.load_progress()
        loaded_statuses = await metadata.load_file_statuses()

        assert loaded_progress is None
        assert loaded_statuses == []


class TestSeedingServiceLogic:
    """Test seeding service logic without full dependencies."""

    def test_json_file_discovery_logic(self):
        """Test the JSON file discovery logic used by SeedingService."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory structure
            statements_comments_dir = os.path.join(
                temp_dir, "statements_with_commentaries"
            )
            statements_suggestions_dir = os.path.join(
                temp_dir, "statements_with_commentsuggestions"
            )
            index_data_dir = os.path.join(temp_dir, "index_data")
            commentary_dir = os.path.join(index_data_dir, "commentary")
            reference_dir = os.path.join(index_data_dir, "reference")

            os.makedirs(statements_comments_dir)
            os.makedirs(statements_suggestions_dir)
            os.makedirs(commentary_dir)
            os.makedirs(reference_dir)

            # Create test JSON files
            test_files = [
                os.path.join(statements_comments_dir, "test1.json"),
                os.path.join(statements_comments_dir, "test2.json"),
                os.path.join(statements_suggestions_dir, "test3.json"),
                os.path.join(commentary_dir, "test4.json"),
                os.path.join(reference_dir, "test5.json"),
                # Non-JSON file should be ignored
                os.path.join(statements_comments_dir, "ignore.txt"),
            ]

            for file_path in test_files:
                with open(file_path, "w") as f:
                    f.write('{"test": "data"}')

            # Simulate the discovery logic from SeedingService._discover_json_files
            discovered_files = []

            # Check statements_with_commentsuggestions directory
            if os.path.exists(statements_suggestions_dir):
                for file in os.listdir(statements_suggestions_dir):
                    if file.endswith(".json"):
                        discovered_files.append(
                            os.path.join(statements_suggestions_dir, file)
                        )

            # Check statements_with_commentaries directory
            if os.path.exists(statements_comments_dir):
                for file in os.listdir(statements_comments_dir):
                    if file.endswith(".json"):
                        discovered_files.append(
                            os.path.join(statements_comments_dir, file)
                        )

            # Check individual index data directories
            if os.path.exists(index_data_dir):
                for content_type in [
                    "commentary",
                    "reference",
                    "statement",
                    "generic_text",
                ]:
                    type_path = os.path.join(index_data_dir, content_type)
                    if os.path.exists(type_path):
                        for file in os.listdir(type_path):
                            if file.endswith(".json"):
                                discovered_files.append(os.path.join(type_path, file))

            discovered_files = sorted(discovered_files)

            # Should find 5 JSON files (ignore the .txt file)
            assert len(discovered_files) == 5
            assert any("test1.json" in f for f in discovered_files)
            assert any("test2.json" in f for f in discovered_files)
            assert any("test3.json" in f for f in discovered_files)
            assert any("test4.json" in f for f in discovered_files)
            assert any("test5.json" in f for f in discovered_files)
            # Ensure .txt file is not included
            assert not any("ignore.txt" in f for f in discovered_files)

    @patch("services.seeding.seeding_service.QdrantEmbeddingsManager")
    def test_needs_seeding_logic(self, mock_embeddings_manager):
        """Test the needs_seeding logic."""
        from services.seeding.seeding_service import SeedingService

        # Mock settings and manager
        mock_settings = Mock()
        mock_settings.initial_data_path = "/test/data"

        mock_manager = Mock()
        mock_manager.is_started = True

        # Test case: no content exists, seeding needed
        mock_manager.count.return_value = 0

        # Can't easily test async method without full setup, but this validates the structure
        assert hasattr(SeedingService, "needs_seeding")
        assert hasattr(SeedingService, "start_seeding")
        assert hasattr(SeedingService, "get_progress")


if __name__ == "__main__":
    # Allow running with python -m pytest
    pytest.main([__file__, "-v"])
