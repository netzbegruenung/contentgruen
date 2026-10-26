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

from services.suchen_ohne_treffer_service import SuchenOhneTrefferService

AUSSAGE = uuid.UUID("11111111-1111-1111-1111-111111111111")
ANDERE = uuid.UUID("22222222-2222-2222-2222-222222222222")
GELOESCHT = uuid.UUID("33333333-3333-3333-3333-333333333333")

# Ein Mittwoch; die Woche beginnt am Montag, dem 2026-10-26.
MITTWOCH = date(2026, 10, 28)
MONTAG = date(2026, 10, 26)


class FakeRepository:
    def __init__(self, haeufigste=None):
        self.gezaehlt = []
        self.abfragen = []
        self._haeufigste = haeufigste or []

    def zaehlen(self, statement_id, woche, aelter_als):
        self.gezaehlt.append((statement_id, woche, aelter_als))

    def haeufigste(self, seit_woche, mindestanzahl, limit):
        self.abfragen.append((seit_woche, mindestanzahl, limit))
        return self._haeufigste


def _statement_service(texte):
    service = Mock()

    async def get(statement_id):
        if statement_id not in texte:
            raise ValueError("nicht gefunden")
        return SimpleNamespace(id=statement_id, text=texte[statement_id])

    service.get = AsyncMock(side_effect=get)
    return service


class TestErfassen:
    def test_erfassen_ohne_treffer_zaehlt_in_der_woche_ab_montag(self):
        repo = FakeRepository()
        service = SuchenOhneTrefferService(repo)

        service.erfassen(AUSSAGE, treffer=0, heute=MITTWOCH)

        assert [(s, w) for s, w, _ in repo.gezaehlt] == [(AUSSAGE, MONTAG)]

    def test_erfassen_raeumt_wochen_ausserhalb_der_aufbewahrung_weg(self):
        repo = FakeRepository()
        service = SuchenOhneTrefferService(repo)

        service.erfassen(AUSSAGE, treffer=0, heute=MITTWOCH)

        # Acht Wochen Aufbewahrung samt laufender: die Montage 26.10., 19.10.,
        # 12.10., 05.10., 28.09., 21.09., 14.09. und 07.09. bleiben.
        assert repo.gezaehlt[0][2] == date(2026, 9, 7)

    def test_erfassen_mit_treffern_zaehlt_nicht(self):
        repo = FakeRepository()
        service = SuchenOhneTrefferService(repo)

        service.erfassen(AUSSAGE, treffer=1, heute=MITTWOCH)

        assert repo.gezaehlt == []

    def test_erfassen_ohne_aussage_zaehlt_nicht(self):
        """Ohne Aussage (Rate-Limit beim Anlegen) gibt es nichts, woran man zaehlt."""
        repo = FakeRepository()
        service = SuchenOhneTrefferService(repo)

        service.erfassen(None, treffer=0, heute=MITTWOCH)

        assert repo.gezaehlt == []


class TestHaeufigste:
    @pytest.mark.asyncio
    async def test_haeufigste_liefert_text_und_anzahl_der_aussage(self):
        repo = FakeRepository(haeufigste=[(AUSSAGE, 7), (ANDERE, 3)])
        service = SuchenOhneTrefferService(repo)
        statements = _statement_service(
            {AUSSAGE: "Windräder töten Vögel", ANDERE: "Wärmepumpe im Altbau"}
        )

        ergebnis = await service.haeufigste(statements, wochen=4, heute=MITTWOCH)

        assert [(e.statement_id, e.text, e.anzahl) for e in ergebnis] == [
            (AUSSAGE, "Windräder töten Vögel", 7),
            (ANDERE, "Wärmepumpe im Altbau", 3),
        ]

    @pytest.mark.asyncio
    async def test_haeufigste_fragt_die_laufende_und_drei_vorwochen_ab(self):
        repo = FakeRepository()
        service = SuchenOhneTrefferService(repo)

        await service.haeufigste(_statement_service({}), wochen=4, heute=MITTWOCH)

        seit_woche, mindestanzahl, limit = repo.abfragen[0]
        assert seit_woche == date(2026, 10, 5)
        assert mindestanzahl == 2
        assert limit == 20

    @pytest.mark.asyncio
    async def test_haeufigste_laesst_nicht_mehr_vorhandene_aussagen_weg(self):
        repo = FakeRepository(haeufigste=[(GELOESCHT, 9), (AUSSAGE, 4)])
        service = SuchenOhneTrefferService(repo)
        statements = _statement_service({AUSSAGE: "Windräder töten Vögel"})

        ergebnis = await service.haeufigste(statements, wochen=4, heute=MITTWOCH)

        assert [e.statement_id for e in ergebnis] == [AUSSAGE]
