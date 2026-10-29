import datetime
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID

from domain.models.commentary import CommentaryReference, Stil, Zweck
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from domain.models.generic_text import GenericTextReference


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


class HintergrundinfoResponse(BeitragResponse):
    title: str
    references: List[GenericTextReference] = []
    references_count: int = 0


class PostResponse(BeitragResponse):
    title: str
    platform: str
    # Das Konto auf der Plattform ("@name"), oeffentlich am Post - keine Kennung.
    author: str
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
