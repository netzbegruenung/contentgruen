"""
"Diese Woche oft genutzt" auf der Startseite (#364, docs/VISION.md "Trends").

Die Beitraege mit der meisten Nutzung der letzten sieben Tage. Gezaehlt wird nur
Nutzung durch andere: Die eigene Kopie erfasst der Zaehl-Endpunkt gar nicht erst
(api/v1/usage.py). Nutzung durch Startkonten zaehlt heute noch mit; das Merkmal
kommt mit #352, und dann gehoert der Filter in die Trend-Abfrage
(UsageTrackingRepository.get_trending_content), nicht hierher.

Bei zu wenig Nutzung gibt es keinen Bereich: Eine Liste mit einem einmal kopierten
Beitrag waere kein Trend, sondern ein Zufall.
"""

import logging
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)

FENSTER_STUNDEN = 7 * 24
"""Diese Woche: die letzten sieben Tage, nicht die Kalenderwoche."""

MINDEST_NUTZUNGEN = 2
"""So oft muss ein Beitrag in der Woche genutzt worden sein, um als oft genutzt zu gelten."""

MINDEST_BEITRAEGE = 3
"""Erreichen weniger Beitraege die Mindestnutzung, entfaellt der Bereich."""

ANZAHL = 5
"""So viele Beitraege zeigt der Bereich hoechstens (wie "Neueste Inhalte")."""

KANDIDATEN = 50
"""
So viele Eintraege holt die Trend-Abfrage. Mehr als ANZAHL, damit gesperrte und
geloeschte Beitraege Platz fuer die naechsten machen; 50 ist auch das Limit der
oeffentlichen Trend-Schnittstelle.
"""

BeitragLaden = Callable[[uuid.UUID], Awaitable[Optional[Dict[str, Any]]]]
"""Den sichtbaren Beitrag zu einer ID als Dict, oder None, wenn er nicht (mehr) sichtbar ist."""


def sichtbaren_beitrag_laden(settings, repository_factory, reference_service=None):
    """
    Der BeitragLaden gegen Qdrant: erst den Typ nachsehen, dann den Beitrag ueber
    das Repository seines Typs lesen, damit er alle Felder fuer die Karte hat.

    Gesperrt, geloescht oder nicht vorhanden meldet ``get`` als ValueError
    (base_repository.py); das heisst hier "nicht zeigen". Aussagen und Herkuenfte
    haben keine Nutzung, die hier ankaeme, und sind ohnehin keine Beitraege.

    Die Herkunft wird wie bei /content/recent um Link und Beschreibung ergaenzt,
    sonst zeigte die Karte nur eine ID.
    """
    from domain.content_registry import REGISTRY

    inhalte = repository_factory.create_content_repository(settings)

    async def laden(beitrag_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        try:
            eintrag = await inhalte.get(beitrag_id)
            spec = REGISTRY.get(eintrag.content_type)
            if spec is None:
                return None
            beitrag = await spec.create_repository(repository_factory, settings).get(
                beitrag_id
            )
        except ValueError:
            return None

        if reference_service is not None:
            await reference_service.herkunft_ergaenzen(beitrag)
        daten = beitrag.model_dump()
        daten["result_type"] = spec.content_type.value
        return daten

    return laden


class TrendAbfrage(Protocol):
    """Die Trend-Abfrage des UsageTrackingService: Beitraege nach Nutzung im Fenster."""

    def get_trending_content(
        self, limit: int = 10, hours: int = 24
    ) -> List[Dict[str, Any]]: ...


class OftGenutztService:
    def __init__(self, trend: TrendAbfrage, beitrag_laden: BeitragLaden):
        self._trend = trend
        self._beitrag_laden = beitrag_laden

    async def beitraege(self) -> List[Dict[str, Any]]:
        """
        Die oft genutzten Beitraege, meistgenutzte zuerst, je mit ``recent_uses``
        (Nutzungen in der Woche). Leer, wenn es zu wenige sind.
        """
        kandidaten = self._trend.get_trending_content(
            limit=KANDIDATEN, hours=FENSTER_STUNDEN
        )
        beitraege: List[Dict[str, Any]] = []
        for kandidat in kandidaten:
            if kandidat["recent_uses"] < MINDEST_NUTZUNGEN:
                # Die Trend-Abfrage sortiert absteigend; danach kommt keiner mehr.
                break
            beitrag = await self._beitrag_laden(uuid.UUID(kandidat["content_id"]))
            if beitrag is None:
                continue
            beitrag["recent_uses"] = kandidat["recent_uses"]
            beitraege.append(beitrag)
            if len(beitraege) == ANZAHL:
                break

        if len(beitraege) < MINDEST_BEITRAEGE:
            logger.debug(
                f"Oft genutzt: nur {len(beitraege)} Beitraege, Bereich entfaellt"
            )
            return []
        return beitraege
