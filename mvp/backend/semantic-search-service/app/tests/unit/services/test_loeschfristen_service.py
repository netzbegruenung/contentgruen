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
    ERLEDIGTER_LOESCHAUFTRAG_TAGE,
    GELOESCHTER_BEITRAG_TAGE,
    MELDUNG_NACH_BEARBEITUNG_TAGE,
    NIE_BENUTZTES_KONTO_TAGE,
    SPERRE_NACH_AUFHEBUNG_TAGE,
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
def sperren():
    return Mock(**{"aufgehobene_loeschen_vor.return_value": 0})


@pytest.fixture
def suchereignisse():
    return Mock(**{"verdichten_vor.return_value": 0})


@pytest.fixture
def service(meldungen, einwuerfe, beitraege, moderation, sperren, suchereignisse):
    return LoeschfristenService(
        meldungen,
        einwuerfe,
        beitraege,
        moderation,
        sperren,
        suchereignisse=suchereignisse,
    )


def test_fristen_wie_im_loeschkonzept():
    """Die Fristen, wie sie in docs/LOESCHKONZEPT.md stehen."""
    assert MELDUNG_NACH_BEARBEITUNG_TAGE == 180
    assert EINWURF_OHNE_BEITRAG_TAGE == 365
    assert GELOESCHTER_BEITRAG_TAGE == 30
    assert SPERRE_NACH_AUFHEBUNG_TAGE == 180
    assert NIE_BENUTZTES_KONTO_TAGE == 30
    assert ERLEDIGTER_LOESCHAUFTRAG_TAGE == 365


class TestLoeschauftraege:
    """Erledigte Loeschauftraege nach dem Widerruf (DSFA R9b)."""

    @pytest.fixture
    def loeschauftraege(self):
        return Mock(
            **{
                "erledigte_loeschen_vor.return_value": 0,
                "ueberfaellige_zaehlen.return_value": 0,
            }
        )

    @pytest.fixture
    def service(
        self, meldungen, einwuerfe, beitraege, moderation, sperren, loeschauftraege
    ):
        return LoeschfristenService(
            meldungen,
            einwuerfe,
            beitraege,
            moderation,
            sperren,
            loeschauftraege=loeschauftraege,
        )

    async def test_erledigt_vor_365_tagen(self, service, loeschauftraege):
        await service.fristen_anwenden(HEUTE)

        loeschauftraege.erledigte_loeschen_vor.assert_called_once_with(
            datetime(2025, 10, 29, tzinfo=timezone.utc)
        )

    async def test_ueberfaellige_als_warning_nur_mit_zahl(
        self, service, loeschauftraege, caplog
    ):
        loeschauftraege.ueberfaellige_zaehlen.return_value = 2

        with caplog.at_level("WARNING"):
            await service.fristen_anwenden(HEUTE)

        warnungen = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnungen) == 1
        assert warnungen[0].getMessage().startswith("2 Loeschauftraege past")

    async def test_keine_warning_ohne_ueberfaellige(self, service, caplog):
        with caplog.at_level("WARNING"):
            await service.fristen_anwenden(HEUTE)

        assert not [r for r in caplog.records if r.levelname == "WARNING"]

    async def test_fehler_haelt_die_anderen_nicht_auf(
        self, service, loeschauftraege, beitraege
    ):
        loeschauftraege.erledigte_loeschen_vor.side_effect = RuntimeError("db weg")

        await service.fristen_anwenden(HEUTE)

        beitraege.geloeschte_laden.assert_awaited_once()


class TestPostgres:
    async def test_suchereignisse_abgeschlossener_tage_werden_verdichtet(
        self, service, suchereignisse
    ):
        """Das Tagespseudonym bleibt nur bis zum Lauf nach Mitternacht (#495)."""
        await service.fristen_anwenden(HEUTE)

        suchereignisse.verdichten_vor.assert_called_once_with(
            datetime(2026, 10, 29, tzinfo=timezone.utc)
        )

    async def test_fehler_beim_verdichten_haelt_die_anderen_nicht_auf(
        self, service, suchereignisse, meldungen
    ):
        suchereignisse.verdichten_vor.side_effect = RuntimeError("db weg")

        await service.fristen_anwenden(HEUTE)

        meldungen.bearbeitete_loeschen_vor.assert_called_once()
        assert service.verdichten_offen is True

    async def test_gelungenes_verdichten_ist_nicht_offen(self, service):
        await service.fristen_anwenden(HEUTE)

        assert service.verdichten_offen is False

    async def test_ohne_suchereignisse_kein_verdichten(
        self, meldungen, einwuerfe, beitraege, moderation, sperren
    ):
        service = LoeschfristenService(
            meldungen, einwuerfe, beitraege, moderation, sperren
        )

        await service.fristen_anwenden(HEUTE)

        meldungen.bearbeitete_loeschen_vor.assert_called_once()

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

    async def test_sperren_aufgehoben_vor_180_tagen(self, service, sperren):
        await service.fristen_anwenden(HEUTE)

        sperren.aufgehobene_loeschen_vor.assert_called_once_with(
            datetime(2026, 5, 2, tzinfo=timezone.utc)
        )

    async def test_fehler_bei_meldungen_haelt_den_rest_nicht_auf(
        self, service, meldungen, einwuerfe, beitraege, sperren
    ):
        meldungen.bearbeitete_loeschen_vor.side_effect = RuntimeError("weg")

        await service.fristen_anwenden(HEUTE)

        einwuerfe.ohne_beitrag_loeschen_vor.assert_called_once()
        sperren.aufgehobene_loeschen_vor.assert_called_once()
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


