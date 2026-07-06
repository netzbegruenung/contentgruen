from pydantic import BaseModel
from typing import List

from domain.models.image import (
    Image,
    ImageDbEntry,
)


class AddImageRequest(BaseModel):
    image: Image


class ImageGetAllResponse(BaseModel):
    results_count: int
    results: List[ImageDbEntry]
    total_records_count: int


class SuggestCaptionRequest(BaseModel):
    image_url: str


class SuggestCaptionResponse(BaseModel):
    suggested_caption: str
