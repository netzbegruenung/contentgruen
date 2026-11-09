import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from domain.cc0_hinweis import Cc0Wortlaut
from domain.models.commentary import CommentaryReference, Stil, Zweck
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from domain.models.generic_text import GenericTextReference

if TYPE_CHECKING:
    from services.dublette import Dublette


class VorhandenDto(BaseModel):
    """
    In der Antwort auf das Anlegen eines Kommentars oder einer Hintergrundinfo: der
    vorhandene Beitrag, dessen Dublette der neue waere (services/dublette.py). Dann
    wurde nichts angelegt, und die Person entscheidet.
    """

    # Titel des vorhandenen, damit das Formular ihn nennen kann.
    titel: Optional[str] = None
    # Der vorhandene ist von derselben Person: Zustimmen saehe sich selbst eine
    # Stimme geben, nehmen geht.
    eigen: bool = False

    @classmethod
    def aus(cls, dublette: Optional["Dublette"]) -> Optional["VorhandenDto"]:
        """Aus der Dublette (services/dublette.py); None ohne Dublette."""
        if dublette is None:
            return None
        return cls(titel=dublette.vorhanden.title, eigen=dublette.eigen)


class BeitragResponse(BaseModel):
    """
    Ein Beitrag, wie Suche und lesende Routen ihn ausliefern (#333, Muster aus #311).

    Bewusst eine Auswahl aus dem DbEntry: keine Kennung (``last_modified_by``,
    ``authors``, ``edit_history``), keine Felder der Moderation und
    Dublettenpruefung. Wer hier ein Feld ergaenzt, entscheidet, dass es nach aussen
    geht. ``original_author`` ist nur unterwegs belegt: ``fuer_aufrufer``
    (services/beitrag_fuer_aufrufer.py) setzt daraus Anzeigename und
    ``ist_eigener_beitrag`` und leert es fuer alle ausser Admins.

    ``from_attributes``: Ein DbEntry laesst sich direkt umwandeln, auch als Feld
    eines Suchtreffers; alles, was hier nicht steht, bleibt dabei zurueck.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content_type: ContentType
    # Nur Hintergrundinfo, Kommentar, Post und Bild haben einen; die
    # Inhalte aus /content nicht.
    title: Optional[str] = None
    # Unterschrift beim Bild; None nur bei Bildern von vor #281.
    text: Optional[str] = None
    created: datetime.datetime
    status: ContentStatus
    usage_count: Optional[int] = None
    # Anzeigename zu original_author; nur fuer angemeldete Aufrufer, sonst None.
    autor_name: Optional[str] = None
    # Ob die aufrufende Person den Beitrag gespeichert hat; nur angemeldet, sonst None.
    ist_eigener_beitrag: Optional[bool] = None
    # Die Kennung des Autors, nur fuer Admins (Moderation), sonst None.
    original_author: Optional[str] = None


class KommentarResponse(BeitragResponse):
    title: str
    long_text: Optional[str] = None
    short_text: Optional[str] = None
    # Die Karte zeigt den Stil und markiert Beitraege fuer die eigenen Leute (#357).
    zweck: Zweck = Zweck.KOMMENTARSPALTE
    style: Optional[Stil] = None
    references: List[CommentaryReference] = []
    references_count: int = 0
    # Wie viele Kommentare auf diesem beruhen ("N Varianten", #356); nachgetragen
    # von services/varianten.py, wo die Karte sie zeigt, sonst 0.
    varianten: int = 0


class HintergrundinfoResponse(BeitragResponse):
    title: str
    references: List[GenericTextReference] = []
    references_count: int = 0
    # Wie bei KommentarResponse (#356).
    varianten: int = 0


class PostResponse(BeitragResponse):
    title: str
    platform: str
    # Das Konto auf der Plattform ("@name"), oeffentlich am Post - keine Kennung.
    author: Optional[str] = None
    url: Optional[str] = None
    engagement: int = 0


# Treffer der Suche je Typ: dieselbe Auswahl plus die Aehnlichkeit.


class BeitragTreffer(BeitragResponse):
    score: float


class KommentarTreffer(KommentarResponse):
    score: float


class HintergrundinfoTreffer(HintergrundinfoResponse):
    score: float


class PostTreffer(PostResponse):
    score: float


### Beitrag aendern (#299) ###

# Wie im Formular (reference-input.component.ts, maxReferences).
HERKUENFTE_HOECHSTENS = 10


class HerkunftEingabe(BaseModel):
    """Eine Herkunft in der Aenderung: Adresse oder Fundstelle, dazu die Notiz."""

    reference_string: str = Field(min_length=1, max_length=2000)
    description: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("reference_string", mode="before")
    @classmethod
    def ohne_leerraum_am_rand(cls, wert):
        return wert.strip() if isinstance(wert, str) else wert

    @field_validator("description", mode="before")
    @classmethod
    def leer_heisst_keine_notiz(cls, wert):
        if isinstance(wert, str):
            return wert.strip() or None
        return wert


class BeitragAendernRequest(BaseModel):
    """
    Titel, Text und Herkunft eines Kommentars oder einer Hintergrundinfo, je ganz
    ersetzt, beim Kommentar auch Kurz- und Langfassung. Der Titel folgt der
    Titelregel (3-120 Zeichen wie beim Anlegen); die Grenze des Texts haengt am Typ
    und prueft der Service.
    """

    title: str = Field(min_length=3, max_length=120)
    # Mindestens 10 Zeichen wie in den Formularen beim Anlegen.
    text: str = Field(min_length=10)
    references: List[HerkunftEingabe] = Field(
        default_factory=list, max_length=HERKUENFTE_HOECHSTENS
    )
    # Der CC0-Hinweis im Dialog, wie beim Anlegen (#431, domain/cc0_hinweis.py).
    cc0_wortlaut: Cc0Wortlaut = None
    # Kurz- und Langfassung, nur beim Kommentar (#551). Fehlt das Feld (eine aeltere
    # App), bleibt die Fassung; leer heisst, sie entfaellt. Die Grenzen haengen am
    # Typ und prueft der Service wie beim Text.
    short_text: Optional[str] = None
    long_text: Optional[str] = None

    @field_validator("title", "text", "short_text", "long_text", mode="before")
    @classmethod
    def ohne_leerraum_am_rand(cls, wert):
        return wert.strip() if isinstance(wert, str) else wert
