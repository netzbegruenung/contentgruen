import datetime
import json
from typing import List, Optional
import uuid
from jsonschema import ValidationError
from pydantic import BaseModel, field_validator

from domain.models.author_entry import AuthorEntry
from domain.models.edit_entry import EditEntry
from domain.models.model_utils import ModelValidator
from domain.models.content_type import ContentType
from domain.models.content_status import ContentStatus
from domain.models.content_visibility import ContentVisibility
from domain.models.content_origin import ContentOrigin


class BaseContent(BaseModel):
    """
    Base model for all content types.

    Attributes:
    -----------
    text: str
        Text of the content that is used for indexing and semantic search.
    content_type: ContentType
        Content type of the content.
    """

    text: str
    content_type: ContentType

    @field_validator("content_type", mode="before")
    def parse_content_type(cls, value):
        try:
            if isinstance(value, str):
                return ContentType(value)
            return value
        except ValueError as e:
            raise ValueError(f"Invalid content type: {value}. Error: {e}")


class BaseContentDbEntry(BaseContent):
    """
    Base model for all content entry items, including common metadata attached with every content item in the database.

    Attributes:
    -----------
    id: uuid.UUID
        Unique identifier for the input.
    created: datetime
        Timestamp the input was created.
    last_modified: datetime
        Timestamp the input was last modified.
    original_author: str
        Name or identifier of the original author.
    last_modified_by: str
        Name or identifier of the last editor.
    authors: List[AuthorEntry]
        Unique set of authors.
    edit_history: List[EditEntry]
        Detailed edit tracking.
    status: ContentStatus
        Current status of the content (e.g., "draft", "flagged", "approved").
    origin: ContentOrigin
        Origin of the content (e.g., "initial_data", "manually_created", "ai-generated").
    most_similar_similarity_score: Optional[float]
        Semantic similarity score compared to existing content.
    most_similar_content_id: Optional[uuid.UUID]
        ID of the most similar content item.
    report_count: int
        Number of reports received for this content.
    is_archived: bool
        Whether the content is archived.
    report_flagged: bool
        Whether the content has been flagged due to user reports.
    rejection_reason: Optional[str]
        Reason for rejection if the content was rejected.
    block_reason: Optional[str]
        Reason for blocking if the content was blocked.
    visibility: str
        Visibility of the content (e.g., "hidden", "restricted", "visible").
    """

    id: uuid.UUID
    created: datetime.datetime
    last_modified: datetime.datetime
    original_author: str
    last_modified_by: str
    authors: List[AuthorEntry] = []
    edit_history: List[EditEntry] = []
    status: ContentStatus
    origin: ContentOrigin
    most_similar_similarity_score: Optional[float] = None
    most_similar_content_id: Optional[uuid.UUID] = None
    report_count: int = 0
    is_archived: bool = False
    report_flagged: bool = False
    rejection_reason: Optional[str] = None
    block_reason: Optional[str] = None
    visibility: ContentVisibility = ContentVisibility.INTERNAL

    @field_validator("id", mode="before")
    def parse_uuid(cls, value):
        return ModelValidator.validate_uuid(value)

    @field_validator("created", "last_modified", mode="before")
    def parse_datetime(cls, value):
        return ModelValidator.validate_datetime(value)

    @field_validator("authors", mode="before")
    def parse_authors(cls, value):
        """
        Ensures 'authors' is a list, deserializing JSON strings if necessary.
        """
        if isinstance(value, str):
            try:
                # Deserialize the JSON string into a list of dicts
                authors_data = json.loads(value)
                if not isinstance(authors_data, list):
                    raise ValueError("authors should be a list")

                # Convert each dict into an AuthorEntry object
                return [AuthorEntry(**author) for author in authors_data]
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON format for authors: {value}. Error: {e}"
                )
            except ValidationError as e:
                raise ValueError(f"Error validating authors: {e}")
        return value

    @field_validator("edit_history", mode="before")
    def parse_edit_history(cls, value):
        """
        Ensures 'edit_history' is a list, deserializing JSON strings if necessary.
        """
        if isinstance(value, str):
            try:
                # Deserialize the JSON string into a list of dicts
                edit_history_data = json.loads(value)
                if not isinstance(edit_history_data, list):
                    raise ValueError("edit_history should be a list")

                # Convert each dict into an EditEntry object
                return [EditEntry(**edit_entry) for edit_entry in edit_history_data]
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON format for edit_history: {value}. Error: {e}"
                )
            except ValidationError as e:
                raise ValueError(f"Error validating edit_history: {e}")
        return value


class BaseContentSearchResult(BaseContentDbEntry):
    """
    Base model for scored content result items.

    Attributes:
    -----------
    score: float
        Similarity score of the content item.
    """

    score: float = 0.0
