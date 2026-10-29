"""
Unit-Tests fuer die Themen an Aussagen: von Hand zuordnen, lesen und als Testset
exportieren.

Das Repository ist durch einen Speicher im Arbeitsspeicher ersetzt (gleiche
Schnittstelle wie AussageThemenRepository), die Aussagen durch einen gemockten
StatementService. Dass das Repository in PostgreSQL dasselbe tut, prueft
tests/integration/test_aussage_themen.py.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from domain.models.content_status import ContentStatus
from domain.themen import ThemaUngueltig
from services.aussage_themen_service import (
    VON_HAND,
    AussageThemenService,
    ThemenZuordnung,
)
from services.content.statement_service import AussageNichtGefunden, StatementService

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

A = uuid.UUID("11111111-1111-1111-1111-111111111111")
B = uuid.UUID("22222222-2222-2222-2222-222222222222")
C = uuid.UUID("33333333-3333-3333-3333-333333333333")


class SpeicherRepository:
    def __init__(self):
        self.zeilen = {}

    def setzen(self, statement_id, themen, quelle):
        self.zeilen[statement_id] = [(t, quelle) for t in themen]

    def themen_von(self, statement_ids):
        return {
            i: [t for t, _ in self.zeilen[i]]
            for i in statement_ids
            if self.zeilen.get(i)
        }

    def zuordnungen(self, quelle):
        return {
            i: [t for t, q in zeilen if q == quelle]
            for i, zeilen in self.zeilen.items()
            if any(q == quelle for _, q in zeilen)
        }


def _aussage(statement_id, text, status=ContentStatus.VISIBLE, **mehr):
    return SimpleNamespace(
        id=statement_id, text=text, status=status, original_author="kennung", **mehr
    )


def _service(aussagen=(), repository=None):
    nach_id = {a.id: a for a in aussagen}

    async def holen(statement_id):
        if statement_id not in nach_id:
            raise AussageNichtGefunden(str(statement_id))
        return nach_id[statement_id]

    statement_service = Mock(spec=StatementService)
    statement_service.get = AsyncMock(side_effect=holen)
    statement_service.kuratierte = AsyncMock(return_value=list(aussagen))
    repository = repository or SpeicherRepository()
    return AussageThemenService(repository, statement_service), repository


async def test_zuordnen_speichert_themen_von_hand():
    service, repository = _service([_aussage(A, "Windräder töten Vögel")])

    themen = await service.zuordnen(A, ["natur-umwelt", "energie-heizen"])

    assert themen == ["natur-umwelt", "energie-heizen"]
    assert repository.zeilen[A] == [
        ("natur-umwelt", VON_HAND),
        ("energie-heizen", VON_HAND),
    ]


async def test_zuordnen_ersetzt_die_bisherigen_themen():
    service, _ = _service([_aussage(A, "Windräder töten Vögel")])
    await service.zuordnen(A, ["natur-umwelt", "energie-heizen"])

    await service.zuordnen(A, ["klima"])

    assert service.themen_von([A]) == {A: ["klima"]}


async def test_zuordnen_mit_leerer_liste_entfernt_alle_themen():
    service, _ = _service([_aussage(A, "Windräder töten Vögel")])
    await service.zuordnen(A, ["klima"])

    await service.zuordnen(A, [])

    assert service.themen_von([A]) == {}


async def test_zuordnen_weist_unbekannte_und_zu_viele_themen_ab():
    service, repository = _service([_aussage(A, "Windräder töten Vögel")])

    with pytest.raises(ThemaUngueltig):
        await service.zuordnen(A, ["windkraft"])
    with pytest.raises(ThemaUngueltig):
        await service.zuordnen(A, ["klima", "verkehr", "europa"])
    assert repository.zeilen == {}


async def test_zuordnen_zu_einer_unbekannten_aussage_scheitert():
    service, repository = _service([])

    with pytest.raises(AussageNichtGefunden):
        await service.zuordnen(A, ["klima"])
    assert repository.zeilen == {}


async def test_themen_von_blendet_schluessel_aus_die_nicht_mehr_in_der_liste_stehen():
    repository = SpeicherRepository()
    repository.setzen(A, ["gestrichen", "klima"], VON_HAND)
    service, _ = _service([], repository)

    assert service.themen_von([A, B]) == {A: ["klima"]}


async def test_themen_von_ordnet_in_der_reihenfolge_der_liste():
    repository = SpeicherRepository()
    repository.setzen(A, ["verkehr", "klima"], VON_HAND)
    service, _ = _service([], repository)

    assert service.themen_von([A]) == {A: ["klima", "verkehr"]}


async def test_testset_enthaelt_text_und_themen_aber_keine_person():
    service, _ = _service(
        [
            _aussage(A, "Windräder töten Vögel"),
            _aussage(B, "Tempolimit bringt nichts"),
        ]
    )
    await service.zuordnen(A, ["natur-umwelt"])
    await service.zuordnen(B, ["verkehr", "klima"])

    testset = await service.testset()

    assert sorted(testset, key=lambda z: z.text) == [
        ThemenZuordnung(B, "Tempolimit bringt nichts", ["klima", "verkehr"], VON_HAND),
        ThemenZuordnung(A, "Windräder töten Vögel", ["natur-umwelt"], VON_HAND),
    ]
    assert set(ThemenZuordnung.__dataclass_fields__) == {
        "statement_id",
        "text",
        "themen",
        "quelle",
    }


async def test_testset_laesst_gesperrte_und_verschwundene_aussagen_weg():
    repository = SpeicherRepository()
    repository.setzen(A, ["klima"], VON_HAND)
    repository.setzen(B, ["klima"], VON_HAND)
    service, _ = _service(
        [_aussage(A, "Gesperrt", status=ContentStatus.BLOCKED)], repository
    )

    assert await service.testset() == []


async def test_aussagen_zum_zuordnen_zuerst_ohne_thema_dann_neueste():
    def am(tag):
        return datetime(2026, 10, tag, tzinfo=timezone.utc)

    service, _ = _service(
        [
            _aussage(A, "Alt, ohne Thema", created=am(1)),
            _aussage(B, "Neu, mit Thema", created=am(20)),
            _aussage(C, "Neu, ohne Thema", created=am(10)),
        ]
    )
    await service.zuordnen(B, ["klima"])

    liste = await service.aussagen_zum_zuordnen()

    assert [(a.statement_id, a.text, a.themen) for a in liste] == [
        (C, "Neu, ohne Thema", ()),
        (A, "Alt, ohne Thema", ()),
        (B, "Neu, mit Thema", ("klima",)),
    ]
