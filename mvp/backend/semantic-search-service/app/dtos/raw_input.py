"""
DTOs fuer den Fangkorb (Rohinput).

Die einzige inhaltliche Pflicht beim Einwerfen ist, dass ueberhaupt etwas
dasteht. Kein Titel, keine Kategorie, kein Zieltyp - all das ist Destillieren
und passiert erst im Destillier-Ablauf (Satz, Status, Verknuepfung).
"""

import datetime
import uuid
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from domain.models.content_type import ContentType
from domain.models.raw_input import RawInputSource, RawInputStatus
from utils.url_validator import validate_url_security

# Der Entwurfssatz wird der Titel des Beitrags und hat deshalb dasselbe Limit
# wie der Titel von Kommentar und Hintergrundinfo.
SATZ_LIMIT = 120

# Die Beitragstypen, die aus dem Destillier-Ablauf entstehen koennen.
BEITRAGSTYPEN = (ContentType.COMMENTARY, ContentType.GENERIC_TEXT)


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
        description="Hinweis fuer andere: Freitext zum Link oder der Fund selbst",
    )
    url: Optional[str] = Field(
        default=None, max_length=2000, description="Link auf den Beitrag"
    )
    image_url: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="URL eines bereits erreichbaren Bildes",
    )

    source_channel: Optional[RawInputSource] = Field(
        default=None,
        description="Kanal, ueber den der Einwurf hereinkam. Ohne Angabe: web",
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


class SaveDraftRequest(BaseModel):
    """
    Der Entwurfssatz: "Was ist der Punkt? Ein Satz."

    Leer (oder nur Leerraum) loescht den eigenen Entwurf.
    """

    sentence: Optional[str] = Field(
        default=None,
        max_length=SATZ_LIMIT,
        description="Der Satz, der spaeter der Titel des Beitrags wird",
    )

    @field_validator("sentence", mode="before")
    @classmethod
    def leerraum_abschneiden(cls, value):
        return _normalisieren(value) if isinstance(value, str) else value


class UpdateRawInputStatusRequest(BaseModel):
    """
    Statuswechsel aus dem Destillier-Ablauf.

    Nur zwei Ziele: ``discarded`` (ohne content_id) und ``processed`` (nur mit
    content_id - der Beitrag, der entstanden ist). ``in_progress`` wird hier nicht
    vergeben: das setzt der erste gespeicherte Satz.

    ``content_type`` ist bei processed optional, damit eine noch zwischengespeicherte
    aeltere App-Version nicht scheitert; ohne ihn bleibt die Karte ungefaerbt.
    """

    status: RawInputStatus
    content_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Der entstandene Beitrag; Pflicht bei processed",
    )
    content_type: Optional[ContentType] = Field(
        default=None,
        description="Typ des entstandenen Beitrags (commentary oder generic_text)",
    )

    @model_validator(mode="after")
    def ziel_und_beitrag_passen(self):
        if self.status not in (RawInputStatus.DISCARDED, RawInputStatus.PROCESSED):
            raise ValueError("status muss discarded oder processed sein")
        if self.status == RawInputStatus.PROCESSED and self.content_id is None:
            raise ValueError("processed braucht die content_id des Beitrags")
        if self.status == RawInputStatus.DISCARDED and (
            self.content_id is not None or self.content_type is not None
        ):
            raise ValueError(
                "discarded nimmt keine content_id und keinen content_type an"
            )
        if self.content_type is not None and self.content_type not in BEITRAGSTYPEN:
            raise ValueError("content_type muss commentary oder generic_text sein")
        return self


###   Responses   ###


class RawInputDraftResponse(BaseModel):
    """Ein Satz zu einem Einwurf, mit Person und Zeitpunkt der letzten Aenderung."""

    id: str
    user_id: str
    sentence: str
    updated_at: datetime.datetime


class RawInputLinkResponse(BaseModel):
    """
    Ein Beitrag, der aus dem Einwurf entstanden ist.

    ``draft_id`` ist der ausformulierte Satz; None, wenn die Person ihren Satz
    spaeter geleert hat. ``content_type`` ist None bei Verknuepfungen aus der Zeit
    vor Fangkorb v2.
    """

    content_id: str
    content_type: Optional[str] = None
    draft_id: Optional[str] = None
    processed_by: Optional[str] = None
    processed_at: datetime.datetime


class RawInputResponse(BaseModel):
    """
    Ein Einwurf, wie ihn der Fangkorb ausliefert.

    ``drafts`` sind alle Saetze aller Personen, aelteste Aenderung zuerst - sie sind
    fuer alle Angemeldeten sichtbar. ``own_draft`` ist daraus der Satz der
    anfragenden Person. ``links`` sind alle entstandenen Beitraege, aelteste
    zuerst; die processed-Felder beschreiben davon den ersten.
    """

    id: str
    content: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    submitted_by: Optional[str] = None
    source_channel: str
    status: RawInputStatus
    created_at: datetime.datetime
    destilled_by: Optional[str] = None
    own_draft: Optional[str] = None
    processed_content_id: Optional[str] = None
    processed_by: Optional[str] = None
    processed_at: Optional[datetime.datetime] = None
    drafts: List[RawInputDraftResponse] = Field(default_factory=list)
    links: List[RawInputLinkResponse] = Field(default_factory=list)


class AddRawInputResponse(BaseModel):
    id: str


class GetRawInputsResponse(BaseModel):
    results_count: int
    results: List[RawInputResponse]
    total_records_count: int


class DraftResponse(BaseModel):
    """Der gespeicherte Entwurf; ``sentence`` ist None, wenn er geloescht wurde."""

    raw_input_id: str
    sentence: Optional[str] = None
    updated_at: Optional[datetime.datetime] = None
