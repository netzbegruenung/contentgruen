import datetime
from pydantic import BaseModel, ValidationError, field_validator, Field
from typing import List, Optional
import uuid
import json

from domain.models.content_type import ContentType
from domain.models.model_utils import ModelValidator
from domain.models.base_content import (
    BaseContent,
    BaseContentDbEntry,
    BaseContentSearchResult,
)


class CommentaryReference(BaseModel):
    """
    Representing a link to a reference for a commentary

    Attributes:
    -----------
    reference_id: UUID
        Unique identifier for the reference
    created: datetime
        Timestamp the reference was linked to the commentary
    description: Optional[str]
        Notiz zu dieser Quelle, die nur fuer diesen Beitrag gilt. Sie haengt
        bewusst an der Verknuepfung und nicht an der Referenz: dieselbe Quelle
        kann in einem anderen Beitrag eine andere Notiz tragen.
    reference_text: Optional[str]
        The actual reference URL (populated when fetching for display)
    reference_description: Optional[str]
        Wird beim Lesen befuellt: die Notiz dieses Beitrags, sonst der Text der
        Referenz.
    """

    reference_id: uuid.UUID
    created: datetime.datetime
    description: Optional[str] = None
    reference_text: Optional[str] = None
    reference_description: Optional[str] = None

    # Field validators to parse from JSON string to UUID and datetime objects

    @field_validator("reference_id", mode="before")
    def parse_uuid(cls, value):
        return ModelValidator.validate_uuid(value)

    @field_validator("created", mode="before")
    def parse_datetime(cls, value):
        return ModelValidator.validate_datetime(value)


class Commentary(BaseContent):
    """
    A commentary on something that can be used standalone but is especially intended to be used as a reply to a statement

    Attributes:
    -----------
    title: str
        Title of the commentary
    long_text: str
        Long text of the commentary, might be empty
    short_text: str
        Short text of the commentary, might be empty
    style: str
        The style of the commentary (e.g. empathisch, faktisch, persönlich, humorvoll, sarkastisch, brückenbauend)
    references: List[CommentaryReference]
        List of references for the commentary
    """

    content_type: ContentType = ContentType.COMMENTARY

    title: str = Field(
        ..., min_length=3, max_length=50, description="Title of the commentary"
    )
    long_text: Optional[str] = None
    short_text: Optional[str] = None
    style: Optional[str] = None
    references: List[CommentaryReference]

    @field_validator("references", mode="before")
    def parse_references(cls, value):
        if isinstance(value, str):
            try:
                # Deserialize the JSON string into a list of dicts
                references_data = json.loads(value)
                if not isinstance(references_data, list):
                    raise ValueError("References should be a list")

                # Convert each dict into a CommentaryReference object
                return [
                    CommentaryReference(**reference) for reference in references_data
                ]
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON format for references: {value}. Error: {e}"
                )
            except ValidationError as e:
                raise ValueError(f"Error validating references: {e}")
        return value


class CommentaryDbEntry(Commentary, BaseContentDbEntry):
    """
    Representing a commentary with additional metadata for indexing

    Attributes:
    -----------
    references_count: int
        Count of references in the commentary
    usage_count: Optional[int]
        Number of times this commentary has been used (copied)
    """

    references_count: int
    usage_count: Optional[int] = None


class CommentarySearchResult(CommentaryDbEntry, BaseContentSearchResult):
    """
    Representing a commentary entry with score and additional result metadata
    """
