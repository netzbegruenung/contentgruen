"""
Was die aufrufende Person an einem Beitrag sieht (#333), ebenso an Aussagen,
Herkunft, Einwuerfen und Saetzen (#385).

Die Kennung ist personenbezogen (GLOSSARY.md). Angemeldete bekommen statt der
Kennung den Anzeigenamen und ein Kennzeichen, ob es der eigene Beitrag,
die eigene Aussage usw. ist (``ist_eigener_beitrag`` usw.), Admins zusaetzlich die Kennung (Moderation).
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
    """Wer eine Antwort mit Personenbezug bekommt: Kennung aus X-User, Admin aus X-Is-Admin."""

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

    Das Feld ``kennung_feld`` behalten nur Admins. ``name_feld`` und ``eigen_feld``
    bekommen Angemeldete statt der Kennung; ohne sie (Destillierer, Ausformulierer)
    geht an Nicht-Admins gar nichts zur Person.
    """

    kennung_feld: str
    name_feld: Optional[str] = None
    eigen_feld: Optional[str] = None

    def nur_kennung(self) -> "Personenbezug":
        """Derselbe Bezug ohne Anzeigename und Kennzeichen: nur die Kennung leeren."""
        return Personenbezug(self.kennung_feld)


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
    benannt = [(o, b) for o, b in paare if b.name_feld]
    if aufrufer.angemeldet and benannt:
        namen = get_anzeigename_service().namen(
            getattr(o, b.kennung_feld) for o, b in benannt
        )
        for objekt, bezug in benannt:
            kennung = getattr(objekt, bezug.kennung_feld)
            if kennung is None:
                # Niemand Bekanntes (Einwurf ohne Sitzung): weder eigen noch fremd.
                continue
            setattr(objekt, bezug.name_feld, namen.get(kennung))
            setattr(objekt, bezug.eigen_feld, kennung == aufrufer.kennung)
    if not aufrufer.ist_admin:
        for objekt, bezug in paare:
            setattr(objekt, bezug.kennung_feld, None)


def fuer_aufrufer(
    objekte: Sequence[A], aufrufer: Aufrufer, bezug: Personenbezug = BEITRAG
) -> Sequence[A]:
    """Wie ``personen_fuer_aufrufer`` fuer eine Liste; gibt sie zurueck."""
    personen_fuer_aufrufer(aufrufer, (objekte, bezug))
    return objekte


def als_responses(
    klasse: Type[A],
    quellen: Iterable,
    aufrufer: Aufrufer,
    bezug: Personenbezug = BEITRAG,
) -> List[A]:
    """Die Objekte als ``klasse``, fuer diesen Aufrufer."""
    objekte = [klasse.model_validate(quelle) for quelle in quellen]
    fuer_aufrufer(objekte, aufrufer, bezug)
    return objekte
