from pydantic import BaseModel, field_validator
from typing import List
from uuid import UUID

from domain.cc0_hinweis import Cc0Wortlaut
from domain.models.image import Image
from dtos.beitrag import BeitragResponse


class AddImageRequest(BaseModel):
    image: Image
    # Kennung des CC0-Hinweises, den die Person beim Speichern gesehen hat (#431,
    # domain/cc0_hinweis.py).
    cc0_wortlaut: Cc0Wortlaut = None

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


class BildResponse(BeitragResponse):
    """
    Ein Bild, wie Suche, getById und getAll es ausliefern (#311, #333).

    Die Auswahl aus BeitragResponse plus die Bildadresse; keine Bearbeitungshistorie
    (last_modified*, authors, edit_history) und keine Felder der Moderation und
    Dublettenpruefung. Wer hier ein Feld ergaenzt, entscheidet, dass es nach aussen
    geht.

    Gesperrte und geloeschte Bilder liefern getById und getAll nicht aus (das
    Repository blendet sie aus, #300); der Zustand ist hier also immer "sichtbar".
    Er bleibt trotzdem, weil BeitragResponse ihn fuer alle Beitragstypen fuehrt und
    die Karte jeden Typ gleich liest.
    """

    title: str
    image_url: str


class ImageGetAllResponse(BaseModel):
    results_count: int
    results: List[BildResponse]
    total_records_count: int
