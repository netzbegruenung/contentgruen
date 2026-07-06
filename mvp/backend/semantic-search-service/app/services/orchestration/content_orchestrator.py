import datetime
import hashlib
from typing import List, Optional, Callable, Dict, Any, Set
import os
import uuid

from core.config import Settings
from core.logging import get_logger
from services.content.commentary_service import CommentaryService
from services.content.reference_service import ReferenceService
from services.content.statement_service import StatementService
from services.content.generic_text_service import GenericTextService
from services.content.base_content_service import BaseContentService
from utils.data_utils import DataLoader, DataSource
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from repositories.aggregated.content_repository import (
    ContentRepository,
)
from repositories.usage_tracking_repository import get_usage_repository
from domain.models.commentary import Commentary, CommentaryReference
from domain.models.content_type import ContentType
from domain.models.statement import Statement, StatementReplysuggestion
from domain.models.reference import Reference
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin

logger = get_logger(__name__)


def get_content_fingerprint(title: str, text: str, content_type: str) -> str:
    """Generate unique fingerprint for seed content identification.

    Args:
        title: Content title
        text: Content text
        content_type: Content type (commentary, statement, etc.)

    Returns:
        32-character hash for unique identification
    """
    content = f"{title}|{text}|{content_type}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


class ProgressTracker:
    """Helper class to track progress across multiple processing phases."""

    def __init__(
        self,
        total_items: int,
        callback: Optional[Callable[[str, int, int], None]] = None,
    ):
        self.total_items = total_items
        self.current_progress = 0
        self.callback = callback

    def report_progress(self, item_name: str) -> None:
        """Report progress for a single item."""
        self.current_progress += 1
        if self.callback:
            self.callback(item_name, self.current_progress, self.total_items)


