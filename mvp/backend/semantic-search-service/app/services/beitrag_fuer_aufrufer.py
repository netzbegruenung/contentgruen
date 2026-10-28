"""
Was die aufrufende Person an einem Beitrag sieht (#333), ebenso an Aussagen,
Herkunft, Einwuerfen und Saetzen (#385).

Die Kennung ist personenbezogen (GLOSSARY.md). Angemeldete bekommen statt der
Kennung den Anzeigenamen und ein Kennzeichen fuer den eigenen Eintrag
(``ist_eigener_beitrag`` usw.), Admins zusaetzlich die Kennung (Moderation).
Besucher bekommen keins von beidem.
"""

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple, Type, TypeVar

from pydantic import BaseModel

from services.anzeigename_service import angemeldet, get_anzeigename_service

# Ein Response-DTO mit den Feldern eines Personenbezugs (dtos/beitrag.py u. a.);
# die Service-Schicht kennt die DTOs selbst nicht.
A = TypeVar("A", bound=BaseModel)


@dataclass(frozen=True)
class Aufrufer:
    """Wer Beitraege ausgeliefert bekommt: Kennung aus X-User, Admin aus X-Is-Admin."""

    kennung: Optional[str] = None
    # Der Kopf allein; ob jemand Admin ist, sagt ist_admin.
    admin_kopf: bool = False

    @property
    def angemeldet(self) -> bool:
        return angemeldet(self.kennung)

    @property
    def ist_admin(self) -> bool:
        # Den Kopf setzt allein das BFF, und nur fuer Angemeldete.
        return self.admin_kopf and self.angemeldet


@dataclass(frozen=True)
class Personenbezug:
    """
    Die Felder eines Response-DTOs, die eine Person bezeichnen.

    ``kennung`` behalten nur Admins. ``name`` und ``eigen`` bekommen Angemeldete
    statt der Kennung; ohne sie (Destillierer, Ausformulierer) geht an
    Nicht-Admins gar nichts zur Person.
    """

    kennung: str
    name: Optional[str] = None
    eigen: Optional[str] = None


BEITRAG = Personenbezug("original_author", "autor_name", "ist_eigener_beitrag")
AUSSAGE = Personenbezug("original_author", "autor_name", "ist_eigene_aussage")
HERKUNFT = Personenbezug("original_author", "autor_name", "ist_eigene_herkunft")
EINWURF = Personenbezug("submitted_by", "submitted_by_name", "ist_eigener_einwurf")
SATZ = Personenbezug("user_id", "user_name", "ist_eigener_satz")
DESTILLIERER = Personenbezug("destilled_by")
AUSFORMULIERER = Personenbezug("processed_by")

Gruppe = Tuple[Sequence[BaseModel], Personenbezug]


def personen_fuer_aufrufer(aufrufer: Aufrufer, *gruppen: Gruppe) -> None:
    """
    Setzt an allen Objekten aller Gruppen, was der Aufrufer zur Person sehen darf.

    Aendert die Objekte selbst: Sie muessen frisch aus dem DbEntry umgewandelt
    sein (``als_responses``), nie ein Objekt, das ein Cache noch haelt.
    Die Anzeigenamen kommen aus einer Abfrage fuer alle Gruppen zusammen.
    """
    paare = [(objekt, bezug) for objekte, bezug in gruppen for objekt in objekte]
    benannt = [(o, b) for o, b in paare if b.name]
    if aufrufer.angemeldet and benannt:
        namen = get_anzeigename_service().namen(
            getattr(o, b.kennung) for o, b in benannt
        )
        for objekt, bezug in benannt:
            kennung = getattr(objekt, bezug.kennung)
            if kennung is None:
                # Niemand Bekanntes (Einwurf ohne Sitzung): weder eigen noch fremd.
                continue
            setattr(objekt, bezug.name, namen.get(kennung))
            setattr(objekt, bezug.eigen, kennung == aufrufer.kennung)
    if not aufrufer.ist_admin:
        for objekt, bezug in paare:
            setattr(objekt, bezug.kennung, None)


def fuer_aufrufer(
    beitraege: Sequence[A], aufrufer: Aufrufer, bezug: Personenbezug = BEITRAG
) -> Sequence[A]:
    """Wie ``personen_fuer_aufrufer`` fuer eine Liste; gibt sie zurueck."""
    personen_fuer_aufrufer(aufrufer, (beitraege, bezug))
    return beitraege


def als_responses(
    klasse: Type[A],
    inhalte: Iterable,
    aufrufer: Aufrufer,
    bezug: Personenbezug = BEITRAG,
) -> List[A]:
    """Die Inhalte als ``klasse``, fuer diesen Aufrufer."""
    beitraege = [klasse.model_validate(inhalt) for inhalt in inhalte]
    fuer_aufrufer(beitraege, aufrufer, bezug)
    return beitraege
