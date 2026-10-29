"""
"Diese Woche oft genutzt" auf der Startseite (#364, docs/VISION.md "Trends").

Die Beitraege mit der meisten Nutzung der letzten sieben Tage. Gezaehlt wird nur
Nutzung verschiedener anderer Personen: Die eigene Kopie und die eines Startkontos
erfasst der Zaehl-Endpunkt gar nicht erst (api/v1/usage.py), und die
Nutzungsabfrage zaehlt je Person (Besucher: Sitzung), Beitrag und Tag nur die
erste Nutzung (UsageTrackingRepository.get_trending_content, #352).

Bei zu wenig Nutzung gibt es keinen Bereich: Eine Liste mit einem einmal kopierten
Beitrag zeigte nicht, was oft genutzt wird, sondern einen Zufall.
"""

import logging
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol

from pydantic import ValidationError

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
So viele Kandidaten holt die Nutzungsabfrage. Mehr als ANZAHL, damit gesperrte und
geloeschte Beitraege Platz fuer die naechsten machen; 50 ist auch das Limit von
/api/v1/usage/trending.
"""

BeitragLaden = Callable[[uuid.UUID], Awaitable[Optional[Dict[str, Any]]]]
"""Den sichtbaren Beitrag zu einer ID als Dict, oder None, wenn er nicht (mehr) sichtbar ist."""


def sichtbaren_beitrag_laden(settings, repository_factory, reference_service):
    """
    Der BeitragLaden gegen Qdrant: erst den Typ nachsehen, dann den Beitrag ueber
    das Repository seines Typs lesen, damit er alle Felder fuer die Karte hat.

    Gesperrt, geloescht oder nicht vorhanden meldet ``get`` als ValueError
    (base_repository.py); das heisst hier "nicht zeigen". Aussagen und Herkuenfte
    haben keine Nutzung, die hier ankaeme, und sind ohnehin keine Beitraege. Ein
    Datensatz, der nicht validiert, fehlt ebenfalls, wird aber als Fehler geloggt:
    Er ist kaputt, nicht abwesend (wie beitrag_laden in api/v1/usage.py).

    Die Herkunft wird wie bei /content/recent um Link und Beschreibung ergaenzt,
    sonst zeigte die Karte nur eine ID. ``result_type`` ist der Wert des
    ContentType (``generic_text``); das Frontend kennt beide Schreibweisen.
    """
    from domain.content_registry import REGISTRY

    alle_typen = repository_factory.create_content_repository(settings)

    async def laden(beitrag_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        try:
            typ = (await alle_typen.get(beitrag_id)).content_type
            spec = REGISTRY.get(typ)
            if spec is None:
                return None
            beitrag = await spec.create_repository(repository_factory, settings).get(
                beitrag_id
            )
        except ValidationError as fehler:
            # Vor ValueError, denn Pydantics ValidationError ist einer.
            logger.error(f"Content {beitrag_id} is not readable: {fehler}")
            return None
        except ValueError:
            return None

        await reference_service.herkunft_ergaenzen(beitrag)
        daten = beitrag.model_dump()
        daten["result_type"] = spec.content_type.value
        return daten

    return laden


class NutzungsAbfrage(Protocol):
    """Die Abfrage des UsageTrackingService: Beitraege nach Nutzung im Zeitfenster."""

    def get_trending_content(
        self, limit: int = 10, hours: int = 24, nur_entdoppelt: bool = False
    ) -> List[Dict[str, Any]]: ...


class OftGenutztService:
    def __init__(self, nutzung: NutzungsAbfrage, beitrag_laden: BeitragLaden):
        self._nutzung = nutzung
        self._beitrag_laden = beitrag_laden

    async def beitraege(self) -> List[Dict[str, Any]]:
        """
        Die oft genutzten Beitraege, meistgenutzte zuerst, je mit ``recent_uses``
        (Nutzungen in der Woche). Leer, wenn es zu wenige sind.
        """
        kandidaten = self._nutzung.get_trending_content(
            limit=KANDIDATEN, hours=FENSTER_STUNDEN, nur_entdoppelt=True
        )
        beitraege: List[Dict[str, Any]] = []
        for kandidat in kandidaten:
            if kandidat["recent_uses"] < MINDEST_NUTZUNGEN:
                # Die Nutzungsabfrage sortiert absteigend; danach kommt keiner mehr.
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