class TestNieBenutzteKonten:
    """Konten aus Einladungen, deren Link nie benutzt wurde (#538)."""

    @pytest.fixture
    def konten(self):
        return Mock(**{"nie_benutzte_loeschen.return_value": 0})

    @pytest.fixture
    def mit_konten(self, meldungen, einwuerfe, beitraege, moderation, sperren, konten):
        return LoeschfristenService(
            meldungen, einwuerfe, beitraege, moderation, sperren, konten
        )

    async def test_30_tage_nach_ablauf_des_links(self, mit_konten, konten):
        # Der Link gilt drei Tage ab dem Anlegen; 30 Tage danach wird geloescht.
        await mit_konten.fristen_anwenden(HEUTE)

        konten.nie_benutzte_loeschen.assert_called_once_with(
            datetime(2026, 9, 26, tzinfo=timezone.utc)
        )

    async def test_fehler_im_realm_haelt_die_anderen_nicht_auf(
        self, mit_konten, konten, meldungen
    ):
        konten.nie_benutzte_loeschen.side_effect = RuntimeError("Keycloak weg")

        await mit_konten.fristen_anwenden(HEUTE)

        meldungen.bearbeitete_loeschen_vor.assert_called_once()


class TestTakt:
    async def test_loeschen_im_takt_laeuft_nach_fehler_weiter(self):
        service = Mock()
        service.fristen_anwenden = AsyncMock(side_effect=[RuntimeError("x"), None])
        schlafen = AsyncMock(side_effect=[None, asyncio.CancelledError()])

        with patch("services.loeschfristen_service.asyncio.sleep", schlafen):
            with pytest.raises(asyncio.CancelledError):
                await loeschen_im_takt(service, takt_sekunden=5)

        assert service.fristen_anwenden.await_count == 2

    async def test_loeschen_im_takt_holt_gescheitertes_verdichten_nach_einer_stunde_nach(
        self,
    ):
        """Sonst ueberlebte das Tagespseudonym bis zur naechsten Mitternacht (#495)."""
        service = Mock(verdichten_offen=True)
        service.fristen_anwenden = AsyncMock()
        schlafen = AsyncMock(side_effect=asyncio.CancelledError())

        with patch("services.loeschfristen_service.asyncio.sleep", schlafen), patch(
            "services.loeschfristen_service.sekunden_bis_mitternacht",
            return_value=20 * 60 * 60,
        ):
            with pytest.raises(asyncio.CancelledError):
                await loeschen_im_takt(service)

        schlafen.assert_awaited_once_with(60 * 60)

    async def test_loeschen_im_takt_zweiter_lauf_kurz_nach_mitternacht(self):
        """Nachzuegler des Vortags verlieren ihr Pseudonym Minuten spaeter (#495)."""
        service = Mock(verdichten_offen=False)
        service.fristen_anwenden = AsyncMock()
        schlafen = AsyncMock(side_effect=[None, asyncio.CancelledError()])

        with patch("services.loeschfristen_service.asyncio.sleep", schlafen), patch(
            "services.loeschfristen_service.sekunden_bis_mitternacht",
            # erster Lauf 00:00:01, zweiter 00:05:01
            side_effect=[24 * 60 * 60 - 1, 24 * 60 * 60 - 301],
        ):
            with pytest.raises(asyncio.CancelledError):
                await loeschen_im_takt(service)

        assert service.fristen_anwenden.await_count == 2
        # danach wieder bis kurz nach der naechsten Mitternacht
        assert [c.args[0] for c in schlafen.await_args_list] == [
            5 * 60,
            24 * 60 * 60 - 300,
        ]
