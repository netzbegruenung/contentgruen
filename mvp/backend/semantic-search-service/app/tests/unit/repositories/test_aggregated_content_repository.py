from typing import List
import datetime
import uuid

from core.config import Settings
from repositories.implementations.qdrant.base_repository import QdrantBaseRepository
from domain.models.content import (
    Content,
    ContentDbEntry,
    ContentSearchResult,
)
from utils.data_utils import DataLoader, DataSource
from domain.models.author_entry import AuthorEntry
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin


class TestContentRepository(QdrantBaseRepository):
    def __init__(self, settings: Settings):
        """
        Initialize the TestRepository with the provided Settings instance.
        Uses SharedEmbeddingsManager for unified storage.

        The TestContentRepository is a test repository that behaves like the aggregated ContentRepository.
        It uses content_type = "test" for logical separation.

        Args:
        - settings: The Settings instance to be used by the TestRepository.
        """
        index_name = "test_index"
        content_type = "test"  # Separate content_type for test data

        super().__init__(
            index_name,
            content_type,
            settings,
            ContentDbEntry,
            ContentSearchResult,
        )

    # TODO: Wrap test content repository in a specific aggregated service class?
    def initialize_index(self) -> DataSource:
        """
        Initialize the repository data.

        This method is called by the ContentOrchestrator to initialize the repository data.
        It checks if there's any test content in the shared repository.
        """
        print(f"=== Initializing {self.__class__.__name__} ===")

        if self.has_content():
            print(f"Initialized {self.__class__.__name__} - found existing content")
            return DataSource.STORAGE
        else:
            print(f"Executing initial data load from JSON files")
            self.initialize_with_initial_data()
            return DataSource.JSON

    def initialize_with_initial_data(self):
        """
        Initialize the TestContentRepository with initial data.
        """
        # Define JSON schema for initial load data
        content_data_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "content_type": {"type": "string"},
                },
                "required": ["text", "content_type"],
                "additionalProperties": False,
            },
        }

        # Load initial data from JSON files
        initial_test_content_data = DataLoader.load_json_data_files(
            self.initial_data_path, content_data_schema
        )

        # Create uuids for content items without id
        for item in initial_test_content_data:
            if "id" not in item:
                item["id"] = str(uuid.uuid4())

        # Parse initial test data into Content objects
        initial_test_content = [
            Content.model_validate(item) for item in initial_test_content_data
        ]

        # Create ContentInput objects from the initial test content data
        now = datetime.datetime.now()
        initial_test_content_inputs = [
            ContentDbEntry(
                text=content.text,
                id=uuid.uuid4(),
                created=now,
                last_modified=now,
                original_author=self.initial_data_author,
                last_modified_by=self.initial_data_author,
                authors=[AuthorEntry(name=self.initial_data_author)],
                edit_history=[],
                content_type=content.content_type,
                status=ContentStatus.RELEASED_INTERNAL,
                origin=ContentOrigin.INITIAL_DATA,
            )
            for content in initial_test_content
        ]

        # Add the initial test content data to the repository
        for item in initial_test_content_inputs:
            self.upsert(item.id, item)

        print(
            f"Executed initial load of data into {self.repository_name}, number of items:",
            len(initial_test_content_inputs),
        )
        # Note: Data is automatically persisted to PostgreSQL via SharedEmbeddingsManager

    def search(self, query_text: str, limit: int = 10) -> List[ContentSearchResult]:
        return super().search(query_text, limit)
