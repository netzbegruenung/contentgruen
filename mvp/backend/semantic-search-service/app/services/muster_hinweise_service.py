"""
Muster-Hinweise fuer Admins (ADR 0004, GLOSSARY.md "Muster-Hinweis", #352).

Ein Muster-Hinweis nennt zwei Konten, die sich gegenseitig nutzen: Innerhalb von
MUSTER_FENSTER_TAGE (sieben) Tagen hat jedes einen Beitrag des anderen genutzt. Er
ist nur ein Hinweis fuer Admins; keine Automatik zieht Punkte ab oder sperrt jemanden.

Wer welchen Beitrag genutzt hat, steht nirgends: Fuer jede Richtung zwischen zwei
Konten merkt sich der Dienst einen Paar-Pruefwert mit dem letzten Tag dieser Richtung
(services/entdoppelung.py, Tabelle muster_pruefwerte). Erst wenn auch der Pruefwert
der Gegenrichtung im Fenster liegt, entsteht eine Zeile mit beiden Kennungen. Nutzung
durch Besucher hat kein Konto und zaehlt hier nicht.

Fristen, angewendet von loeschen_im_takt, einem eigenen Hintergrund-Task aus main.py
(die Pruefwerte der entdoppelten Nutzung verwirft ein eigener, services/entdoppelung.py):
- Paar-Pruefwerte bleiben MUSTER_FENSTER_TAGE: der Lauf verwirft alle, deren letzter
  Tag davor liegt.
- Muster-Hinweise bleiben MUSTER_FRIST_TAGE nach dem letzten auffaelligen Tag (DSFA
  zu #374: 8 Wochen), dann gehen sie. Wird ein Konto geloescht, gehen seine Hinweise
  mit (mvp/scripts/manual/person_loeschen.sql).

Hinweise entstehen nur mit eingeschalteten Punkten (``punkte_aktiv``, geprueft im
Zaehl-Endpunkt api/v1/usage.py): Sie schuetzen die Punkte und haben ohne sie keinen
Zweck.
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from core.logging import get_logger
from repositories.muster_hinweis_repository import (
    MusterHinweis,
    MusterHinweisRepository,
)
from services.entdoppelung import ANONYM, paar_pruefwert
from utils.utc_tag import heute_utc, sekunden_bis_mitternacht

logger = get_logger(__name__)

MUSTER_FENSTER_TAGE = 7
"""So viele Tage (der heutige eingeschlossen) duerfen zwischen A->B und B->A liegen."""

MUSTER_FRIST_TAGE = 56
"""Acht Wochen nach dem letzten auffaelligen Tag."""

ANZAHL = 50
"""So viele Hinweise zeigt das Admin-Dashboard hoechstens."""

LOESCH_TAKT_SEKUNDEN = 24 * 60 * 60


class MusterHinweiseService:
    def __init__(self, repository: MusterHinweisRepository):
        self._repository = repository

    def nutzung_melden(
        self,
        nutzende: Optional[str],
        autor: Optional[str],
        moment: Optional[datetime] = None,
    ) -> None:
        """Eine Nutzung eines Beitrags von ``autor`` durch das Konto ``nutzende``."""
        if not nutzende or not autor or ANONYM in (nutzende, autor):
            return
        if nutzende == autor:
            return
        moment = moment or datetime.now(timezone.utc)
        tag = moment.astimezone(timezone.utc).date()
        self._repository.nutzung_merken(
            paar_pruefwert(nutzende, autor),
            paar_pruefwert(autor, nutzende),
            nutzende,
            autor,
            tag,
            fenster_ab=_fenster_ab(tag),
        )

    def hinweise(self) -> List[MusterHinweis]:
        return self._repository.hinweise(ANZAHL)

    def fristen_anwenden(self, heute: Optional[date] = None) -> None:
        heute = heute or heute_utc()
        paare = self._repository.paare_verwerfen_vor(_fenster_ab(heute))
        geloescht = self._repository.loeschen_vor(
            heute - timedelta(days=MUSTER_FRIST_TAGE)
        )
        logger.info(
            f"Discarded {paare} pair check values past the window, "
            f"deleted {geloescht} pattern notes past their Loeschfrist"
        )


def _fenster_ab(tag: date) -> date:
    """Der erste Tag des Fensters, das an ``tag`` endet."""
    return tag - timedelta(days=MUSTER_FENSTER_TAGE - 1)


async def loeschen_im_takt(
    service: MusterHinweiseService, takt_sekunden: float = LOESCH_TAKT_SEKUNDEN
) -> None:
    """
    Hintergrund-Task: wendet die Fristen sofort und dann taeglich an, spaetestens
    aber um Mitternacht (UTC), bis er abgebrochen wird.
    """
    while True:
        try:
            await asyncio.to_thread(service.fristen_anwenden)
        except Exception as e:
            logger.error(f"Error applying pattern note retention: {e}", exc_info=True)
        await asyncio.sleep(min(takt_sekunden, sekunden_bis_mitternacht() + 1))
