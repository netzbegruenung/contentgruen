"""
"Hier fehlt eine Antwort": die unbeantworteten Aussagen fuer Mitwirkende.

Unbeantwortet ist nach Glossar eine Aussage ohne Kommentar oder eine, nach der
mindestens zwei Personen ohne Treffer gesucht haben und die noch keinen Kommentar
hat. Die zweite Quelle ist dieselbe wie die Admin-Kennzahl
(SuchenOhneTrefferService.haeufigste): dieselbe Schwelle, nur sichtbare Aussagen.
Stammt eine davon aus einer Suchanfrage, ist ihr Text der Suchtext der ersten
suchenden Person (wie in der Admin-Kennzahl). Mitwirkende sehen dazu, wie viele
Personen ohne Treffer danach gesucht haben, gezaehlt wie in der Kennzahl
(Tagespseudonyme, ueber die Wochen summiert), damit Hotspots sichtbar werden; die
Zahl der Suchen sehen nur Admins.

Anders als die Kennzahl laesst die Liste eine Aussage weg, sobald sie einen
sichtbaren Kommentar hat (StatementService.mit_kommentar): Die Suchen ohne Treffer
zaehlen ueber Wochen weiter, und wer geantwortet hat, soll die Luecke nicht weiter
offen sehen. Ein gesperrter oder geloeschter Kommentar zaehlt nicht. Gefiltert wird
vor der Begrenzung, mit oder ohne Thema aus KANDIDATEN_MIT_FILTER Aussagen der
Kennzahl, damit beantwortete Hotspots unbeantwortete nicht unter die Grenze druecken;
ihr Anteil waechst mit den Wochen, ein knapper Puffer reichte nicht lange. Scheitert
die Pruefung auf Kommentare, bleibt die Liste ungefiltert (Warnung im Log): Sie ist
Beiwerk und soll nicht ganz ausfallen.

Sortiert nach Bedarf: zuerst die Aussagen mit Suchen ohne Treffer, absteigend nach
der Zahl der Personen (bei gleicher Zahl wie in der Kennzahl), dann die uebrigen
ohne Kommentar, neueste zuerst. Nach Personen statt nach Suchen, damit die
Reihenfolge zur gezeigten Zahl passt und die Zahl der Suchen nicht verraet. Aussagen aus
Suchanfragen, die die Schwelle nicht erreichen und auf die niemand geantwortet hat,
erscheinen nicht: Sie sind die Suchanfrage einer einzelnen Person
(StatementRepository.ohne_kommentar). Eine unbeantwortete Suchanfrage ueber der
Schwelle erscheint erst, wenn ein Admin sie freigegeben hat (Vormoderation,
SuchenOhneTrefferService.sichtbar_fuer_alle); andere Aussagen mit Suchen ohne
Treffer betrifft das nicht.

Jede Aussage traegt ihre Themen (AussageThemenService). Mit einem Thema als Filter
bleiben nur die Aussagen mit diesem Thema, in derselben Reihenfolge; gefiltert wird
vor der Begrenzung, damit die Liste nicht durch Aussagen anderer Themen leer bleibt.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import List, Optional, Tuple

from domain.models.statement import angelegt_am
from services.aussage_themen_service import AussageThemenService
from services.content.statement_service import StatementService
from services.suchen_ohne_treffer_service import (
    WOCHEN_STANDARD,
    SuchenOhneTrefferService,
)

logger = logging.getLogger(__name__)

LIMIT_STANDARD = 50

# Wie viele Aussagen mit Suchen ohne Treffer gelesen werden: Thema und beantwortete
# Aussagen fallen erst danach heraus, und mit nur LIMIT_STANDARD fehlten Aussagen,
# die weiter hinten stehen.
KANDIDATEN_MIT_FILTER = 500


@dataclass(frozen=True)
class UnbeantworteteAussage:
    statement_id: uuid.UUID
    text: str
    # Personen, die im Zeitraum ohne Treffer danach gesucht haben; 0 bei einer
    # Aussage, die nur wegen des fehlenden Kommentars auf der Liste steht.
    personen_ohne_treffer: int
    # Schluessel aus domain/themen.py, in der Reihenfolge der Liste.
    themen: Tuple[str, ...] = ()


class UnbeantworteteAussagenService:
    def __init__(
        self,
        statement_service: StatementService,
        suchen_ohne_treffer: SuchenOhneTrefferService,
        themen: AussageThemenService,
    ):
        self._statement_service = statement_service
        self._suchen_ohne_treffer = suchen_ohne_treffer
        self._themen = themen

    async def liste(
        self,
        limit: int = LIMIT_STANDARD,
        thema: Optional[str] = None,
        mit_themen: bool = True,
    ) -> List[UnbeantworteteAussage]:
        """
        ``mit_themen=False`` (nur ohne Thema-Filter): ohne Nachschlagen der Themen,
        etwa wenn nur gezaehlt wird ("Seit deinem letzten Besuch"); die Eintraege
        tragen dann keine Themen, Auswahl und Reihenfolge bleiben gleich.
        """
        # Verborgene Suchanfragen (Vormoderation) fallen schon in haeufigste vor der
        # Begrenzung heraus, beantwortete Aussagen gleich danach.
        gesucht = await self._suchen_ohne_treffer.haeufigste(
            wochen=WOCHEN_STANDARD,
            limit=KANDIDATEN_MIT_FILTER,
            ohne_verborgene=True,
        )
        try:
            beantwortet = await self._statement_service.mit_kommentar(
                [g.statement_id for g in gesucht]
            )
        except Exception as fehler:
            # Die Liste ist Beiwerk: lieber ungefiltert als gar nicht.
            logger.warning(
                f"Hier fehlt eine Antwort: Pruefung auf Kommentare gescheitert "
                f"({type(fehler).__name__}), Liste bleibt ungefiltert"
            )
            beantwortet = set()
        gesucht = sorted(
            (g for g in gesucht if g.statement_id not in beantwortet),
            key=lambda g: g.personen,
            reverse=True,
        )
        kandidaten = [(g.statement_id, g.text, g.personen) for g in gesucht]
        schon_drin = {statement_id for statement_id, _, _ in kandidaten}

        ohne_kommentar = await self._statement_service.ohne_kommentar()
        ohne_kommentar.sort(key=angelegt_am, reverse=True)
        kandidaten += [
            (aussage.id, aussage.text, 0)
            for aussage in ohne_kommentar
            if aussage.id not in schon_drin
        ]

        if thema is None:
            # Ohne Filter zaehlen nur die ersten; nur deren Themen nachschlagen.
            kandidaten = kandidaten[:limit]
        themen = (
            self._themen.themen_von([s for s, _, _ in kandidaten])
            if mit_themen or thema is not None
            else {}
        )
        ergebnis = [
            UnbeantworteteAussage(
                statement_id, text, personen, tuple(themen.get(statement_id, ()))
            )
            for statement_id, text, personen in kandidaten
            if thema is None or thema in themen.get(statement_id, ())
        ]
        return ergebnis[:limit]
