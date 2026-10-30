from typing import Optional
from pydantic import Field, field_validator

from domain.models.content_type import ContentType
from domain.models.base_content import (
    BaseContent,
    BaseContentDbEntry,
    BaseContentSearchResult,
)


class Image(BaseContent):
    """
    A captioned image captured as searchable political content.

    The 'text' field (inherited from BaseContent, overridden to Optional here) holds
    the Unterschrift used for semantic search. New images need one (AddImageRequest,
    ADR 0003); the field stays Optional so that entries without Unterschrift from
    before #281 (pending_description) still validate. Readers never see them
    (AUSGEBLENDET in content_status.py).

    Attributes:
    -----------
    title: str
        Short descriptive title for the image.
    image_url: str
        Publicly accessible URL of the image.
    text: Optional[str]
        Unterschrift, the embedded search text. None only for entries from before #281.
    description_model: Optional[str]
        Identifier of the AI model that generated 'text'. Only the former background
        worker set it; since #393 nothing suggests an Unterschrift, so nothing sets it.
    """

    content_type: ContentType = ContentType.IMAGE

    title: str = Field(..., min_length=3, max_length=200)
    image_url: str = Field(..., description="Publicly accessible URL of the image")
    text: Optional[str] = None  # overrides BaseContent's required str
    description_model: Optional[str] = None

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v: str) -> str:
        if not v.lower().startswith(("http://", "https://")):
            raise ValueError("image_url must be an http or https URL")
        return v


class ImageDbEntry(Image, BaseContentDbEntry):
    """Image with additional metadata for indexing."""

    # Wie bei Kommentar und Hintergrundinfo: die Suche traegt die Nutzung in jedes
    # Ergebnis ein (SearchOrchestrator.enrich_with_usage).
    usage_count: Optional[int] = None


class ImageSearchResult(ImageDbEntry, BaseContentSearchResult):
    """Image entry with score and additional result metadata."""
