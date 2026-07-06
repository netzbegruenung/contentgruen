import asyncio
import os
import psutil
from datetime import datetime
from typing import Optional, List
import threading

from core.logging import get_logger

from core.config import Settings
from services.embeddings.qdrant_embeddings_manager import QdrantEmbeddingsManager
from services.orchestration.content_orchestrator import ContentOrchestrator
from services.content.commentary_service import CommentaryService
from services.content.reference_service import ReferenceService
from services.content.statement_service import StatementService
from services.content.generic_text_service import GenericTextService
from utils.data_utils import DataLoader
from services.seeding.seeding_status import (
    SeedingStatus,
    SeedingProgress,
    SeedingMetadata,
    SeedingFileStatus,
    FileProcessingStatus,
)

logger = get_logger(__name__)


class SeedingService:
    """
    Asynchronous seeding service that runs in background without blocking application startup.
    Uses file-based metadata storage for tracking seeding progress.
    """

    def __init__(
        self,
        settings: Settings,
        shared_embeddings_manager: QdrantEmbeddingsManager,
        metadata_path: str = "/metadata",
    ):
        self.settings = settings
        self.shared_embeddings_manager = shared_embeddings_manager
        self.metadata_path = metadata_path
        self.metadata = SeedingMetadata(
            os.path.join(metadata_path, "seeding_status.json")
        )

        # Threading lock for status updates
        self._lock = threading.Lock()
        self._current_progress: Optional[SeedingProgress] = None

        # Graceful stop mechanism
        self._stop_requested = False

        # Create metadata directory if it doesn't exist
        os.makedirs(metadata_path, exist_ok=True)

    async def needs_seeding(self) -> bool:
        """
        Check if seeding is needed for incremental/idempotent seeding.
        Returns True if there are new JSON files to process or if database is empty.
        """
        try:
            # Ensure embeddings manager is started to check database content
            if not self.shared_embeddings_manager.is_started:
                logger.info(
                    "🌱 Starting embeddings manager to check database content..."
                )
                self.shared_embeddings_manager.start()

            content_count = self.shared_embeddings_manager.count()
            logger.info(f"🔢 Found {content_count} items in unified_content_index")

            # Get list of available JSON files
            json_files = await self._discover_json_files()
            logger.info(f"🔍 Found {len(json_files)} JSON files to potentially process")

            # Check for incomplete seeding that should be resumed
            progress = await self.metadata.load_progress()
            if progress and progress.status in [
                SeedingStatus.INTERRUPTED,
                SeedingStatus.FAILED,
            ]:
                logger.info(
                    f"⚠️ Previous seeding was {progress.status.value}, will attempt to resume"
                )
                return True

            # For idempotent seeding: Always return True if we have JSON files
            # The actual duplicate checking happens during processing
            if len(json_files) > 0:
                if content_count == 0:
                    logger.info(
                        "🌱 Empty database with seed files available - seeding needed"
                    )
                else:
                    logger.info(
                        "🌱 Incremental seeding available - will check for new content"
                    )
                return True
            else:
                logger.info("🌱 No seed files found - seeding not needed")
                return False

        except Exception as e:
            logger.error(f"❌ Error checking if seeding needed: {e}", exc_info=True)
            # If we can't check, assume we need seeding to be safe
            return True

    async def get_progress(self) -> SeedingProgress:
        """Get current seeding progress."""
        with self._lock:
            if self._current_progress:
                return self._current_progress

        # Load from file if not in memory
        progress = await self.metadata.load_progress()
        if progress:
            with self._lock:
                self._current_progress = progress
            return progress

        # Default progress if no metadata found
        return SeedingProgress(status=SeedingStatus.NOT_STARTED)

    def _check_pid_lock(self) -> bool:
        """Check if another seeding process is running via PID file."""
        pid_file = os.path.join(self.metadata_path, "seeding.pid")

        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r") as f:
                    pid = int(f.read().strip())

                # Check if process is still running
                if psutil.pid_exists(pid):
                    try:
                        process = psutil.Process(pid)
                        # Check if it's actually a Python process (our seeding)
                        if "python" in process.name().lower():
                            logger.warning(
                                f"🔒 Seeding process already running with PID {pid}"
                            )
                            return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                # PID exists but process is dead, clean up
                logger.info(f"🔓 Removing stale PID file for dead process {pid}")
                os.remove(pid_file)
            except (ValueError, IOError) as e:
                logger.error(f"Error reading PID file: {e}")
                # Remove corrupted PID file
                os.remove(pid_file)

        return False

    def _create_pid_lock(self) -> None:
        """Create PID file for current process."""
        pid_file = os.path.join(self.metadata_path, "seeding.pid")
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
        logger.info(f"🔐 Created PID lock file with PID {os.getpid()}")

    def _remove_pid_lock(self) -> None:
        """Remove PID file."""
        pid_file = os.path.join(self.metadata_path, "seeding.pid")
        if os.path.exists(pid_file):
            try:
                os.remove(pid_file)
                logger.info("🔓 Removed PID lock file")
            except Exception as e:
                logger.error(f"Error removing PID file: {e}")

    async def start_seeding(self) -> None:
        """
        Start the seeding process in background.
        This method should be called as a background task.
        """
        logger.info(f"🌱 Starting background seeding process...")

        # Check for existing lock
        if self._check_pid_lock():
            logger.warning("🔒 Another seeding process is already running, aborting")
            raise RuntimeError("Seeding process is already running")

        try:
            # Create PID lock
            self._create_pid_lock()

            # Reset stop flag for new seeding
            with self._lock:
                self._stop_requested = False

            # Initialize progress
            progress = SeedingProgress(
                status=SeedingStatus.RUNNING, started_at=datetime.now()
            )

            with self._lock:
                self._current_progress = progress
            await self.metadata.save_progress(progress)

            # Get list of JSON files to process
            json_files = await self._discover_json_files()
            progress.total_files = len(json_files)

            logger.info(f"🌱 Found {len(json_files)} JSON files to process")

            if len(json_files) == 0:
                progress.status = SeedingStatus.COMPLETED
                progress.completed_at = datetime.now()
                with self._lock:
                    self._current_progress = progress
                await self.metadata.save_progress(progress)
                logger.info(f"🌱 No JSON files found, seeding marked as completed")
                self._remove_pid_lock()  # Clean up PID lock before returning
                return

            # Create index managers
            content_services = self._create_content_services()
            coordinator = ContentOrchestrator(
                self.settings,
                content_services["commentary"],
                content_services["reference"],
                content_services["statement"],
                content_services["generic_text"],
            )

            # Process files with proper progress tracking
            await self._process_files_with_progress(coordinator, json_files, progress)

            # Check if stop was requested during processing
            if self._check_stop_requested():
                logger.info("🛑 Seeding was stopped gracefully during processing")
                self._remove_pid_lock()  # Clean up PID lock before returning
                return  # Exit without marking as completed

            # Update progress with seeding statistics and fingerprints
            progress.status = SeedingStatus.COMPLETED
            progress.completed_at = datetime.now()
            progress.content_added = coordinator.seeding_stats["added"]
            progress.content_skipped = coordinator.seeding_stats["skipped"]
            progress.processed_fingerprints = list(coordinator.processed_fingerprints)

            with self._lock:
                self._current_progress = progress
            await self.metadata.save_progress(progress)

            # Log comprehensive seeding summary
            summary = coordinator.get_seeding_summary()
            logger.info(f"🌱 Background seeding completed successfully! {summary}")

        except Exception as e:
            logger.error(f"❌ Error during seeding: {e}", exc_info=True)

            # Mark as failed with better error handling
            try:
                progress = await self.get_progress()
                progress.status = SeedingStatus.FAILED
                progress.error_message = str(e)
                progress.completed_at = datetime.now()

                with self._lock:
                    self._current_progress = progress
                await self.metadata.save_progress(progress)
            except Exception as save_error:
                logger.error(
                    f"❌ Additional error saving failed status: {save_error}",
                    exc_info=True,
                )
        finally:
            # Always remove PID lock when done
            self._remove_pid_lock()

    async def _discover_json_files(self) -> List[str]:
        """Discover all JSON files that need to be processed from the new data structure."""
        json_files = []

        # Use the same path configuration as the main application
        seed_data_path = self.settings.data_path
        logger.info(f"🔍 Looking for seed data in: {seed_data_path}")

        # Check statements_with_commentaries directory
        commentaries_path = os.path.join(seed_data_path, "statements_with_commentaries")
        if os.path.exists(commentaries_path):
            for file in os.listdir(commentaries_path):
                if file.endswith(".json"):
                    json_files.append(os.path.join(commentaries_path, file))

        # Check statements_with_generictexts directory
        generictexts_path = os.path.join(seed_data_path, "statements_with_generictexts")
        if os.path.exists(generictexts_path):
            for file in os.listdir(generictexts_path):
                if file.endswith(".json"):
                    json_files.append(os.path.join(generictexts_path, file))

        # Check individual index data directories
        index_data_path = os.path.join(seed_data_path, "index_data")
        if os.path.exists(index_data_path):
            for content_type in [
                "commentary",
                "reference",
                "statement",
                "generic_text",
            ]:
                type_path = os.path.join(index_data_path, content_type + "_index")
                if os.path.exists(type_path):
                    for file in os.listdir(type_path):
                        if file.endswith(".json"):
                            json_files.append(os.path.join(type_path, file))

        return sorted(json_files)

    def _create_content_services(self) -> dict:
        """Create content service instances."""
        return {
            "commentary": CommentaryService(self.settings),
            "reference": ReferenceService(self.settings),
            "statement": StatementService(self.settings),
            "generic_text": GenericTextService(self.settings),
        }

    async def _process_files_with_progress(
        self,
        coordinator: ContentOrchestrator,
        json_files: List[str],
        progress: SeedingProgress,
    ) -> None:
        """Process files with proper progress tracking and error handling."""
        try:
            logger.info("🌱 Starting file processing with progress tracking...")

            # Create file status tracking
            file_statuses = []
            for file_path in json_files:
                file_status = SeedingFileStatus(
                    file_path=file_path,
                    status=FileProcessingStatus.PENDING,
                    file_size_bytes=(
                        os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    ),
                    content_type=self._determine_content_type(file_path),
                )
                file_statuses.append(file_status)

            # Save initial file statuses
            await self.metadata.save_file_statuses(file_statuses)

            # Phase 1: Initialize coordinator
            await self._update_progress(
                progress, "Initializing index managers...", file_statuses
            )

            original_path = coordinator.initial_data_path
            seed_data_path = self._get_seed_data_path()
            coordinator.initial_data_path = seed_data_path

            try:
                # Load previously processed fingerprints for idempotent seeding
                existing_progress = await self.metadata.load_progress()
                if existing_progress and existing_progress.processed_fingerprints:
                    coordinator.load_processed_fingerprints(
                        set(existing_progress.processed_fingerprints)
                    )
                    logger.info(
                        f"🔍 Loaded {len(existing_progress.processed_fingerprints)} processed fingerprints"
                    )
                else:
                    coordinator.load_processed_fingerprints(set())
                    logger.info(
                        "🔍 Starting fresh seeding - no previous fingerprints found"
                    )

                # Reset stats for new seeding session
                coordinator.reset_seeding_stats()

                # Run coordinator initialization with progress updates
                await self._run_coordinator_with_progress(
                    coordinator, progress, file_statuses
                )

            finally:
                # Always restore original path
                coordinator.initial_data_path = original_path

        except Exception as e:
            logger.error(f"❌ Error during file processing: {e}", exc_info=True)

            # Mark remaining files as failed
            if "file_statuses" in locals():
                for file_status in file_statuses:
                    if file_status.status == FileProcessingStatus.PENDING:
                        file_status.status = FileProcessingStatus.FAILED
                        file_status.error_message = str(e)

                await self.metadata.save_file_statuses(file_statuses)
            raise

    async def reset_seeding(self) -> None:
        """Reset seeding status and clear all metadata."""
        logger.info("🔄 Resetting seeding status...")

        with self._lock:
            self._current_progress = None

        await self.metadata.clear_metadata()
        logger.info("✅ Seeding status reset")

    async def wait_for_completion(self, timeout_seconds: int = 600) -> bool:
        """
        Wait for seeding to complete (useful for tests or admin operations).

        Args:
            timeout_seconds: Maximum time to wait in seconds

        Returns:
            True if seeding completed successfully, False if timeout or failed
        """
        start_time = datetime.now()

        while True:
            progress = await self.get_progress()

            if progress.is_complete():
                return progress.status == SeedingStatus.COMPLETED

            if progress.status == SeedingStatus.FAILED:
                return False

            # Check timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout_seconds:
                logger.warning(
                    f"⏰ Timeout waiting for seeding completion after {timeout_seconds}s"
                )
                return False

            # Wait before checking again
            await asyncio.sleep(1)

    def _get_seed_data_path(self) -> str:
        """Get the seed data path from settings configuration."""
        # Use the same path configuration as the main application
        return self.settings.data_path

    def _determine_content_type(self, file_path: str) -> str:
        """Determine content type based on file path."""
        if "statements_with_commentaries" in file_path:
            return "statements_with_commentaries"
        elif "statements_with_generictexts" in file_path:
            return "statements_with_generictexts"
        elif "commentary_index" in file_path:
            return "commentary"
        elif "reference_index" in file_path:
            return "reference"
        elif "statement_index" in file_path:
            return "statement"
        elif "generic_text_index" in file_path:
            return "generic_text"
        else:
            return "unknown"

    async def _update_progress(
        self,
        progress: SeedingProgress,
        current_file: str,
        file_statuses: List[SeedingFileStatus],
    ) -> None:
        """Update progress and save both progress and file statuses."""
        progress.current_file = current_file
        progress.last_updated = datetime.now()

        with self._lock:
            self._current_progress = progress

        await self.metadata.save_progress(progress)
        await self.metadata.save_file_statuses(file_statuses)

    async def resume_seeding(self) -> None:
        """Resume interrupted seeding from last checkpoint."""
        logger.info("🔄 Attempting to resume interrupted seeding...")

        progress = await self.get_progress()
        if progress.status not in [SeedingStatus.INTERRUPTED, SeedingStatus.FAILED]:
            logger.warning(
                f"⚠️ No interrupted/failed seeding found to resume (current status: {progress.status.value})"
            )
            return

        progress.status = SeedingStatus.RESUMING
        progress.resumed_at = datetime.now()
        await self.metadata.save_progress(progress)

        # Continue with seeding
        progress.status = SeedingStatus.RUNNING
        await self.start_seeding()

    async def request_stop(self) -> None:
        """Request graceful stop of running seeding process."""
        logger.info("🛑 Graceful stop requested for seeding...")

        with self._lock:
            self._stop_requested = True

        # Update progress to show stop was requested
        progress = await self.get_progress()
        if progress.is_running():
            progress.current_file = "Stop requested - finishing current item..."
            await self.metadata.save_progress(progress)

    def _check_stop_requested(self) -> bool:
        """Check if graceful stop was requested."""
        with self._lock:
            return self._stop_requested

    async def _run_coordinator_with_progress(
        self,
        coordinator: ContentOrchestrator,
        progress: SeedingProgress,
        file_statuses: List[SeedingFileStatus],
    ) -> None:
        """Run coordinator initialization with REAL progress updates from actual file processing."""

        # Track progress state
        self._processed_files = 0
        self._total_discovered_files = 0

        def real_progress_callback(filename: str, current_index: int, total_files: int):
            """Real progress callback that gets called for each file actually processed by the coordinator."""
            try:
                # Update total files count if this is the first callback or we discovered more files
                if total_files > self._total_discovered_files:
                    self._total_discovered_files = total_files
                    progress.total_files = total_files

                # Find the file status for this file and update it
                matching_file_status = None
                for file_status in file_statuses:
                    if (
                        filename in file_status.file_path
                        or file_status.file_path.endswith(filename)
                    ):
                        matching_file_status = file_status
                        break

                # Update file status
                if matching_file_status:
                    matching_file_status.status = FileProcessingStatus.COMPLETED
                    matching_file_status.processed_at = datetime.now()
                else:
                    # Create a new file status if we didn't track this file initially
                    file_status = SeedingFileStatus(
                        file_path=filename,
                        status=FileProcessingStatus.COMPLETED,
                        processed_at=datetime.now(),
                        content_type=self._determine_content_type(filename),
                    )
                    file_statuses.append(file_status)

                # Update overall progress
                self._processed_files = current_index + 1
                progress.files_processed = self._processed_files
                progress.current_file = filename
                progress.update_processing_rate()

                logger.debug(
                    f"🌱 Real progress: {filename} ({self._processed_files}/{total_files})"
                )

                # This would be async in the real callback, but we can't make the callback async
                # So we'll update the progress synchronously here and save async later
                progress.current_file = f"Processing {filename}"
                progress.last_updated = datetime.now()

            except Exception as e:
                logger.error(f"Error in progress callback: {e}", exc_info=True)

        logger.info("🌱 Running coordinator with REAL progress tracking...")

        # Set stop callback on coordinator for graceful interruption
        coordinator._stop_callback = self._check_stop_requested

        # Run coordinator with real progress callback
        try:
            await coordinator.initialize_repositories(real_progress_callback)
        except Exception as e:
            # Check if this was a graceful stop
            if self._check_stop_requested():
                logger.info("🛑 Seeding stopped gracefully by user request")
                # Mark as interrupted for potential resume
                progress.status = SeedingStatus.INTERRUPTED
                progress.current_file = "Stopped by user request"
                progress.completed_at = datetime.now()
                await self._update_progress(
                    progress, "Stopped by user request", file_statuses
                )
                return
            else:
                # Re-raise if not a graceful stop
                raise

        # Check if stop was requested after coordinator finished normally
        if self._check_stop_requested():
            logger.info("🛑 Seeding stopped gracefully by user request")
            # Mark as interrupted for potential resume
            progress.status = SeedingStatus.INTERRUPTED
            progress.current_file = "Stopped by user request"
            progress.completed_at = datetime.now()
            await self._update_progress(
                progress, "Stopped by user request", file_statuses
            )
            return

        # Ensure all file statuses are marked as completed
        for file_status in file_statuses:
            if file_status.status == FileProcessingStatus.PENDING:
                file_status.status = FileProcessingStatus.COMPLETED
                file_status.processed_at = datetime.now()

        # Final progress update
        progress.files_processed = len(file_statuses)
        progress.current_file = "Completed"
        await self._update_progress(
            progress, "All files processed successfully", file_statuses
        )

        logger.info(
            f"🌱 Coordinator completed - processed {self._processed_files} files"
        )


# Global seeding service instance
_seeding_service: Optional[SeedingService] = None


def get_seeding_service(
    settings: Optional[Settings] = None,
    shared_embeddings_manager: Optional[QdrantEmbeddingsManager] = None,
    metadata_path: str = "/metadata",
) -> SeedingService:
    """Get the global seeding service instance."""
    global _seeding_service

    if _seeding_service is None:
        if not settings or not shared_embeddings_manager:
            raise RuntimeError(
                "Settings and QdrantEmbeddingsManager required for first initialization"
            )
        _seeding_service = SeedingService(
            settings, shared_embeddings_manager, metadata_path
        )

    return _seeding_service
