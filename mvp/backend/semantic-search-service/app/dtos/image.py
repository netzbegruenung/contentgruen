from pydantic import BaseModel
from typing import List, Literal, Optional
from uuid import UUID

from domain.models.image import (
    Image,
    ImageDbEntry,
)


class AddImageRequest(BaseModel):
    image: Image


class AddImageResponse(BaseModel):
    """Antwort auf addImage: die ID, ohne Bildunterschrift zusaetzlich der Status.

    status steht nur in der 202-Antwort; die Route laesst None-Felder weg, damit
    die 201-Antwort wie bisher nur die ID enthaelt.
    """

    id: UUID
    status: Optional[Literal["pending_description"]] = None


class ImageGetAllResponse(BaseModel):
    results_count: int
    results: List[ImageDbEntry]
    total_records_count: int


class SuggestCaptionRequest(BaseModel):
    image_url: str


class SuggestCaptionResponse(BaseModel):
    suggested_caption: str
