"""
Die Meilensteine einer Person (GLOSSARY.md "Meilenstein", ADR 0004, #351).

Wie die Punkte (services/punkte_service.py) werden sie bei jedem Abruf aus dem Bestand
berechnet und nicht gespeichert; gesperrte und endgueltig entfernte Beitraege fallen
damit von selbst heraus. Gezeigt werden sie nur der Person selbst, in "Meine Beitraege".
Ein Abzeichen am Anzeigenamen, das andere sehen, braucht eine eigene Zustimmung zur
Sichtbarkeit (docs/VISION.md "Meilensteine", ADR 0004 "Ranglisten nur mit Zustimmung",
docs/DSFA.md Abschnitt 3 Risiko 1); die gibt es noch nicht, deshalb hier auch kein
Abzeichen fuer andere.

Woher die Zahlen kommen:
- Nutzung: die entdoppelte Nutzung der sichtbaren Beitraege, wie bei den Punkten;
  eigene Kopien und Kopien von Startkonten zaehlen dort schon nicht.
- Zustimmung: Zustimmungen anderer zu den sichtbaren Beitraegen, ohne eigene und ohne
  die von Startkonten. Ablehnung bringt keinen Meilenstein.
- Unterstuetzungsarbeit: Einwuerfe anderer, die die Person ausformuliert hat, und
  eigene Einwuerfe, die andere ausformuliert haben, je mit nicht gesperrtem Beitrag
  und ohne Startkonten auf der anderen Seite.

Weil nichts gespeichert wird, kann ein erreichter Meilenstein wieder verschwinden,
etwa wenn ein Beitrag gesperrt oder geloescht wird; das ist der Preis dafuer, dass es
keine Tabelle mit Meilensteinen und keine Frist dafuer gibt.

Ein Startkonto hat keine Meilensteine, ein Konto ohne geltende Art.-9-Einwilligung
auch nicht: Deren Wortlaut nennt die Meilenstein-Abzeichen als Zweck (#559). Gefragt
wird je Abruf, damit ein Widerruf sofort wirkt.
"""

import asyncio
from typing import Callable, List, Optional, Protocol, Set

from core.config import Settings
from domain.meilensteine import Meilenstein, Meilensteindaten, meilensteine_berechnen
from services.art9_einwilligung_service import get_art9_einwilligung_service
from services.punkte_service import NutzungsQuelle, SichtbareBeitraege


class MeilensteinQuellen(Protocol):
    def zustimmungen(self, content_ids: List, ausgenommen: Set[str]) -> int: ...

    def einwuerfe_ausformuliert_von(
        self, user_id: str, ausgenommen: Set[str]
    ) -> int: ...

    def eigene_einwuerfe_von_anderen_ausformuliert(
        self, user_id: str, ausgenommen: Set[str]
    ) -> int: ...


class MeilensteineService:
    def __init__(
        self,
        sichtbare_beitraege: SichtbareBeitraege,
        nutzung: NutzungsQuelle,
        stimmen_und_einwuerfe: MeilensteinQuellen,
        settings: Settings,
        eingewilligt: Optional[Callable[[str], bool]] = None,
    ):
        self._sichtbare_beitraege = sichtbare_beitraege
        self._nutzung = nutzung
        self._stimmen_und_einwuerfe = stimmen_und_einwuerfe
        self._settings = settings
        # Spaet geholt wie in PunkteService, damit Tests den Dienst ersetzen koennen.
        self._eingewilligt = eingewilligt or (
            lambda user_id: get_art9_einwilligung_service().eingewilligt(user_id)
        )

    async def meilensteine(self, user_id: str) -> List[Meilenstein]:
        """Alle Meilensteine mit Stand; leer fuer Startkonten und ohne Einwilligung."""
        if self._settings.ist_startkonto(user_id):
            return []
        if not await asyncio.to_thread(self._eingewilligt, user_id):
            return []

        beitraege = await self._sichtbare_beitraege(user_id)
        ids = [b.id for b in beitraege]
        startkonten = set(self._settings.startkonto_kennungen())
        # Die Repositories fragen PostgreSQL synchron ab: im Thread, nicht im Event-Loop.
        nutzung = sum(
            (
                await asyncio.to_thread(self._nutzung.get_nutzung_entdoppelt_batch, ids)
            ).values()
        )
        quelle = self._stimmen_und_einwuerfe
        zustimmungen = await asyncio.to_thread(
            quelle.zustimmungen, ids, {user_id} | startkonten
        )
        ausformuliert = await asyncio.to_thread(
            quelle.einwuerfe_ausformuliert_von, user_id, startkonten
        )
        eingeworfen = await asyncio.to_thread(
            quelle.eigene_einwuerfe_von_anderen_ausformuliert, user_id, startkonten
        )
        return meilensteine_berechnen(
            Meilensteindaten(
                nutzungen=nutzung,
                zustimmungen=zustimmungen,
                einwuerfe_ausformuliert=ausformuliert,
                eigene_einwuerfe_von_anderen_ausformuliert=eingeworfen,
            )
        )
