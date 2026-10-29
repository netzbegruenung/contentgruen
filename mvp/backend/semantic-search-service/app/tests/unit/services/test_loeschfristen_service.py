"""
Unit-Tests fuer die Loeschfristen (#421).

Repositories und Moderation sind gemockt. Geprueft werden die Grenzen je Frist, das
Stempeln und endgueltige Entfernen geloeschter Beitraege, dass ein Fehler in einer
Datenart die anderen nicht aufhaelt, und der Hintergrund-Task.
"""

import asyncio
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from services.loeschfristen_service import (
    EINWURF_OHNE_BEITRAG_TAGE,
    GELOESCHTER_BEITRAG_TAGE,
    MELDUNG_NACH_BEARBEITUNG_TAGE,
    LoeschfristenService,
    loeschen_im_takt,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

HEUTE = date(2026, 10, 29)


@pytest.fixture
def meldungen():
    return Mock(**{"bearbeitete_loeschen_vor.return_value": 0})


@pytest.fixture
def einwuerfe():
    return Mock(**{"ohne_beitrag_loeschen_vor.return_value": 0})


@pytest.fixture
def beitraege():
    repo = Mock()
    repo.geloeschte_laden = AsyncMock(return_value=[])
    repo.geloescht_am_setzen = AsyncMock()
    return repo


@pytest.fixture
def moderation():
    return Mock(delete_content=AsyncMock(return_value=True))


@pytest.fixture
def service(meldungen, einwuerfe, beitraege, moderation):
    return LoeschfristenService(meldungen, einwuerfe, beitraege, moderation)


def test_fristen():
    """Die Fristen, wie sie in docs/LOESCHKONZEPT.md stehen."""
    assert MELDUNG_NACH_BEARBEITUNG_TAGE == 180
    assert EINWURF_OHNE_BEITRAG_TAGE == 365
    assert GELOESCHTER_BEITRAG_TAGE == 30


class TestPostgres:
    async def test_meldungen_bearbeitet_vor_180_tagen(self, service, meldungen):
        await service.fristen_anwenden(HEUTE)

        meldungen.bearbeitete_loeschen_vor.assert_called_once_with(
            datetime(2026, 5, 2, tzinfo=timezone.utc)
        )

    async def test_einwuerfe_ohne_arbeit_seit_365_tagen(self, service, einwuerfe):
        await service.fristen_anwenden(HEUTE)

        einwuerfe.ohne_beitrag_loeschen_vor.assert_called_once_with(
            datetime(2025, 10, 29, tzinfo=timezone.utc)
        )

    async def test_fehler_bei_meldungen_haelt_den_rest_nicht_auf(
        self, service, meldungen, einwuerfe, beitraege
    ):
        meldungen.bearbeitete_loeschen_vor.side_effect = RuntimeError("weg")

        await service.fristen_anwenden(HEUTE)

        einwuerfe.ohne_beitrag_loeschen_vor.assert_called_once()
        beitraege.geloeschte_laden.assert_awaited_once()


class TestGeloeschteBeitraege:
    async def test_ohne_tag_bekommt_heute_und_bleibt(
        self, service, beitraege, moderation
    ):
        beitraege.geloeschte_laden.return_value = [{"id": "a", "content_type": "post"}]

        await service.fristen_anwenden(HEUTE)

        beitraege.geloescht_am_setzen.assert_awaited_once_with(["a"], HEUTE)
        moderation.delete_content.assert_not_awaited()

    async def test_nach_30_tagen_endgueltig_entfernt(
        self, service, beitraege, moderation
    ):
        beitraege.geloeschte_laden.return_value = [
            {"id": "alt", "content_type": "post", "geloescht_am": "2026-09-28"},
            {"id": "jung", "content_type": "image", "geloescht_am": "2026-09-29"},
        ]

        await service.fristen_anwenden(HEUTE)

        moderation.delete_content.assert_awaited_once_with("alt", "post", None)
        beitraege.geloescht_am_setzen.assert_not_awaited()

    async def test_fehler_bei_einem_beitrag_haelt_die_anderen_nicht_auf(
        self, service, beitraege, moderation
    ):
        beitraege.geloeschte_laden.return_value = [
            {"id": "a", "content_type": "post", "geloescht_am": "2026-01-01"},
            {"id": "b", "content_type": "post", "geloescht_am": "2026-01-01"},
        ]
        moderation.delete_content.side_effect = [RuntimeError("Qdrant"), True]

        await service.fristen_anwenden(HEUTE)

        assert moderation.delete_content.await_count == 2

    async def test_unlesbarer_tag_wird_neu_gesetzt(
        self, service, beitraege, moderation
    ):
        beitraege.geloeschte_laden.return_value = [
            {"id": "a", "content_type": "post", "geloescht_am": "kaputt"}
        ]

        await service.fristen_anwenden(HEUTE)

        beitraege.geloescht_am_setzen.assert_awaited_once_with(["a"], HEUTE)
        moderation.delete_content.assert_not_awaited()


class TestTakt:
    async def test_laeuft_nach_fehler_weiter(self):
        service = Mock()
        service.fristen_anwenden = AsyncMock(side_effect=[RuntimeError("x"), None])
        schlafen = AsyncMock(side_effect=[None, asyncio.CancelledError()])

        with patch("services.loeschfristen_service.asyncio.sleep", schlafen):
            with pytest.raises(asyncio.CancelledError):
                await loeschen_im_takt(service, takt_sekunden=5)

        assert service.fristen_anwenden.await_count == 2
