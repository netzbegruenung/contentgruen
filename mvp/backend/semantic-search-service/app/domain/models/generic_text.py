from typing import Optional, List
from pydantic import BaseModel, field_validator, Field
import datetime
import uuid
import json
from domain.models.content_type import ContentType
from domain.models.model_utils import ModelValidator
from domain.models.base_content import (
    BaseContent,
    BaseContentDbEntry,
    BaseContentSearchResult,
)


class GenericTextReference(BaseModel):
    """
    Representing a link to a reference for generic text content

    Attributes:
    -----------
    reference_id: UUID
        Unique identifier for the reference
    created: datetime
        Timestamp the reference was linked to the generic text
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

    @field_validator("reference_id", mode="before")
    def parse_uuid(cls, value):
        return ModelValidator.validate_uuid(value)

    @field_validator("created", mode="before")
    def parse_datetime(cls, value):
        return ModelValidator.validate_datetime(value)


class GenericText(BaseContent):
    """
    GenericText model representing generic political content that doesn't fit into specific content types.

    This serves as a catch-all for valuable political content including speech excerpts,
    article quotes, study findings, poems, election program sections, and other useful content
    not yet categorized into specific types.

    The 'text' field inherited from BaseContent contains the actual content for semantic search.

    Attributes:
    -----------
    title: str
        Title of the generic text content
    references: List[GenericTextReference]
        List of references/sources for this content
    """

    content_type: ContentType = ContentType.GENERIC_TEXT

    title: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Title of the generic text content",
    )
    references: List[GenericTextReference] = []

    @field_validator("references", mode="before")
    def parse_references(cls, value):
        if isinstance(value, str):
            try:
                references_data = json.loads(value)
                if not isinstance(references_data, list):
                    raise ValueError("References should be a list")
                return [
                    GenericTextReference(**reference) for reference in references_data
                ]
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON format for references: {value}. Error: {e}"
                )
            except Exception as e:
                raise ValueError(f"Error validating references: {e}")
        return value


class GenericTextDbEntry(GenericText, BaseContentDbEntry):
    """
    Representing a generic text with additional input metadata for indexing

    Attributes:
    -----------
    references_count: int
        Count of references in the generic text
    usage_count: Optional[int]
        Number of times this generic text has been used (copied)
    """

    references_count: int = 0
    usage_count: Optional[int] = None


class GenericTextSearchResult(GenericTextDbEntry, BaseContentSearchResult):
    """
    Representing a generic text entry with score and additional result metadata
    """
