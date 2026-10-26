"""
Unit-Tests fuer die Kennzahl "Suchen ohne Treffer".

Das Repository ist durch eine Fake-Klasse ersetzt, die Aussagen kommen aus einem
gemockten StatementService. Geprueft wird, wann eine Suche zaehlt, in welche Woche
sie faellt und was Admins am Ende sehen.
"""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from domain.models.content_status import ContentStatus
from services.suchen_ohne_treffer_service import (
    SuchenOhneTrefferService,
    aufbewahrungsgrenze,
)

pytestmark = pytest.mark.unit

AUSSAGE = uuid.UUID("11111111-1111-1111-1111-111111111111")
ANDERE = uuid.UUID("22222222-2222-2222-2222-222222222222")
GELOESCHT = uuid.UUID("33333333-3333-3333-3333-333333333333")
GESPERRT = uuid.UUID("44444444-4444-4444-4444-444444444444")

# Ein Mittwoch; die Woche beginnt am Montag, dem 2026-10-26.
MITTWOCH = date(2026, 10, 28)
MONTAG = date(2026, 10, 26)


class FakeRepository:
    def __init__(self, haeufigste=None):
        self.gezaehlt = []
        self.abfragen = []
        self._haeufigste = haeufigste or []

    def zaehlen(self, statement_id, woche):
        self.gezaehlt.append((statement_id, woche))

    def haeufigste(self, seit_woche, mindestanzahl, limit):
        self.abfragen.append((seit_woche, mindestanzahl, limit))
        return self._haeufigste


def _statement_service(aussagen):
    """aussagen: ID -> (Text, Status); fehlende IDs gibt es nicht."""
    service = Mock()

    async def get(statement_id):
        if statement_id not in aussagen:
            raise ValueError("nicht gefunden")
        text, status = aussagen[statement_id]
        return SimpleNamespace(id=statement_id, text=text, status=status)

    service.get = AsyncMock(side_effect=get)
    return service


def _service(repo, aussagen=None):
    return SuchenOhneTrefferService(repo, _statement_service(aussagen or {}))


FREI = ContentStatus.RELEASED_INTERNAL


class TestErfassen:
    def test_erfassen_ohne_treffer_zaehlt_in_der_woche_ab_montag(self):
        repo = FakeRepository()

        _service(repo).erfassen(AUSSAGE, treffer=0, heute=MITTWOCH)

        assert repo.gezaehlt == [(AUSSAGE, MONTAG)]

    def test_erfassen_mit_treffern_zaehlt_nicht(self):
        repo = FakeRepository()

        _service(repo).erfassen(AUSSAGE, treffer=1, heute=MITTWOCH)

        assert repo.gezaehlt == []

    def test_erfassen_ohne_aussage_zaehlt_nicht(self):
        """Ohne Aussage (Rate-Limit beim Anlegen) gibt es nichts, woran man zaehlt."""
        repo = FakeRepository()

        _service(repo).erfassen(None, treffer=0, heute=MITTWOCH)

        assert repo.gezaehlt == []


class TestAufbewahrung:
    def test_aufbewahrungsgrenze_behaelt_acht_wochen_samt_laufender(self):
        # Es bleiben die Montage 26.10., 19.10., 12.10., 05.10., 28.09., 21.09.,
        # 14.09. und 07.09.
        assert aufbewahrungsgrenze(MITTWOCH) == date(2026, 9, 7)


class TestHaeufigste:
    @pytest.mark.asyncio
    async def test_haeufigste_liefert_text_und_anzahl_der_aussage(self):
        repo = FakeRepository(haeufigste=[(AUSSAGE, 7), (ANDERE, 3)])
        service = _service(
            repo,
            {
                AUSSAGE: ("Windräder töten Vögel", FREI),
                ANDERE: ("Wärmepumpe im Altbau", FREI),
            },
        )

        ergebnis = await service.haeufigste(wochen=4, heute=MITTWOCH)

        assert [(e.statement_id, e.text, e.anzahl) for e in ergebnis] == [
            (AUSSAGE, "Windräder töten Vögel", 7),
            (ANDERE, "Wärmepumpe im Altbau", 3),
        ]

    @pytest.mark.asyncio
    async def test_haeufigste_fragt_die_laufende_und_drei_vorwochen_ab(self):
        repo = FakeRepository()

        await _service(repo).haeufigste(wochen=4, heute=MITTWOCH)

        seit_woche, mindestanzahl, limit = repo.abfragen[0]
        assert seit_woche == date(2026, 10, 5)
        assert mindestanzahl == 2
        assert limit == 20

    @pytest.mark.asyncio
    async def test_haeufigste_laesst_nicht_mehr_vorhandene_aussagen_weg(self):
        repo = FakeRepository(haeufigste=[(GELOESCHT, 9), (AUSSAGE, 4)])
        service = _service(repo, {AUSSAGE: ("Windräder töten Vögel", FREI)})

        ergebnis = await service.haeufigste(wochen=4, heute=MITTWOCH)

        assert [e.statement_id for e in ergebnis] == [AUSSAGE]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", [ContentStatus.BLOCKED, ContentStatus.DUPLICATE])
    async def test_haeufigste_zeigt_keine_gesperrten_oder_dubletten(self, status):
        repo = FakeRepository(haeufigste=[(GESPERRT, 9), (AUSSAGE, 4)])
        service = _service(
            repo,
            {
                GESPERRT: ("enthält einen Namen", status),
                AUSSAGE: ("Windräder töten Vögel", FREI),
            },
        )

        ergebnis = await service.haeufigste(wochen=4, heute=MITTWOCH)

        assert [e.statement_id for e in ergebnis] == [AUSSAGE]
