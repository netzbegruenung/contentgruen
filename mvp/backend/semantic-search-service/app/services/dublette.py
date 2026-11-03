"""
Die Entscheidung der Person ueber eine Dublette, gleich fuer Kommentar und
Hintergrundinfo (Glossar "Dublette").

Ein neuer Beitrag, der einem vorhandenen desselben Typs fast gleicht, wird nicht
angelegt: Die Person sieht den vorhandenen und entscheidet. Beim ersten Versuch hat
sie das noch nicht; danach kommt ihre Entscheidung mit derselben Anfrage zurueck:

- ``trotz_dublette_von``: trotzdem speichern - die neue wird angelegt.
- ``vorhanden_nehmen``: den eigenen vorhandenen nehmen - erst das verknuepft ihn mit
  der mitgeschickten Aussage. Einen fremden verknuepft auch das nicht.

Beides gilt nur fuer den vorhandenen, den die Person gesehen hat: Ist inzwischen ein
anderer vorhanden, sieht sie erst ihn.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from domain.models.base_content import BaseContentSearchResult
from dtos.beitrag import VorhandenDto
from services.content.base_content_service import Dublettenpruefung


class VorhandenWeg(Exception):
    """Der Beitrag, den die Person nehmen wollte, ist nicht mehr vorhanden."""


def ist_gezeigter(
    vorhanden: Optional[BaseContentSearchResult], angefragt: Optional[UUID]
) -> bool:
    """Die Entscheidung der Person gilt genau dem vorhandenen, den sie gesehen hat."""
    return (
        vorhanden is not None
        and angefragt is not None
        and str(vorhanden.id) == str(angefragt)
    )


def entscheidung_anwenden(
    pruefung: Dublettenpruefung,
    trotz_dublette_von: Optional[UUID],
    vorhanden_nehmen: Optional[UUID],
) -> Dublettenpruefung:
    """
    Die Pruefung nach der Entscheidung der Person: Speichert sie trotz genau dieses
    vorhandenen, gilt keiner als vorhanden (der aehnlichste Treffer bleibt fuer
    most_similar_* erhalten).

    Wirft VorhandenWeg, wenn sie einen vorhandenen nehmen wollte und keiner mehr
    vorhanden ist: Einen neuen anzulegen, hat sie nicht gewaehlt.
    """
    if ist_gezeigter(pruefung.vorhanden, trotz_dublette_von):
        pruefung = Dublettenpruefung(vorhanden=None, aehnlichster=pruefung.aehnlichster)
    if pruefung.vorhanden is None and vorhanden_nehmen is not None:
        raise VorhandenWeg()
    return pruefung


@dataclass(frozen=True)
class Dublette:
    """
    Der vorhandene Beitrag, dessen Dublette der neue waere, aus Sicht der Person.

    - eigen: Er ist von ihr - Zustimmen saehe sich selbst eine Stimme geben.
    - genommen: Sie hat ihn, ihren eigenen, mit vorhanden_nehmen gewaehlt; nur dann
      wird er mit der mitgeschickten Aussage verknuepft.
    """

    vorhanden: BaseContentSearchResult
    eigen: bool
    genommen: bool

    @classmethod
    def aus(
        cls,
        vorhanden: Optional[BaseContentSearchResult],
        aufrufer: str,
        vorhanden_nehmen: Optional[UUID],
    ) -> Optional["Dublette"]:
        """None, wenn nichts vorhanden ist (der neue Beitrag ist angelegt)."""
        if vorhanden is None:
            return None
        eigen = vorhanden.original_author == aufrufer
        return cls(
            vorhanden=vorhanden,
            eigen=eigen,
            genommen=eigen and ist_gezeigter(vorhanden, vorhanden_nehmen),
        )

    def als_antwort(self) -> VorhandenDto:
        return VorhandenDto(titel=self.vorhanden.title, eigen=self.eigen)
