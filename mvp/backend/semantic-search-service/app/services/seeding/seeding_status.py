from enum import Enum
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from pathlib import Path
import json
import uuid
import logging


class SeedingStatus(Enum):
    """Seeding operation status."""

    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    PAUSED = "paused"
    RESUMING = "resuming"


class FileProcessingStatus(Enum):
    """Individual file processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SeedingProgress:
    """Seeding progress tracking with enhanced file-level detail."""

    status: SeedingStatus
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    files_processed: int = 0
    total_files: int = 0
    current_file: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    resumed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    last_updated: Optional[datetime] = None
    files_failed: int = 0
    files_skipped: int = 0
    processing_rate_files_per_second: float = 0.0
    estimated_completion_time: Optional[datetime] = None
    memory_usage_mb: Optional[float] = None

    # Idempotency tracking
    content_added: int = 0
    content_skipped: int = 0
    processed_fingerprints: List[str] = field(default_factory=list)

    def get_progress_percent(self) -> float:
        """Get progress as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.files_processed / self.total_files) * 100

    def is_complete(self) -> bool:
        """Check if seeding is complete."""
        return self.status == SeedingStatus.COMPLETED

    def is_running(self) -> bool:
        """Check if seeding is currently running."""
        return self.status == SeedingStatus.RUNNING

    def estimate_time_remaining(self) -> Optional[int]:
        """Estimate seconds remaining based on current progress and processing rate."""
        if not self.started_at or self.files_processed == 0 or self.total_files == 0:
            return None

        # Calculate effective processing time (excluding paused time)
        now = datetime.now()
        effective_start = self.resumed_at if self.resumed_at else self.started_at

        if self.status == SeedingStatus.PAUSED and self.paused_at:
            # If currently paused, use paused time as end time
            elapsed = (self.paused_at - effective_start).total_seconds()
        else:
            elapsed = (now - effective_start).total_seconds()

        # Require a minimum elapsed window before estimating: a rate derived from a
        # near-zero elapsed time is meaningless and makes a just-started run report a
        # misleading ~0s remaining. Treat such fresh progress as "no estimate yet".
        if elapsed < 1.0 or self.files_processed == 0:
            return None

        # Use stored processing rate if available, otherwise calculate
        if self.processing_rate_files_per_second > 0:
            rate = self.processing_rate_files_per_second
        else:
            rate = self.files_processed / elapsed

        remaining_files = self.total_files - self.files_processed

        if rate > 0:
            estimated_seconds = int(remaining_files / rate)
            # Update estimated completion time
            if self.status == SeedingStatus.RUNNING:
                self.estimated_completion_time = now + timedelta(
                    seconds=estimated_seconds
                )
            return estimated_seconds
        return None

    def update_processing_rate(self) -> None:
        """Update the processing rate based on current progress."""
        if not self.started_at or self.files_processed == 0:
            self.processing_rate_files_per_second = 0.0
            return

        now = datetime.now()
        effective_start = self.resumed_at if self.resumed_at else self.started_at

        if self.status == SeedingStatus.PAUSED and self.paused_at:
            elapsed = (self.paused_at - effective_start).total_seconds()
        else:
            elapsed = (now - effective_start).total_seconds()

        if elapsed > 0:
            self.processing_rate_files_per_second = self.files_processed / elapsed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Convert datetime objects to ISO strings
        datetime_fields = [
            "started_at",
            "completed_at",
            "last_updated",
            "paused_at",
            "resumed_at",
            "estimated_completion_time",
        ]
        for field in datetime_fields:
            if result.get(field):
                result[field] = result[field].isoformat()
        result["status"] = self.status.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SeedingProgress":
        """Create from dictionary (JSON deserialization)."""
        # Convert ISO strings back to datetime objects
        datetime_fields = [
            "started_at",
            "completed_at",
            "last_updated",
            "paused_at",
            "resumed_at",
            "estimated_completion_time",
        ]
        for field in datetime_fields:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])

        # Convert status string back to enum
        if isinstance(data.get("status"), str):
            data["status"] = SeedingStatus(data["status"])

        # Handle missing fields for backward compatibility
        for field in [
            "session_id",
            "files_failed",
            "files_skipped",
            "processing_rate_files_per_second",
            "content_added",
            "content_skipped",
            "processed_fingerprints",
        ]:
            if field not in data:
                if field == "session_id":
                    data[field] = str(uuid.uuid4())
                elif field == "processed_fingerprints":
                    data[field] = []
                else:
                    data[field] = (
                        0
                        if "files_" in field or "rate" in field or "content_" in field
                        else None
                    )

        return cls(**data)


