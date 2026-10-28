"""
Unit-Tests fuer "Hier fehlt eine Antwort": welche Aussagen als unbeantwortet gelten
und in welcher Reihenfolge Mitwirkende sie sehen.

Die beiden Quellen sind ersetzt: Aussagen ohne Kommentar kommen aus einem gemockten
StatementService, Suchen ohne Treffer aus einem gemockten SuchenOhneTrefferService.
Welche Aussagen Qdrant als "ohne Kommentar" liefert, prueft der Integrationstest.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from services.content.statement_service import StatementService
from services.suchen_ohne_treffer_service import (
    SucheOhneTreffer,
    SuchenOhneTrefferService,
)
from services.unbeantwortete_aussagen_service import (
    UnbeantworteteAussage,
    UnbeantworteteAussagenService,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

A = uuid.UUID("11111111-1111-1111-1111-111111111111")
B = uuid.UUID("22222222-2222-2222-2222-222222222222")
C = uuid.UUID("33333333-3333-3333-3333-333333333333")
D = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _aussage(statement_id, text, tag):
    return SimpleNamespace(
        id=statement_id,
        text=text,
        created=datetime(2026, 10, tag, tzinfo=timezone.utc),
    )


def _service(ohne_kommentar=(), gesucht=()):
    statement_service = Mock(spec=StatementService)
    statement_service.ohne_kommentar = AsyncMock(return_value=list(ohne_kommentar))
    suchen = Mock(spec=SuchenOhneTrefferService)
    suchen.haeufigste = AsyncMock(return_value=list(gesucht))
    return UnbeantworteteAussagenService(statement_service, suchen)


async def test_liste_zeigt_aussagen_ohne_kommentar_neueste_zuerst():
    service = _service(
        ohne_kommentar=[
            _aussage(A, "Windräder sind hässlich", 1),
            _aussage(B, "Tempo 30 bringt nichts", 20),
        ]
    )

    liste = await service.liste()

    assert liste == [
        UnbeantworteteAussage(B, "Tempo 30 bringt nichts", 0),
        UnbeantworteteAussage(A, "Windräder sind hässlich", 0),
    ]


async def test_gesuchte_aussagen_stehen_vorn_mit_zahl_der_personen():
    service = _service(
        ohne_kommentar=[_aussage(A, "Windräder sind hässlich", 20)],
        gesucht=[
            SucheOhneTreffer(B, "Wärmepumpen sind zu teuer", 7, 4),
            SucheOhneTreffer(C, "Das Heizungsgesetz enteignet uns", 3, 2),
        ],
    )

    liste = await service.liste()

    assert [a.statement_id for a in liste] == [B, C, A]
    assert [a.personen_ohne_treffer for a in liste] == [4, 2, 0]


async def test_gesuchte_aussagen_nach_personen_nicht_nach_suchen():
    """Die Reihenfolge passt zur gezeigten Zahl und verraet die Suchen nicht."""
    service = _service(
        gesucht=[
            SucheOhneTreffer(A, "Windräder töten Vögel", 9, 2),
            SucheOhneTreffer(B, "Wärmepumpen sind zu teuer", 5, 5),
            SucheOhneTreffer(C, "Das Heizungsgesetz enteignet uns", 4, 2),
        ],
    )

    liste = await service.liste()

    assert [(a.statement_id, a.personen_ohne_treffer) for a in liste] == [
        (B, 5),
        (A, 2),
        (C, 2),
    ]


async def test_gesuchte_aussage_ohne_kommentar_erscheint_nur_einmal():
    service = _service(
        ohne_kommentar=[_aussage(A, "Windräder sind hässlich", 20)],
        gesucht=[SucheOhneTreffer(A, "Windräder sind hässlich", 2, 2)],
    )

    liste = await service.liste()

    assert liste == [UnbeantworteteAussage(A, "Windräder sind hässlich", 2)]


async def test_liste_ist_begrenzt():
    service = _service(
        ohne_kommentar=[_aussage(C, "c", 2), _aussage(D, "d", 1)],
        gesucht=[SucheOhneTreffer(A, "a", 5, 3), SucheOhneTreffer(B, "b", 4, 2)],
    )

    liste = await service.liste(limit=3)

    assert [a.statement_id for a in liste] == [A, B, C]
