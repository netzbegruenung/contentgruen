"""
"Antwort auf (optional)" fuer Beitragstypen ohne eigene Dublettenpruefung (Post, Bild,
#619): die Felder der Anfrage und der Antwort, wie beim Kommentar und bei der
Hintergrundinfo (dtos/commentary.py, dtos/generic_text.py).
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from domain.themen import ThemenDerAussage
from dtos.statement import ThemaDto

# Wie im Antwort-auf-Feld des Formulars und bei der Hintergrundinfo.
AUSSAGE_MIN_ZEICHEN = 10


class AntwortAufAnfrage(BaseModel):
    """Worauf der Beitrag antwortet. Ohne beides steht er fuer sich."""

    # ID einer vorhandenen Aussage oder, wenn keine bekannt ist, ihr Text.
    statement_id: Optional[UUID] = None
    statement_text: Optional[str] = Field(default=None, max_length=1000)
    # Die Themen der Aussage, wenn sie per Text kommt (#455): Eine neue bekommt sie,
    # eine vorhandene nur, wenn sie noch keine hat. Zu einer per ID gewaehlten
    # Aussage gelten sie nicht.
    themen: ThemenDerAussage = Field(default_factory=list)

    # Leer (oder nur Leerraum) heisst: keine Aussage. Sonst mindestens
    # AUSSAGE_MIN_ZEICHEN - kuerzer ist keine Aussage, auf die man antworten kann.
    @field_validator("statement_text")
    @classmethod
    def aussage_leer_oder_lang_genug(cls, text: Optional[str]) -> Optional[str]:
        if text is None or not text.strip():
            return None
        if len(text.strip()) < AUSSAGE_MIN_ZEICHEN:
            raise ValueError(
                f"Die Aussage braucht mindestens {AUSSAGE_MIN_ZEICHEN} Zeichen"
            )
        return text


class AntwortAufErgebnis(BaseModel):
    """Woran der gespeicherte Beitrag jetzt haengt."""

    # Die Aussage, an der der Beitrag haengt; None ohne Aussage oder wenn die
    # Verknuepfung scheiterte.
    statement_id: Optional[UUID] = None
    # Ihr Text - bei Text-Anfragen kann das eine schon vorhandene, sehr aehnliche
    # Aussage sein, nicht wortgleich mit dem Getippten.
    statement_text: Optional[str] = None
    # Kam die Aussage per Text mit Themen: die Themen, die sie jetzt hat. Sonst leer.
    themen: List[ThemaDto] = Field(default_factory=list)
    # False nur, wenn eine Aussage angegeben war und nicht verknuepft werden konnte.
    # Der Beitrag ist dann trotzdem gespeichert.
    verknuepft: bool = True
