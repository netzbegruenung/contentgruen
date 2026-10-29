"""
Muster-Hinweise fuer Admins (ADR 0004, GLOSSARY.md "Muster-Hinweis", #352).

Ein Muster-Hinweis nennt zwei Konten, die sich gegenseitig nutzen: Am selben Tag hat
jedes einen Beitrag des anderen genutzt. Er ist nur ein Hinweis fuer Admins; keine
Automatik zieht Punkte ab oder sperrt jemanden.

Erkannt wird nur innerhalb eines Tages. Wer welchen Beitrag genutzt hat, steht
nirgends: Fuer jede Nutzung zwischen zwei Konten merkt sich der Dienst bis zum
Tagesende einen Paar-Pruefwert (services/entdoppelung.py). Erst wenn auch der
Pruefwert der Gegenrichtung da ist, entsteht eine Zeile mit beiden Kennungen. Nutzung
durch Besucher hat kein Konto und zaehlt hier nicht.

Fristen, angewendet von loeschen_im_takt, einem eigenen Hintergrund-Task aus main.py:
- Pruefwerte (nutzung_heute) gelten nur ihren Tag; der Lauf nach Mitternacht (UTC)
  verwirft alle vergangener Tage, auch die der entdoppelten Nutzung.
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
from repositories.usage_tracking_repository import UsageTrackingRepository
from services.entdoppelung import ANONYM, paar_pruefwert
from utils.utc_tag import heute_utc, sekunden_bis_mitternacht

logger = get_logger(__name__)

MUSTER_FRIST_TAGE = 56
"""Acht Wochen nach dem letzten auffaelligen Tag."""

ANZAHL = 50
"""So viele Hinweise zeigt das Admin-Dashboard hoechstens."""

LOESCH_TAKT_SEKUNDEN = 24 * 60 * 60


class MusterHinweiseService:
    def __init__(
        self,
        repository: MusterHinweisRepository,
        nutzung: UsageTrackingRepository,
    ):
        self._repository = repository
        self._nutzung = nutzung

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
        hin = paar_pruefwert(nutzende, autor, moment)
        rueck = paar_pruefwert(autor, nutzende, moment)
        self._repository.nutzung_merken(
            hin, rueck, nutzende, autor, moment.astimezone(timezone.utc).date()
        )

    def hinweise(self) -> List[MusterHinweis]:
        return self._repository.hinweise(ANZAHL)

    def fristen_anwenden(self, heute: Optional[date] = None) -> None:
        heute = heute or heute_utc()
        verworfen = self._nutzung.vergangene_tage_verwerfen(heute)
        geloescht = self._repository.loeschen_vor(
            heute - timedelta(days=MUSTER_FRIST_TAGE)
        )
        logger.info(
            f"Discarded {verworfen} check values of past days, "
            f"deleted {geloescht} pattern notes past their Loeschfrist"
        )


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
