import json

from pydantic import BaseModel, field_validator
from typing import Dict, List, Optional

from domain.models.commentary import (
    CommentaryReference,
    Fassung,
    Stil,
    Zweck,
    stil_lesen,
)
from domain.models.content import ContentDbEntry
from dtos.beitrag import BeitragResponse


###   Responses   ###


class ContributionEntry(ContentDbEntry):
    """
    Ein Eintrag in "Meine Beitraege", so wie die Beitragskarte ihn braucht.

    ContentDbEntry allein verwirft beim Lesen aus Qdrant alles, was nicht zu den
    gemeinsamen Feldern gehoert - auch Titel und Bildadresse, obwohl sie im Payload
    stehen. Die Nutzung und ihr Zuwachs der letzten 7 Tage liegen nicht in Qdrant,
    sondern in PostgreSQL und werden im Endpunkt nachgetragen, ebenso Adresse und Beschreibung der Herkunft.

    Die Herkunft nutzt CommentaryReference: GenericTextReference hat dieselben Felder,
    Bild und Post haben keine Herkunft.
    """

    # Optional wie im Bildmodell: ein Bild ohne Bildunterschrift ist ein gueltiger
    # Beitrag und darf beim Lesen nicht herausfallen.
    text: Optional[str] = None
    title: Optional[str] = None
    image_url: Optional[str] = None
    usage_count: int = 0
    # Zuwachs der letzten 7 Tage (#349); steht nicht im Payload, kommt wie
    # usage_count aus PostgreSQL.
    nutzung_letzte_7_tage: int = 0
    # Kurz- und Langfassung eines Kommentars (#355); die Karte zeigt Reiter dafuer.
    short_text: Optional[str] = None
    long_text: Optional[str] = None
    # Zweck und Stil eines Kommentars (#357); None bei anderen Typen und bei
    # Kommentaren von vor #357 (dann gilt Kommentarspalte).
    zweck: Optional[Zweck] = None
    style: Optional[Stil] = None
    references: List[CommentaryReference] = []

    @field_validator("style", mode="before")
    @classmethod
    def _stil_lesen(cls, value):
        # Wie CommentaryDbEntry: Gespeichertes muss lesbar bleiben.
        return stil_lesen(value)

    @field_validator("usage_count", mode="before")
    @classmethod
    def _nutzung_null_als_null(cls, value):
        # Aeltere Payloads tragen usage_count: null. Die echte Zahl kommt ohnehin aus
        # PostgreSQL und wird im Endpunkt nachgetragen; ohne diese Umwandlung
        # scheitert schon das Lesen aus Qdrant und die ganze Liste mit 500.
        return 0 if value is None else value

    @field_validator("references", mode="before")
    @classmethod
    def _herkunft_als_liste(cls, value):
        # Wie Commentary.parse_references: aeltere Payloads tragen die Liste als JSON-Text.
        if value is None:
            return []
        if isinstance(value, str):
            return json.loads(value)
        return value


class FassungsNutzung(BaseModel):
    """Nutzung einer Fassung und ihr Zuwachs der letzten 7 Tage (#355)."""

    nutzung: int = 0
    letzte_7_tage: int = 0


class MeinBeitragResponse(BeitragResponse):
    """
    Ein Beitrag in "Meine Beitraege", wie er nach aussen geht (#385).

    Dieselbe Auswahl wie ueberall an Beitraegen (dtos/beitrag.py) plus, was die
    Album-Karte braucht. ``ContributionEntry`` bleibt das Lesemodell aus Qdrant;
    Bearbeitungshistorie und Moderationsfelder bleiben dort zurueck.
    """

    image_url: Optional[str] = None
    usage_count: int = 0
    nutzung_letzte_7_tage: int = 0
    short_text: Optional[str] = None
    long_text: Optional[str] = None
    zweck: Optional[Zweck] = None
    style: Optional[Stil] = None
    # Nur am Kommentar: je vorhandener Fassung ("kurz", "mittel", "lang"); None bei
    # anderen Typen oder wenn die Zahlen nicht lesbar waren.
    nutzung_je_fassung: Optional[Dict[Fassung, FassungsNutzung]] = None
    references: List[CommentaryReference] = []


class GetContributionsOfUserResponse(BaseModel):
    results_count: int
    results: List[MeinBeitragResponse]
    total_records_count: int
