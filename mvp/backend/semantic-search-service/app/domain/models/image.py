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
    the caption used for semantic search. In Phase A the router enforces a non-empty
    caption before accepting the submission. In Phase B the field may be None on
    creation; the background worker fills it after calling the vision AI.

    Attributes:
    -----------
    title: str
        Short descriptive title for the image.
    image_url: str
        Publicly accessible URL of the image.
    text: Optional[str]
        Caption / AI-generated description used as the embedded search text.
        None until the background worker fills it (Phase B path only).
    description_model: Optional[str]
        Identifier of the AI model that generated 'text'; None for user-supplied captions.
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


class ImageSearchResult(ImageDbEntry, BaseContentSearchResult):
    """Image entry with score and additional result metadata."""
