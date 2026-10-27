"""
Was die aufrufende Person an einem Beitrag sieht (#333).

Die Kennung ist personenbezogen (GLOSSARY.md). Angemeldete bekommen statt der
Kennung den Anzeigenamen und ``ist_eigener_beitrag``, Admins zusaetzlich die
Kennung (Moderation). Besucher bekommen keins von beidem.
"""

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Type, TypeVar

from dtos.beitrag import BeitragAntwort
from services.anzeigename_service import angemeldet, get_anzeigename_service

A = TypeVar("A", bound=BeitragAntwort)


@dataclass(frozen=True)
class Aufrufer:
    """Wer eine Antwort bekommt: Kennung aus X-User, Admin aus X-Is-Admin."""

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


def fuer_aufrufer(antworten: Sequence[A], aufrufer: Aufrufer) -> Sequence[A]:
    """
    Setzt an jeder Antwort, was der Aufrufer sehen darf, und gibt sie zurueck.

    Aendert die Antworten selbst: Sie muessen frisch aus dem DbEntry umgewandelt
    sein (``als_antworten``), nie ein Objekt, das ein Cache noch haelt.
    Die Anzeigenamen kommen aus einer Abfrage fuer alle.
    """
    if aufrufer.angemeldet and antworten:
        namen = get_anzeigename_service().namen(a.original_author for a in antworten)
        for antwort in antworten:
            antwort.autor_name = namen.get(antwort.original_author)
            antwort.ist_eigener_beitrag = antwort.original_author == aufrufer.kennung
    if not aufrufer.ist_admin:
        for antwort in antworten:
            antwort.original_author = None
    return antworten


def als_antworten(klasse: Type[A], inhalte: Iterable, aufrufer: Aufrufer) -> List[A]:
    """Die Beitraege als ``klasse``, fuer diesen Aufrufer."""
    antworten = [klasse.model_validate(inhalt) for inhalt in inhalte]
    fuer_aufrufer(antworten, aufrufer)
    return antworten
