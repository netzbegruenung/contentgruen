import datetime
from pydantic import BaseModel, field_validator
from typing import List, Optional
from uuid import UUID

from domain.models.content_status import ContentStatus
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

    Der Zustand bleibt, weil getById und getAll bisher nicht nach ihm filtern und
    gesperrte oder geloeschte Bilder sonst nicht von sichtbaren zu unterscheiden
    waeren. Das ist eine bekannte Luecke: Laut Glossar findet ein gesperrtes Bild
    nur ein Admin, ein geloeschtes niemand. Das Filtern gehoert zu #300.
    """

    id: UUID
    content_type: ContentType
    title: str
    image_url: str
    # Unterschrift; None nur bei Bildern von vor #281.
    text: Optional[str] = None
    created: datetime.datetime
    status: ContentStatus
    # Anzeigename zu original_author; nur fuer angemeldete Aufrufer, sonst None.
    autor_name: Optional[str] = None

    @classmethod
    def aus_bild(cls, bild: ImageDbEntry, autor_name: Optional[str]) -> "BildResponse":
        # Uebernimmt genau die Felder dieser Klasse, alles andere bleibt zurueck.
        return cls.model_validate(bild, from_attributes=True).model_copy(
            update={"autor_name": autor_name}
        )


class ImageGetAllResponse(BaseModel):
    results_count: int
    results: List[BildResponse]
    total_records_count: int


class SuggestCaptionRequest(BaseModel):
    image_url: str


class SuggestCaptionResponse(BaseModel):
    suggested_caption: str
