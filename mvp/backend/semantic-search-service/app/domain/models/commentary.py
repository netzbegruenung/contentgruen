import datetime
from enum import Enum
from domain.models.zeit import UtcZeit
from pydantic import (
    BaseModel,
    ValidationError,
    field_validator,
    model_validator,
    Field,
)
from typing import ClassVar, List, Optional
import uuid
import json

from domain.models.content_type import ContentType
from domain.models.model_utils import ModelValidator
from domain.models.base_content import (
    BaseContent,
    BaseContentDbEntry,
    BaseContentSearchResult,
)


class Fassung(str, Enum):
    """
    Eine der Laengen eines Kommentars (GLOSSARY.md): Mittel ist der Haupttext
    (``text``), Kurz und Lang sind optional (``short_text``, ``long_text``).
    Kopiert und gezaehlt wird je Fassung (#355).
    """

    KURZ = "kurz"
    MITTEL = "mittel"
    LANG = "lang"


class Zweck(str, Enum):
    """
    Fuer wen ein Kommentar geschrieben ist (GLOSSARY.md, #357): als Antwort in
    Kommentarspalten an die Unentschiedenen, die mitlesen (Standard), oder fuer die
    eigenen Leute. Die Suche zeigt die Kommentare fuer die Kommentarspalte zuerst.
    """

    KOMMENTARSPALTE = "kommentarspalte"
    EIGENE_LEUTE = "eigene_leute"


class Stil(str, Enum):
    """
    Die Tonlage eines Kommentars (GLOSSARY.md, #357), optional. ``BISSIG`` nur beim
    Zweck "Fuer die eigenen Leute" (``Commentary._bissig_nur_fuer_eigene_leute``).
    """

    SACHLICH = "sachlich"
    HUMORVOLL = "humorvoll"
    PERSOENLICH = "persoenlich"
    BRUECKENBAUEND = "brueckenbauend"
    BISSIG = "bissig"


# Freie Stile von vor #357 (Seed und frueheres Formular), die einem Stil entsprechen.
# Andere freie Werte ("empathisch", "sarkastisch") haben keinen und fallen beim Lesen weg.
_STIL_ALTE_SCHREIBWEISEN = {
    "faktisch": Stil.SACHLICH,
    "persönlich": Stil.PERSOENLICH,
    "brückenbauend": Stil.BRUECKENBAUEND,
}


def bissig_ohne_eigene_leute(stil: Optional[Stil], zweck: Optional[Zweck]) -> bool:
    """Die Regel aus GLOSSARY.md, verletzt: "bissig" ausserhalb von "Fuer die eigenen Leute"."""
    return stil == Stil.BISSIG and zweck != Zweck.EIGENE_LEUTE


def stil_lesen(value, zweck: Optional[Zweck]) -> Optional[Stil]:
    """
    Ein gespeicherter Stil, nachsichtig gelesen: alte Schreibweisen werden zum Stil;
    was es nicht (mehr) gibt oder nicht zum Zweck passt, faellt weg, statt das Lesen
    scheitern zu lassen. Ohne Zweck gilt Kommentarspalte.
    """
    if isinstance(value, str):
        value = _STIL_ALTE_SCHREIBWEISEN.get(value, value)
    try:
        stil = Stil(value)
    except ValueError:
        return None
    return None if bissig_ohne_eigene_leute(stil, zweck) else stil


def fuer_eigene_leute(kommentar: Optional["Commentary"]) -> bool:
    """Ob ein Kommentar fuer die eigenen Leute geschrieben ist; die Suche stellt ihn hintan."""
    return kommentar is not None and kommentar.zweck == Zweck.EIGENE_LEUTE


