from pydantic import BaseModel, field_validator
from typing import List
from uuid import UUID

from domain.models.image import (
    Image,
    ImageDbEntry,
)


class AddImageRequest(BaseModel):
    image: Image

    @field_validator("image")
    @classmethod
    def unterschrift_erforderlich(cls, image: Image) -> Image:
        # Ohne Unterschrift ist es kein Bild (GLOSSARY.md, ADR 0003).
        if not image.text or not image.text.strip():
            raise ValueError("Ein Bild braucht eine Unterschrift")
        return image


class AddImageResponse(BaseModel):
    """Antwort auf addImage: die ID des gespeicherten Bildes."""

    id: UUID


class ImageGetAllResponse(BaseModel):
    results_count: int
    results: List[ImageDbEntry]
    total_records_count: int


class SuggestCaptionRequest(BaseModel):
    image_url: str


class SuggestCaptionResponse(BaseModel):
    suggested_caption: str