@dataclass
class SeedingFileStatus:
    """Enhanced status of individual file processing."""

    file_path: str
    status: FileProcessingStatus
    file_size_bytes: int = 0
    processed_at: Optional[datetime] = None
    processing_duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    items_processed: int = 0
    content_type: Optional[str] = None
    checksum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        if result.get("processed_at"):
            result["processed_at"] = result["processed_at"].isoformat()
        result["status"] = self.status.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SeedingFileStatus":
        """Create from dictionary (JSON deserialization)."""
        if data.get("processed_at"):
            data["processed_at"] = datetime.fromisoformat(data["processed_at"])

        # Convert status string back to enum
        if isinstance(data.get("status"), str):
            data["status"] = FileProcessingStatus(data["status"])

        # Handle missing fields for backward compatibility
        for field in ["file_size_bytes", "retry_count", "items_processed"]:
            if field not in data:
                data[field] = 0

        return cls(**data)

    def calculate_checksum(self) -> str:
        """Calculate and store file checksum for integrity verification."""
        import hashlib

        try:
            with open(self.file_path, "rb") as f:
                file_hash = hashlib.md5()
                for chunk in iter(lambda: f.read(4096), b""):
                    file_hash.update(chunk)
                self.checksum = file_hash.hexdigest()
                return self.checksum
        except Exception as e:
            logging.warning(f"Could not calculate checksum for {self.file_path}: {e}")
            return ""


class SeedingMetadata:
    """File-based metadata storage for seeding status."""

    def __init__(self, metadata_file: str = "seeding_status.json"):
        self.metadata_file = metadata_file

    async def save_progress(self, progress: SeedingProgress) -> None:
        """Save seeding progress to file."""
        try:
            progress.last_updated = datetime.now()
            data = progress.to_dict()

            with open(self.metadata_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving seeding progress: {e}")

    async def load_progress(self) -> Optional[SeedingProgress]:
        """Load seeding progress from file."""
        try:
            with open(self.metadata_file, "r") as f:
                data = json.load(f)
            return SeedingProgress.from_dict(data)
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error loading seeding progress: {e}")
            return None

    async def save_file_statuses(self, file_statuses: List[SeedingFileStatus]) -> None:
        """Save file processing statuses."""
        try:
            file_data = [fs.to_dict() for fs in file_statuses]
            file_status_path = self.metadata_file.replace(".json", "_files.json")

            with open(file_status_path, "w") as f:
                json.dump(file_data, f, indent=2)
        except Exception as e:
            print(f"Error saving file statuses: {e}")

    async def load_file_statuses(self) -> List[SeedingFileStatus]:
        """Load file processing statuses."""
        try:
            file_status_path = self.metadata_file.replace(".json", "_files.json")
            with open(file_status_path, "r") as f:
                data = json.load(f)
            return [SeedingFileStatus.from_dict(item) for item in data]
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"Error loading file statuses: {e}")
            return []

    async def clear_metadata(self) -> None:
        """Clear all metadata files."""
        try:
            import os

            if os.path.exists(self.metadata_file):
                os.remove(self.metadata_file)

            file_status_path = self.metadata_file.replace(".json", "_files.json")
            if os.path.exists(file_status_path):
                os.remove(file_status_path)
        except Exception as e:
            print(f"Error clearing metadata: {e}")
