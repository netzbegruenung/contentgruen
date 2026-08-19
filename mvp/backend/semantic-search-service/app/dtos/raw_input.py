"""
DTOs fuer den Fangkorb (Rohinput).

Die einzige inhaltliche Pflicht ist, dass ueberhaupt etwas dasteht. Kein Titel,
keine Kategorie, kein Zieltyp - all das waere schon Destillieren und gehoert in
die spaetere Verarbeitung, nicht in den Einwurf.
"""

import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from domain.models.raw_input import RawInputStatus
from utils.url_validator import validate_url_security


def _normalisieren(wert: Optional[str]) -> Optional[str]:
    """Leerraum abschneiden; aus einem leeren Feld wird None, nicht ""."""
    if wert is None:
        return None
    bereinigt = wert.strip()
    return bereinigt or None


def _url_pruefen(url: Optional[str], feldname: str) -> Optional[str]:
    """http/https erzwingen und die Sicherheitspruefung anwenden."""
    if url is None:
        return None
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError(f"{feldname} muss mit http:// oder https:// beginnen")
    ist_gueltig, fehler = validate_url_security(url)
    if not ist_gueltig:
        raise ValueError(f"{feldname}: {fehler}")
    return url


###   Requests   ###


class AddRawInputRequest(BaseModel):
    """
    Ein Einwurf. Mindestens eines von ``content``, ``url``, ``image_url``.

    ``image_url`` verweist auf ein bereits im Netz liegendes Bild - einen
    Datei-Upload gibt es im gesamten Stack nicht (siehe docs/ROHINPUT.md).
    """

    content: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Freitext: der eine Satz oder eine Notiz zum Link",
    )
    url: Optional[str] = Field(
        default=None, max_length=2000, description="Link auf den Beitrag"
    )
    image_url: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="URL eines bereits erreichbaren Bildes",
    )

    @field_validator("content", "url", "image_url", mode="before")
    @classmethod
    def leerraum_abschneiden(cls, value):
        return _normalisieren(value) if isinstance(value, str) else value

    @field_validator("url")
    @classmethod
    def url_pruefen(cls, value):
        return _url_pruefen(value, "url")

    @field_validator("image_url")
    @classmethod
    def bild_url_pruefen(cls, value):
        return _url_pruefen(value, "image_url")

    @model_validator(mode="after")
    def mindestens_ein_feld(self):
        if not any([self.content, self.url, self.image_url]):
            raise ValueError(
                "Mindestens eines von content, url oder image_url muss gefuellt sein"
            )
        return self


###   Responses   ###


class RawInputResponse(BaseModel):
    """Ein Einwurf, wie ihn der Fangkorb ausliefert."""

    id: str
    content: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    submitted_by: Optional[str] = None
    source_channel: str
    status: RawInputStatus
    created_at: datetime.datetime


class AddRawInputResponse(BaseModel):
    id: str


class GetRawInputsResponse(BaseModel):
    results_count: int
    results: List[RawInputResponse]
    total_records_count: int