class DataProcessor:
    """Helper class for processing different types of initial data."""

    def __init__(self, orchestrator: "ContentOrchestrator"):
        self.orchestrator = orchestrator
        # Only initialize usage repository if not in test environment
        try:
            self.usage_repository = get_usage_repository()
        except Exception:
            # In tests or when DB is not available, set to None
            self.usage_repository = None

    async def process_reference(self, reference_data: Dict[str, Any]) -> uuid.UUID:
        """Process a single reference and return its ID."""
        reference = Reference(
            text=reference_data["text"],
            reference_string=reference_data["reference_string"],
        )

        # add_reference returns a tuple (reference_id, is_new, description)
        reference_id, _, _ = await self.orchestrator.reference_service.add_reference(
            reference,
            self.orchestrator.initial_data_author,
            status=ContentStatus.RELEASED_INTERNAL,
            origin=ContentOrigin.INITIAL_DATA,
        )
        return reference_id

    async def process_references_batch(
        self, references_data: List[Dict[str, Any]]
    ) -> List[uuid.UUID]:
        """
        Process multiple references in batch for better performance.
        Returns a list of reference IDs in the same order as input.
        """
        reference_ids = []

        # Check for existing references first to avoid duplicate processing
        reference_cache = {}

        for reference_data in references_data:
            ref_string = reference_data["reference_string"]

            # Check if we've already processed this reference in this batch
            if ref_string in reference_cache:
                reference_ids.append(reference_cache[ref_string])
                continue

            # Check if reference already exists in the database
            existing = await self.orchestrator.reference_service.find_exact_match(
                ref_string
            )
            if existing:
                reference_cache[ref_string] = existing.id
                reference_ids.append(existing.id)
                # Increment usage count for existing reference
                await self.orchestrator.reference_service._increment_usage_count(
                    existing.id
                )
            else:
                # Process new reference
                reference_id = await self.process_reference(reference_data)
                reference_cache[ref_string] = reference_id
                reference_ids.append(reference_id)

        return reference_ids

    async def create_commentary_with_references(
        self, commentary_data: Dict[str, Any]
    ) -> Optional[uuid.UUID]:
        """Create a commentary with its references and return the commentary ID, or None if skipped."""
        title = commentary_data["title"]
        text = commentary_data["text"]
        metadata = commentary_data.get("metadata", {})

        # Check if this commentary has already been processed
        if self.orchestrator.is_content_processed(title, text, "commentary"):
            self.orchestrator.mark_content_processed(
                title, text, "commentary", "skipped"
            )
            return None

        commentary_references = []

        for reference_data in commentary_data.get("references", []):
            reference_id = await self.process_reference(reference_data)
            commentary_references.append(
                CommentaryReference(
                    reference_id=reference_id,
                    created=datetime.datetime.now(),
                )
            )

        commentary = Commentary(
            text=text,
            title=title,
            long_text=commentary_data.get("long_text", None),
            short_text=commentary_data.get("short_text", None),
            style=commentary_data.get("style", None),
            references=commentary_references,
        )

        # Parse created_at from metadata if available
        created_at = None
        if metadata and "created_at" in metadata:
            try:
                created_at = datetime.datetime.fromisoformat(metadata["created_at"])
            except (ValueError, TypeError):
                logger.warning(
                    f"Could not parse created_at from metadata: {metadata.get('created_at')}"
                )

        result = await self.orchestrator.commentary_service.add_commentary(
            commentary,
            self.orchestrator.initial_data_author,
            status=ContentStatus.RELEASED_INTERNAL,
            origin=ContentOrigin.INITIAL_DATA,
            created_at=created_at,
        )

        # Mark as processed
        self.orchestrator.mark_content_processed(title, text, "commentary", "added")

        # Initialize usage tracking with metadata if provided
        if self.usage_repository and metadata and result[1]:
            usage_count = metadata.get("usage_count", 0)
            if usage_count > 0:
                try:
                    self.usage_repository.initialize_usage_data(result[1], usage_count)
                    logger.info(
                        f"Initialized usage data for commentary {result[1]} with count {usage_count}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not initialize usage data for commentary {result[1]}: {e}"
                    )

        return result[1]

    async def create_generictext_with_references(
        self, generictext_data: Dict[str, Any]
    ) -> Optional[uuid.UUID]:
        """Create a generic text with its references and return the generic text ID, or None if skipped."""
        from domain.models.generic_text import GenericText, GenericTextReference

        title = generictext_data["title"]
        text = generictext_data["text"]
        metadata = generictext_data.get("metadata", {})

        # Check if this generic text has already been processed
        if self.orchestrator.is_content_processed(title, text, "generic_text"):
            self.orchestrator.mark_content_processed(
                title, text, "generic_text", "skipped"
            )
            return None

        generictext_references = []

        for reference_data in generictext_data.get("references", []):
            reference_id = await self.process_reference(reference_data)
            generictext_references.append(
                GenericTextReference(
                    reference_id=reference_id,
                    created=datetime.datetime.now(),
                )
            )

        generictext = GenericText(
            text=text,
            title=title,
            references=generictext_references,
        )

        # Parse created_at from metadata if available
        created_at = None
        if metadata and "created_at" in metadata:
            try:
                created_at = datetime.datetime.fromisoformat(metadata["created_at"])
            except (ValueError, TypeError):
                logger.warning(
                    f"Could not parse created_at from metadata: {metadata.get('created_at')}"
                )

        result = await self.orchestrator.generic_text_service.add_generic_text(
            generictext,
            self.orchestrator.initial_data_author,
            status=ContentStatus.RELEASED_INTERNAL,
            origin=ContentOrigin.INITIAL_DATA,
            created_at=created_at,
        )

        # Mark as processed
        self.orchestrator.mark_content_processed(title, text, "generic_text", "added")

        # Initialize usage tracking with metadata if provided
        if self.usage_repository and metadata and result[1]:
            usage_count = metadata.get("usage_count", 0)
            if usage_count > 0:
                try:
                    self.usage_repository.initialize_usage_data(result[1], usage_count)
                    logger.info(
                        f"Initialized usage data for generic_text {result[1]} with count {usage_count}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not initialize usage data for generic_text {result[1]}: {e}"
                    )

        return result[1]  # Return the UUID from the tuple

    async def create_statement_with_replies(
        self,
        statement_text: str,
        reply_ids: List[uuid.UUID],
        content_type: ContentType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create a statement with reply suggestions."""
        statement_replysuggestions = [
            StatementReplysuggestion(
                id=reply_id,
                content_type=content_type,
                relevance=0.7,
                created=datetime.datetime.now(),
                updated=datetime.datetime.now(),
                number_of_usages=0,
            )
            for reply_id in reply_ids
        ]

        statement = Statement(
            text=statement_text,
            replysuggestions=statement_replysuggestions,
        )

        # Parse created_at from metadata if available
        created_at = None
        if metadata and "created_at" in metadata:
            try:
                created_at = datetime.datetime.fromisoformat(metadata["created_at"])
            except (ValueError, TypeError):
                logger.warning(
                    f"Could not parse created_at from metadata: {metadata.get('created_at')}"
                )

        result = await self.orchestrator.statement_service.add_statement(
            statement,
            self.orchestrator.initial_data_author,
            status=ContentStatus.RELEASED_INTERNAL,
            origin=ContentOrigin.INITIAL_DATA,
            created_at=created_at,
        )

        # Initialize usage tracking with metadata if provided
        if self.usage_repository and metadata and result and len(result) > 1:
            statement_id = result[1]
            usage_count = metadata.get("usage_count", 0)
            if usage_count > 0:
                try:
                    self.usage_repository.initialize_usage_data(
                        statement_id, usage_count
                    )
                    logger.info(
                        f"Initialized usage data for statement {statement_id} with count {usage_count}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not initialize usage data for statement {statement_id}: {e}"
                    )


class ContentOrchestrator:
    """
    Class to orchestrate operations spanning multiple content services.
    """

    def __init__(
        self,
        settings: Settings,
        commentary_service: CommentaryService,
        reference_service: ReferenceService,
        statement_service: StatementService,
        generic_text_service: GenericTextService,
    ):
        self.settings = settings
        self.initial_data_path = settings.data_path
        self.commentary_service = commentary_service
        self.reference_service = reference_service
        self.statement_service = statement_service
        self.generic_text_service = generic_text_service
        self.initial_data_author = settings.initial_data_author

        self.services: List[BaseContentService] = [
            self.commentary_service,
            self.reference_service,
            self.statement_service,
            self.generic_text_service,
        ]

        self.data_processor = DataProcessor(self)
        self._stop_callback: Optional[Callable[[], bool]] = None

        # Track processed content fingerprints for idempotent seeding
        self.processed_fingerprints: Set[str] = set()

        # Seeding operation counters
        self.seeding_stats = {"added": 0, "skipped": 0}

    async def initialize_repositories(
        self, progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> None:
        """
        Initialize all repositories with initial data from JSON files.
        """
        # Phase 1: Individual repository initialization
        should_load_shared = await self._initialize_individual_repositories()

        # Phase 2: Shared data initialization with progress tracking
        if should_load_shared:
            print(
                "Loaded initial data from JSON files for at least one repository, executing shared initialization logic"
            )
            await self._initialize_shared_data_with_progress(progress_callback)

    async def _initialize_individual_repositories(self) -> bool:
        """Initialize individual repositories and return whether any loaded from JSON."""
        # Initialize aggregated content repository
        repository_factory = QdrantRepositoryFactory()
        content_repository = repository_factory.create_content_repository(self.settings)
        content_repository_result = await content_repository.initialize_index()

        # Use asyncio.gather for parallel initialization
        import asyncio

        service_results = await asyncio.gather(
            *[service.initialize_repository() for service in self.services]
        )

        return (
            any(result is DataSource.JSON for result in service_results)
            or content_repository_result is DataSource.JSON
        )

    def _calculate_total_work_items(self) -> int:
        """Calculate total work items for progress tracking."""
        total_items = 0

        # Count commentaries items
        commentaries_data = self._load_commentaries_data()
        if commentaries_data:
            total_items += len(commentaries_data)

        # Count generictexts items
        generictexts_data = self._load_generictexts_data()
        if generictexts_data:
            total_items += len(generictexts_data)

        return total_items

    async def _initialize_shared_data_with_progress(
        self, progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> None:
        """Initialize shared data with proper progress tracking."""
        total_work_items = self._calculate_total_work_items()
        print(f"Total work items to process: {total_work_items}")

        progress_tracker = ProgressTracker(total_work_items, progress_callback)

        # Process all datasets with unified progress tracking
        await self._process_commentaries_data(progress_tracker)
        await self._process_generictexts_data(progress_tracker)

    def _load_commentaries_data(self) -> List[Dict[str, Any]]:
        """Load commentaries data from JSON files."""
        data_path = os.path.join(self.initial_data_path, "statements_with_commentaries")

        if not os.path.exists(data_path):
            return []

        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string"},
                    "commentaries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "title": {"type": "string"},
                                "long_text": {"type": "string"},
                                "short_text": {"type": "string"},
                                "style": {"type": "string"},
                                "references": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "text": {"type": "string"},
                                            "reference_string": {"type": "string"},
                                        },
                                        "required": ["text", "reference_string"],
                                        "additionalProperties": False,
                                    },
                                },
                                "metadata": {
                                    "type": "object",
                                    "properties": {
                                        "usage_count": {"type": "integer"},
                                        "created_at": {"type": "string"},
                                    },
                                    "additionalProperties": False,
                                },
                            },
                            "required": ["text", "title"],
                            "additionalProperties": True,
                        },
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "usage_count": {"type": "integer"},
                            "created_at": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                },
                "required": ["statement", "commentaries"],
                "additionalProperties": True,
            },
        }

        return DataLoader.load_json_data_files(data_path, schema)

    def _load_generictexts_data(self) -> List[Dict[str, Any]]:
        """Load generictexts data from JSON files."""
        data_path = os.path.join(self.initial_data_path, "statements_with_generictexts")

        if not os.path.exists(data_path):
            return []

        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string"},
                    "generic_texts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "title": {"type": "string"},
                                "references": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "text": {"type": "string"},
                                            "reference_string": {"type": "string"},
                                        },
                                        "required": ["text", "reference_string"],
                                        "additionalProperties": False,
                                    },
                                },
                                "metadata": {
                                    "type": "object",
                                    "properties": {
                                        "usage_count": {"type": "integer"},
                                        "created_at": {"type": "string"},
                                    },
                                    "additionalProperties": False,
                                },
                            },
                            "required": ["text", "title"],
                            "additionalProperties": True,
                        },
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "usage_count": {"type": "integer"},
                            "created_at": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                },
                "required": ["statement", "generic_texts"],
                "additionalProperties": True,
            },
        }

        return DataLoader.load_json_data_files(data_path, schema)

    async def _process_commentaries_data(
        self, progress_tracker: ProgressTracker
    ) -> None:
        """Process statements with commentaries."""
        print("=== Initializing shared data: statements with commentaries ===")

        data = self._load_commentaries_data()
        if not data:
            print("No initial data found for statements with commentaries")
            return

        for item_index, item in enumerate(data):
            if self._should_stop_processing():
                print(
                    f"Stop requested during commentaries processing at item {item_index + 1}/{len(data)}"
                )
                return

            await self._process_single_commentary_item(item)
            progress_tracker.report_progress(
                f"statement_with_commentaries_{item_index}"
            )

        self._save_commentary_services()
        self._refresh_topics()

    async def _process_generictexts_data(
        self, progress_tracker: ProgressTracker
    ) -> None:
        """Process statements with generic texts."""
        print("=== Initializing shared data: statements with generic texts ===")

        data = self._load_generictexts_data()
        if not data:
            print("No initial data found for statements with generic texts")
            return

        for item_index, item in enumerate(data):
            if self._should_stop_processing():
                print(
                    f"Stop requested during generic texts processing at item {item_index + 1}/{len(data)}"
                )
                return

            await self._process_single_generictext_item(item)
            progress_tracker.report_progress(
                f"statement_with_generictexts_{item_index}"
            )

        self._save_generictext_services()
        self._refresh_topics()

    async def _process_single_commentary_item(self, item: Dict[str, Any]) -> None:
        """Process a single item from commentaries data."""
        statement_text = item["statement"]
        commentaries = item["commentaries"]
        statement_metadata = item.get("metadata", {})

        reply_ids = []
        for commentary_data in commentaries:
            commentary_id = await self.data_processor.create_commentary_with_references(
                commentary_data
            )
            # Only add to reply_ids if commentary was actually created (not skipped)
            if commentary_id is not None:
                reply_ids.append(commentary_id)

        # Only create statement if we have at least one reply
        if reply_ids:
            await self.data_processor.create_statement_with_replies(
                statement_text, reply_ids, ContentType.COMMENTARY, statement_metadata
            )

    async def _process_single_generictext_item(self, item: Dict[str, Any]) -> None:
        """Process a single item from generic texts data."""
        statement_text = item["statement"]
        generic_texts = item["generic_texts"]
        statement_metadata = item.get("metadata", {})

        reply_ids = []
        for generictext_data in generic_texts:
            generictext_id = (
                await self.data_processor.create_generictext_with_references(
                    generictext_data
                )
            )
            # Only add to reply_ids if generic text was actually created (not skipped)
            if generictext_id is not None:
                reply_ids.append(generictext_id)

        # Only create statement if we have at least one reply
        if reply_ids:
            await self.data_processor.create_statement_with_replies(
                statement_text, reply_ids, ContentType.GENERIC_TEXT, statement_metadata
            )

    def _should_stop_processing(self) -> bool:
        """Check if processing should be stopped."""
        return (
            hasattr(self, "_stop_callback")
            and self._stop_callback
            and self._stop_callback()
        )

    def _save_commentary_services(self) -> None:
        """Save services after processing commentaries."""
        self.commentary_service.save()
        self.reference_service.save()
        self.statement_service.save()

    def _save_generictext_services(self) -> None:
        """Save services after processing generic texts."""
        self.generic_text_service.save()
        self.reference_service.save()
        self.statement_service.save()

    def _refresh_topics(self) -> None:
        """Refresh topics for repositories that support it."""
        # Currently only statement service supports topics
        # Other services can be added here when topic support is implemented
        try:
            self.statement_service.refresh_topics()
            print("Successfully refreshed topics for statement service")
        except Exception as e:
            print(f"Warning: Could not refresh topics for statement service: {e}")

    def load_processed_fingerprints(self, fingerprints: Set[str]) -> None:
        """Load previously processed content fingerprints for idempotent seeding."""
        self.processed_fingerprints = fingerprints.copy()
        logger.info(
            f"Loaded {len(self.processed_fingerprints)} processed content fingerprints"
        )

    def is_content_processed(self, title: str, text: str, content_type: str) -> bool:
        """Check if content has already been processed based on fingerprint."""
        fingerprint = get_content_fingerprint(title, text, content_type)
        return fingerprint in self.processed_fingerprints

    def mark_content_processed(
        self, title: str, text: str, content_type: str, operation: str = "added"
    ) -> str:
        """Mark content as processed and update statistics."""
        fingerprint = get_content_fingerprint(title, text, content_type)
        self.processed_fingerprints.add(fingerprint)

        # Update statistics
        if operation in self.seeding_stats:
            self.seeding_stats[operation] += 1

        logger.info(
            f'Seeding: {operation.title()} {content_type}: "{title}" (fingerprint: {fingerprint})'
        )
        return fingerprint

    def get_seeding_summary(self) -> str:
        """Get a summary of seeding operations."""
        return (
            f"Seeding complete - {self.seeding_stats['added']} added, "
            f"{self.seeding_stats['skipped']} skipped"
        )

    def reset_seeding_stats(self) -> None:
        """Reset seeding statistics counters."""
        self.seeding_stats = {"added": 0, "skipped": 0}
