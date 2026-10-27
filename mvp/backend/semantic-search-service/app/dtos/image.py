import datetime
from pydantic import BaseModel, field_validator
from typing import List, Optional
from uuid import UUID

from domain.models.content_type import ContentType
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


class BildResponse(BaseModel):
    """
    Ein Bild, wie getById und getAll es ausliefern (#311).

    Bewusst eine Auswahl aus ImageDbEntry: der Anzeigename statt der Kennung, keine
    Bearbeitungshistorie (last_modified*, authors, edit_history) und keine Felder der
    Moderation und Dublettenpruefung. Wer hier ein Feld ergaenzt, entscheidet, dass
    es nach aussen geht.
    """

    id: UUID
    content_type: ContentType
    title: str
    image_url: str
    # Unterschrift; None nur bei Bildern von vor #281.
    text: Optional[str] = None
    created: datetime.datetime
    # Anzeigename zu original_author; nur fuer angemeldete Aufrufer, sonst None.
    autor_name: Optional[str] = None

    @classmethod
    def aus_bild(cls, bild: ImageDbEntry, autor_name: Optional[str]) -> "BildResponse":
        return cls(
            id=bild.id,
            content_type=bild.content_type,
            title=bild.title,
            image_url=bild.image_url,
            text=bild.text,
            created=bild.created,
            autor_name=autor_name,
        )


class ImageGetAllResponse(BaseModel):
    results_count: int
    results: List[BildResponse]
    total_records_count: int


class SuggestCaptionRequest(BaseModel):
    image_url: str


class SuggestCaptionResponse(BaseModel):
    suggested_caption: str
