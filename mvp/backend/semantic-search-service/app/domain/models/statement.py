import datetime
from pydantic import BaseModel, ValidationError, field_validator
from typing import List
import json
import uuid

from domain.models.content_type import ContentType
from domain.models.model_utils import ModelValidator
from domain.models.base_content import (
    BaseContent,
    BaseContentDbEntry,
    BaseContentSearchResult,
)


class StatementReplysuggestion(BaseModel):
    """
    Reply suggestion model representing a link from a statement to content that can be used as a reply to a statement

    Attributes:
    -----------
    id: UUID
        Unique identifier for the reply suggestion
    content_type: ContentType
        Content type of the reply suggestion
    relevance: float
        Relevance of the reply suggestion to the statement
    created: datetime
        Timestamp the reply suggestion was created
    updated: datetime
        Timestamp the reply suggestion was last modified
    number_of_usages: int
        Number of times the reply suggestion has been used as a reply to a statement
    """

    id: uuid.UUID
    content_type: ContentType
    relevance: float
    created: datetime.datetime
    updated: datetime.datetime
    number_of_usages: int

    @field_validator("id", mode="before")
    def parse_uuid(cls, value):
        return ModelValidator.validate_uuid(value)

    @field_validator("content_type", mode="before")
    def parse_content_type(cls, value):
        try:
            if isinstance(value, str):
                return ContentType(value)
            return value
        except ValueError as e:
            raise ValueError(
                f"Invalid content type for replysuggestion content_type: {value}. Error: {e}"
            )

    @field_validator("created", "updated", mode="before")
    def parse_datetime(cls, value):
        return ModelValidator.validate_datetime(value)


class Statement(BaseContent):
    """
    Statement model representing a generic statement with a list of reply suggestions

    Attributes:
    -----------
    replysuggestions: List[StatementReplysuggestion]
        List of reply suggestions for the statement
    """

    content_type: ContentType = ContentType.STATEMENT

    replysuggestions: List[StatementReplysuggestion]

    @field_validator("replysuggestions", mode="before")
    def parse_replysuggestions(cls, value):
        if isinstance(value, str):
            try:
                # Deserialize the JSON string into a list of dicts
                suggestions_data = json.loads(value)
                if not isinstance(suggestions_data, list):
                    raise ValueError("replysuggestions should be a list")

                # Convert each dict into a StatementReplysuggestion object
                return [
                    StatementReplysuggestion(**suggestion)
                    for suggestion in suggestions_data
                ]
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON format for replysuggestions: {value}. Error: {e}"
                )
            except ValidationError as e:
                raise ValueError(f"Error validating replysuggestions: {e}")
        return value


class StatementDbEntry(Statement, BaseContentDbEntry):
    """
    StatementInput model representing a statement with additional properties to insert it into the statement_index

    Attributes:
    -----------
    replysuggestions_count: int
        Number of reply suggestions for the statement
    """

    replysuggestions_count: int


class StatementSearchResult(StatementDbEntry, BaseContentSearchResult):
    """
    Representing a statement with score and additional result metadata
    """
