"""
Was die aufrufende Person an einem Beitrag sieht (#333).

Die Kennung ist personenbezogen (GLOSSARY.md). Angemeldete bekommen statt der
Kennung den Anzeigenamen und ``ist_eigener_beitrag``, Admins zusaetzlich die
Kennung (Moderation). Besucher bekommen keins von beidem.
"""

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Type, TypeVar

from pydantic import BaseModel

from services.anzeigename_service import angemeldet, get_anzeigename_service

# Ein Response-DTO mit original_author, autor_name und ist_eigener_beitrag
# (dtos/beitrag.py); die Service-Schicht kennt die DTOs selbst nicht.
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


def fuer_aufrufer(beitraege: Sequence[A], aufrufer: Aufrufer) -> Sequence[A]:
    """
    Setzt an jedem Beitrag, was der Aufrufer sehen darf, und gibt sie zurueck.

    Aendert die Beitraege selbst: Sie muessen frisch aus dem DbEntry umgewandelt
    sein (``als_responses``), nie ein Objekt, das ein Cache noch haelt.
    Die Anzeigenamen kommen aus einer Abfrage fuer alle.
    """
    if aufrufer.angemeldet and beitraege:
        namen = get_anzeigename_service().namen(b.original_author for b in beitraege)
        for beitrag in beitraege:
            beitrag.autor_name = namen.get(beitrag.original_author)
            beitrag.ist_eigener_beitrag = beitrag.original_author == aufrufer.kennung
    if not aufrufer.ist_admin:
        for beitrag in beitraege:
            beitrag.original_author = None
    return beitraege


def als_responses(klasse: Type[A], inhalte: Iterable, aufrufer: Aufrufer) -> List[A]:
    """Die Beitraege als ``klasse``, fuer diesen Aufrufer."""
    beitraege = [klasse.model_validate(inhalt) for inhalt in inhalte]
    fuer_aufrufer(beitraege, aufrufer)
    return beitraege
