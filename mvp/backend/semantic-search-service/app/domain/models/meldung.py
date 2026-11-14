"""
Angaben der meldenden Person an einer Meldung (Glossar „Meldung“, #438).

Grenzen fuer Name und E-Mail-Adresse, an einer Stelle fuer Melde-Route und
Tabelle ``content_reports``. Der Meldedialog fuehrt dieselben Werte in
``shared/components/report-dialog``. 254 ist die laengste zulaessige
E-Mail-Adresse (RFC 5321).
"""

from dataclasses import dataclass
from typing import NamedTuple, Optional
from uuid import UUID

from pydantic.networks import validate_email
from pydantic_core import PydanticCustomError

MELDER_NAME_MAX = 200
MELDER_EMAIL_MAX = 254


@dataclass(frozen=True)
class MelderAngaben:
    """Was die meldende Person nach Art. 16 Abs. 2 DSA zur Meldung angibt.

    Name und E-Mail-Adresse sind freiwillig (lit. c), die Erklaerung guten
    Glaubens ist Pflicht (lit. d). Die drei reisen gemeinsam von der Melde-Route
    ueber den ModerationService bis in die Tabelle.
    """

    guter_glaube: bool
    name: Optional[str] = None
    email: Optional[str] = None


class MelderAdresse(NamedTuple):
    """E-Mail-Adresse einer offenen Meldung und der gemeldete Beitrag (#493)."""

    content_id: UUID
    email: str


@dataclass(frozen=True)
class MelderSuche:
    """Name und/oder E-Mail-Adresse, nach denen ein Admin die Meldungen einer
    Person sucht, um Auskunft zu geben oder ihre Angaben zu loeschen (#494).

    Gesucht wird nur die ganze Angabe, ohne Ruecksicht auf Gross- und
    Kleinschreibung: Ein Teiltreffer zeigte Meldungen anderer Personen. Sind
    beide angegeben, muessen beide passen. Leere Angaben zaehlen als nicht
    angegeben; ohne jede Angabe gibt es keine Suche. Die Adresse wird so
    normalisiert wie beim Speichern (EmailStr), sonst faende eine anders
    geschriebene, gleiche Adresse nichts.
    """

    email: Optional[str] = None
    name: Optional[str] = None

    def __post_init__(self):
        email = (self.email or "").strip() or None
        name = (self.name or "").strip() or None
        if email is None and name is None:
            raise ValueError("Name oder E-Mail-Adresse fehlt")
        object.__setattr__(self, "email", _wie_gespeichert(email))
        object.__setattr__(self, "name", name)

    @property
    def nur_name(self) -> bool:
        """Ohne E-Mail-Adresse koennen die Treffer verschiedene Personen sein."""
        return self.email is None


def _wie_gespeichert(email: Optional[str]) -> Optional[str]:
    """Die Adresse in der Form, in der EmailStr sie speichert (Unicode NFC,
    Domain normalisiert); was keine gueltige Adresse ist, bleibt, wie es ist."""
    if email is None:
        return None
    try:
        return validate_email(email)[1]
    except PydanticCustomError:
        return email


@dataclass(frozen=True)
class AngabenGeloescht:
    """Was das Loeschen der Angaben einer Person getan hat (#494).

    Bearbeitete und abgewiesene Meldungen sind ganz geloescht; offene bleiben
    als Arbeit fuer die Moderation stehen und haben nur Name und E-Mail-Adresse
    verloren.
    """

    geloescht: int
    angaben_entfernt: int


@dataclass(frozen=True)
class MeldungErgebnis:
    """
    Was ``ModerationService.report_content`` angelegt hat. Wahr, wenn die Meldung
    angenommen ist; ``neu`` ist falsch bei einer Doppelmeldung derselben Person (dann
    entsteht nichts, und es kommt keine Mail); ``mit_email``, ob an der neuen Meldung
    eine Adresse fuer Bestaetigung und Entscheidung steht (Review zu #670).
    """

    erfolg: bool
    neu: bool = False
    mit_email: bool = False

    def __bool__(self) -> bool:
        return self.erfolg


MELDUNG_FEHLGESCHLAGEN = MeldungErgebnis(erfolg=False)