class CommentaryReference(BaseModel):
    """
    Representing a link to a reference for a commentary

    Attributes:
    -----------
    reference_id: UUID
        Unique identifier for the reference
    created: datetime
        Timestamp the reference was linked to the commentary
    description: Optional[str]
        Notiz zu dieser Quelle, die nur fuer diesen Beitrag gilt. Sie haengt
        bewusst an der Verknuepfung und nicht an der Referenz: dieselbe Quelle
        kann in einem anderen Beitrag eine andere Notiz tragen.
    reference_text: Optional[str]
        The actual reference URL (populated when fetching for display)
    reference_description: Optional[str]
        Wird beim Lesen befuellt: die Notiz dieses Beitrags, sonst der Text der
        Referenz.
    """

    reference_id: uuid.UUID
    created: UtcZeit
    description: Optional[str] = None
    reference_text: Optional[str] = None
    reference_description: Optional[str] = None

    # Field validators to parse from JSON string to UUID and datetime objects

    @field_validator("reference_id", mode="before")
    def parse_uuid(cls, value):
        return ModelValidator.validate_uuid(value)

    @field_validator("created", mode="before")
    def parse_datetime(cls, value):
        return ModelValidator.validate_datetime(value)


class Commentary(BaseContent):
    """
    A commentary on something that can be used standalone but is especially intended to be used as a reply to a statement

    Attributes:
    -----------
    title: str
        Title of the commentary
    long_text: str
        Long text of the commentary, might be empty
    short_text: str
        Short text of the commentary, might be empty
    zweck: Zweck
        Fuer wen der Kommentar geschrieben ist; ohne Angabe Kommentarspalte
    style: Optional[Stil]
        Der Stil des Kommentars, optional
    references: List[CommentaryReference]
        List of references for the commentary
    """

    content_type: ContentType = ContentType.COMMENTARY

    # Der Titel ist eine Behauptung in einem Satz, kein Thema und keine Frage
    # (die gehoeren ins Statement). 120 Zeichen passen gemessen in die feste
    # 4-Zeilen-Titelbox der Suchkarte; Limit und Kartenhoehe gehoeren zusammen.
    title: str = Field(
        ..., min_length=3, max_length=120, description="Title of the commentary"
    )
    long_text: Optional[str] = None
    short_text: Optional[str] = None
    zweck: Zweck = Zweck.KOMMENTARSPALTE
    style: Optional[Stil] = None
    references: List[CommentaryReference]

    # Lesemodelle setzen das: Gespeichertes muss lesbar bleiben, auch mit einem Stil,
    # den es nicht (mehr) gibt oder der nicht zum Zweck passt (stil_lesen).
    STIL_NACHSICHTIG_LESEN: ClassVar[bool] = False

    @field_validator("zweck", mode="before")
    @classmethod
    def _zweck_ohne_angabe_ist_kommentarspalte(cls, value):
        return Zweck.KOMMENTARSPALTE if value is None else value

    @field_validator("style", mode="before")
    @classmethod
    def _stil_pruefen(cls, value, info):
        if cls.STIL_NACHSICHTIG_LESEN:
            return stil_lesen(value, info.data.get("zweck"))
        # Leer heisst: kein Stil, wie bei den Fassungen.
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def _bissig_nur_fuer_eigene_leute(self):
        if bissig_ohne_eigene_leute(self.style, self.zweck):
            raise ValueError(
                "Der Stil bissig geht nur beim Zweck Für die eigenen Leute"
            )
        return self

    @field_validator("references", mode="before")
    def parse_references(cls, value):
        if isinstance(value, str):
            try:
                # Deserialize the JSON string into a list of dicts
                references_data = json.loads(value)
                if not isinstance(references_data, list):
                    raise ValueError("References should be a list")

                # Convert each dict into a CommentaryReference object
                return [
                    CommentaryReference(**reference) for reference in references_data
                ]
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON format for references: {value}. Error: {e}"
                )
            except ValidationError as e:
                raise ValueError(f"Error validating references: {e}")
        return value


class CommentaryDbEntry(Commentary, BaseContentDbEntry):
    """
    Representing a commentary with additional metadata for indexing

    Attributes:
    -----------
    references_count: int
        Count of references in the commentary
    usage_count: Optional[int]
        Number of times this commentary has been used (copied)
    """

    references_count: int
    usage_count: Optional[int] = None

    STIL_NACHSICHTIG_LESEN: ClassVar[bool] = True


class CommentarySearchResult(CommentaryDbEntry, BaseContentSearchResult):
    """
    Representing a commentary entry with score and additional result metadata
    """
