"""
Themen an Aussagen: von Hand zuordnen, lesen und als Testset exportieren.

Eine Aussage hat null bis zwei Themen aus der festen Liste (domain/themen.py).
Gespeichert wird je Zuordnung nur Aussage, Thema und Zuordnungsart, keine Person und
kein Zeitpunkt: Das Testset fuer spaetere Themenvorschlaege (#401) soll ohne
Personendaten exportierbar sein, und wer zugeordnet hat, braucht niemand.

Die Zuordnungsart unterscheidet die Zuordnungen von Hand von denen einer spaeteren
Automatik (Roadmap-Stufe 3); nur die von Hand taugen als Testset.
"""

import asyncio
import uuid
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Protocol, Tuple

from pydantic import ValidationError

from domain.models.content_origin import ContentOrigin
from domain.models.content_status import ContentStatus
from domain.models.statement import StatementDbEntry, angelegt_am
from domain.themen import NACH_SCHLUESSEL, THEMEN, Zuordnungsart, themen_pruefen
from services.content.statement_service import AussageNichtGefunden, StatementService

VON_HAND = Zuordnungsart.VON_HAND

_REIHENFOLGE = {t.schluessel: i for i, t in enumerate(THEMEN)}


class IAussageThemenRepository(Protocol):
    def setzen(
        self, statement_id: uuid.UUID, themen: List[str], zuordnungsart: Zuordnungsart
    ) -> None: ...

    def themen_von(
        self, statement_ids: Iterable[uuid.UUID]
    ) -> Dict[uuid.UUID, List[str]]: ...

    def zuordnungen(
        self, zuordnungsart: Zuordnungsart
    ) -> Dict[uuid.UUID, List[str]]: ...


@dataclass(frozen=True)
class ThemenZuordnung:
    """Eine Zeile des Testsets: bewusst ohne Autor, Kennung und Zeitpunkt."""

    statement_id: uuid.UUID
    text: str
    themen: List[str]
    zuordnungsart: Zuordnungsart


@dataclass(frozen=True)
class AussageMitThemen:
    statement_id: uuid.UUID
    text: str
    themen: Tuple[str, ...]
    # Ob ihre Zuordnung von Hand ins Testset geht (fuers_testset).
    im_testset: bool


def fuers_testset(aussage: StatementDbEntry) -> bool:
    """
    Ob die Zuordnungen einer Aussage ins Testset duerfen: nur sichtbare, und keine
    aus Suchanfragen, auch keine beantworteten. Deren Text ist, was eine Person
    eingetippt hat, und kann Persoenliches enthalten. In der App sehen Mitwirkende
    ihn ab der Schwelle von "Suchen ohne Treffer"; aus der App hinaus geht er nicht.
    """
    return (
        aussage.status == ContentStatus.VISIBLE
        and aussage.origin is not ContentOrigin.SEARCH_QUERY
    )


def _bekannt_und_geordnet(themen: Iterable[str]) -> List[str]:
    return sorted((t for t in themen if t in NACH_SCHLUESSEL), key=_REIHENFOLGE.get)


class AussageThemenService:
    def __init__(
        self,
        repository: IAussageThemenRepository,
        statement_service: StatementService,
    ):
        self._repository = repository
        self._statement_service = statement_service

    async def zuordnen(self, statement_id: uuid.UUID, themen: List[str]) -> List[str]:
        """
        Die Themen einer Aussage von Hand setzen; ersetzt die bisherigen, eine
        leere Liste entfernt alle.

        Raises:
            ThemaUngueltig: unbekanntes Thema oder mehr als zwei.
            AussageNichtGefunden: Die Aussage gibt es nicht, oder sie ist nicht
                sichtbar (gesperrt oder geloescht).
        """
        geprueft = themen_pruefen(themen)
        aussage = await self._aussage(statement_id)
        if aussage.status != ContentStatus.VISIBLE:
            raise AussageNichtGefunden(str(statement_id))
        self._repository.setzen(statement_id, geprueft, VON_HAND)
        return geprueft

    def themen_von(
        self, statement_ids: Iterable[uuid.UUID]
    ) -> Dict[uuid.UUID, List[str]]:
        """
        Die Themen je Aussage, in der Reihenfolge der Liste. Aussagen ohne Thema
        fehlen im Ergebnis; Schluessel, die nicht mehr in der Liste stehen, auch.
        """
        ergebnis = {}
        for statement_id, themen in self._repository.themen_von(
            list(statement_ids)
        ).items():
            bekannt = _bekannt_und_geordnet(themen)
            if bekannt:
                ergebnis[statement_id] = bekannt
        return ergebnis

    async def aussagen_zum_zuordnen(self) -> List[AussageMitThemen]:
        """
        Alle sichtbaren Aussagen ohne die unbeantworteten Suchanfragen
        (StatementService.kuratierte), mit ihren Themen, damit sich auch
        beantwortete Aussagen nachtraeglich zuordnen lassen. Zuerst die ohne
        Thema, darin die neuesten zuerst.
        """
        aussagen = await self._statement_service.kuratierte()
        themen = self.themen_von([a.id for a in aussagen])
        aussagen.sort(key=angelegt_am, reverse=True)
        aussagen.sort(key=lambda a: a.id in themen)
        return [
            AussageMitThemen(
                a.id, a.text, tuple(themen.get(a.id, ())), fuers_testset(a)
            )
            for a in aussagen
        ]

    async def testset(self) -> List[ThemenZuordnung]:
        """
        Alle Zuordnungen von Hand mit dem Text ihrer Aussage, als Testset fuer
        Themenvorschlaege, ohne Person und Zeitpunkt; welche Aussagen: fuers_testset.
        """
        zuordnungen = [
            (statement_id, bekannt)
            for statement_id, themen in self._repository.zuordnungen(VON_HAND).items()
            if (bekannt := _bekannt_und_geordnet(themen))
        ]
        aussagen = await asyncio.gather(
            *(self._aussage_oder_none(statement_id) for statement_id, _ in zuordnungen)
        )
        return [
            ThemenZuordnung(statement_id, aussage.text, bekannt, VON_HAND)
            for (statement_id, bekannt), aussage in zip(zuordnungen, aussagen)
            if aussage is not None and fuers_testset(aussage)
        ]

    async def _aussage_oder_none(
        self, statement_id: uuid.UUID
    ) -> Optional[StatementDbEntry]:
        try:
            return await self._aussage(statement_id)
        except AussageNichtGefunden:
            return None

    async def _aussage(self, statement_id: uuid.UUID):
        try:
            return await self._statement_service.get(statement_id)
        except ValidationError:
            # Nicht lesbar ist kaputt, nicht abwesend (wie StatementService._aussage_laden).
            raise
        except ValueError as fehler:
            raise AussageNichtGefunden(str(statement_id)) from fehler
