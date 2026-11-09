"""
Stimmen verfallen bei Sinnänderung (#427): Die NLI-Stufe entscheidet, ob ein geänderter
Titel dieselbe Behauptung trifft wie der alte (fassung.gleiche_behauptung,
StatementService.gleiche_behauptung); BeitragAendernService lässt die Stimmen sonst
verfallen. Mit Attrappen statt Modell und Einbettung.
"""

import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from repositories.aggregated.content_repository import ContentRepository
from services.content.beitrag_aendern_service import (
    AenderErgebnis,
    Aenderung,
    BeitragAendernService,
)
from services.content.statement_service import StatementService
from services.dieselbe_behauptung import fassung
from services.dieselbe_behauptung.regel import Richtung, Urteil
from tests.unit.services.test_beitrag_aendern_service import (
    AUTOR,
    BEITRAG_ID,
    _beitrag,
)

pytestmark = pytest.mark.unit

ALT = "Wärmepumpe lohnt sich auch im Altbau"
DIESELBE = Urteil(Richtung(0.99, 0.0), Richtung(0.98, 0.01))
WIDERSPRUCH = Urteil(Richtung(0.01, 0.97), Richtung(0.02, 0.95))
# Knapp unter tau, kein Widerspruch: das unsichere Band fuer den Bestaetiger.
KNAPP = Urteil(Richtung(0.93, 0.01), Richtung(0.60, 0.02))


class Nli:
    """Attrappe des NLI-Modells: ein festes Urteil je Paar, oder None (nicht verfügbar)."""

    def __init__(self, urteil):
        self.urteil = urteil
        self.paare = []

    async def urteile(self, paare, warte_hoechstens=None):
        self.paare += list(paare)
        self.gewartet = warte_hoechstens
        return None if self.urteil is None else [self.urteil for _ in paare]


def _aehnlich(wert):
    return AsyncMock(return_value=wert)


@pytest.mark.asyncio
class TestGleicheBehauptung:
    async def test_umformulierung_bleibt_dieselbe(self, test_settings):
        nli = Nli(DIESELBE)
        gleich = await fassung.gleiche_behauptung(
            ALT,
            "Auch im Altbau lohnt sich eine Wärmepumpe",
            nli,
            None,
            test_settings,
            _aehnlich(0.95),
        )
        assert gleich is True
        # Neue Fassung zuerst, wie bei der Aussage (neuer Text, Kandidat).
        assert nli.paare == [("Auch im Altbau lohnt sich eine Wärmepumpe", ALT)]

    async def test_gegenteil_ist_andere_behauptung(self, test_settings):
        gleich = await fassung.gleiche_behauptung(
            ALT,
            "Wärmepumpe lohnt sich nicht im Altbau",
            Nli(WIDERSPRUCH),
            None,
            test_settings,
            _aehnlich(0.97),
        )
        assert gleich is False

    async def test_ganz_anderer_titel_unter_der_untergrenze(self, test_settings):
        nli = Nli(DIESELBE)
        gleich = await fassung.gleiche_behauptung(
            ALT, "Windräder bringen Geld", nli, None, test_settings, _aehnlich(0.6)
        )
        assert gleich is False
        assert nli.paare == []

    async def test_normalisiert_gleich_ohne_modell(self, test_settings):
        aehnlich = _aehnlich(1.0)
        gleich = await fassung.gleiche_behauptung(
            ALT,
            "  wärmepumpe lohnt sich auch im Altbau!",
            Nli(None),
            None,
            test_settings,
            aehnlich,
        )
        assert gleich is True
        aehnlich.assert_not_awaited()

    async def test_modell_urteilt_nicht_niemand_entscheidet(self, test_settings):
        gleich = await fassung.gleiche_behauptung(
            ALT,
            "Wärmepumpe lohnt sich nicht",
            Nli(None),
            None,
            test_settings,
            _aehnlich(0.95),
        )
        assert gleich is None

    async def test_bestaetiger_rettet_knappe_umformulierung(self, test_settings):
        gleich = await fassung.gleiche_behauptung(
            ALT,
            "Auch im Altbau rechnet sich die Wärmepumpe",
            Nli(KNAPP),
            Nli(DIESELBE),
            test_settings,
            _aehnlich(0.95),
        )
        assert gleich is True

    async def test_bestaetiger_ohne_urteil_niemand_entscheidet(self, test_settings):
        """Fuer Aussagen heisst das "keine dieselbe"; hier wuerde es Stimmen loeschen."""
        gleich = await fassung.gleiche_behauptung(
            ALT,
            "Auch im Altbau rechnet sich die Wärmepumpe",
            Nli(KNAPP),
            Nli(None),
            test_settings,
            _aehnlich(0.95),
        )
        assert gleich is None

    async def test_bestaetiger_verneint_andere_behauptung(self, test_settings):
        gleich = await fassung.gleiche_behauptung(
            ALT,
            "Auch im Altbau rechnet sich die Wärmepumpe",
            Nli(KNAPP),
            Nli(WIDERSPRUCH),
            test_settings,
            _aehnlich(0.95),
        )
        assert gleich is False


@pytest.mark.asyncio
class TestImStatementService:
    def _dienst(self, test_settings, repository_factory, modus, nli):
        settings = test_settings.model_copy(update={"dieselbe_aussage_nli": modus})
        dienst = StatementService(
            settings, repository_factory=repository_factory, nli=nli
        )
        dienst._aehnlichkeit = _aehnlich(0.97)
        return dienst

    async def test_an_entscheidet(self, test_settings, repository_factory):
        dienst = self._dienst(test_settings, repository_factory, "an", Nli(WIDERSPRUCH))
        assert await dienst.gleiche_behauptung(ALT, "Wärmepumpe lohnt nicht") is False

    @pytest.mark.parametrize("modus", ["aus", "schatten"])
    async def test_nicht_an_entscheidet_niemand(
        self, test_settings, repository_factory, modus
    ):
        nli = Nli(WIDERSPRUCH)
        dienst = self._dienst(test_settings, repository_factory, modus, nli)
        assert await dienst.gleiche_behauptung(ALT, "Wärmepumpe lohnt nicht") is None
        assert nli.paare == []

    async def test_wartet_begrenzt_wie_bei_aussagen(
        self, test_settings, repository_factory
    ):
        nli = Nli(DIESELBE)
        dienst = self._dienst(test_settings, repository_factory, "an", nli)
        await dienst.gleiche_behauptung(ALT, "Auch im Altbau lohnt sich die Wärmepumpe")
        assert nli.gewartet == 3.0

    async def test_fehler_entscheidet_niemand(self, test_settings, repository_factory):
        dienst = self._dienst(test_settings, repository_factory, "an", Nli(DIESELBE))
        dienst._aehnlichkeit = AsyncMock(side_effect=RuntimeError())
        assert await dienst.gleiche_behauptung(ALT, "Wärmepumpe lohnt nicht") is None


@pytest.fixture
def speicher(test_embeddings_manager):
    return test_embeddings_manager


def _aendern_service(test_settings, speicher, gleiche_behauptung, stimmen_loeschen):
    return BeitragAendernService(
        ContentRepository(test_settings, speicher),
        AsyncMock(return_value=uuid.uuid4()),
        Mock(return_value=False),
        gleiche_behauptung=gleiche_behauptung,
        stimmen_loeschen=stimmen_loeschen,
    )


def _aenderung(titel, text="Neuer Text."):
    return Aenderung(titel=titel, text=text)


@pytest.mark.asyncio
class TestStimmenBeimAendern:
    async def test_andere_behauptung_stimmen_verfallen(self, test_settings, speicher):
        speicher.add_test_data("commentary", [_beitrag(title=ALT)])
        gleich = AsyncMock(return_value=False)
        loeschen = Mock(return_value=4)
        service = _aendern_service(test_settings, speicher, gleich, loeschen)

        neu = "Wärmepumpe lohnt sich im Altbau nicht"
        ergebnis = await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, _aenderung(neu))

        assert ergebnis is AenderErgebnis.GEAENDERT
        gleich.assert_awaited_once_with(ALT, neu)
        loeschen.assert_called_once_with(uuid.UUID(BEITRAG_ID))

    async def test_kleine_korrektur_stimmen_bleiben(self, test_settings, speicher):
        speicher.add_test_data("commentary", [_beitrag(title=ALT)])
        loeschen = Mock()
        service = _aendern_service(
            test_settings, speicher, AsyncMock(return_value=True), loeschen
        )
        await service.aendern(
            uuid.UUID(BEITRAG_ID),
            AUTOR,
            _aenderung("Wärmepumpen lohnen sich auch im Altbau"),
        )
        loeschen.assert_not_called()

    async def test_ohne_entscheidung_stimmen_bleiben(self, test_settings, speicher):
        speicher.add_test_data("commentary", [_beitrag(title=ALT)])
        loeschen = Mock()
        service = _aendern_service(
            test_settings, speicher, AsyncMock(return_value=None), loeschen
        )
        await service.aendern(
            uuid.UUID(BEITRAG_ID), AUTOR, _aenderung("Etwas ganz anderes")
        )
        loeschen.assert_not_called()

    async def test_nur_text_geaendert_ohne_pruefung(self, test_settings, speicher):
        speicher.add_test_data("commentary", [_beitrag(title=ALT)])
        gleich = AsyncMock(return_value=False)
        loeschen = Mock()
        service = _aendern_service(test_settings, speicher, gleich, loeschen)
        await service.aendern(
            uuid.UUID(BEITRAG_ID), AUTOR, _aenderung(ALT, text="Ganz neuer Text.")
        )
        gleich.assert_not_awaited()
        loeschen.assert_not_called()

    async def test_loeschen_scheitert_aenderung_steht(self, test_settings, speicher):
        speicher.add_test_data("commentary", [_beitrag(title=ALT)])
        service = _aendern_service(
            test_settings,
            speicher,
            AsyncMock(return_value=False),
            Mock(side_effect=ConnectionError()),
        )
        neu = "Wärmepumpe lohnt sich im Altbau nicht"
        ergebnis = await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, _aenderung(neu))
        assert ergebnis is AenderErgebnis.GEAENDERT
        assert speicher.get_data()[BEITRAG_ID]["title"] == neu

    async def test_hintergrundinfo_ebenso(self, test_settings, speicher):
        speicher.add_test_data("generic_text", [_beitrag("generic_text", title=ALT)])
        gleich = AsyncMock(return_value=False)
        loeschen = Mock(return_value=1)
        service = _aendern_service(test_settings, speicher, gleich, loeschen)
        neu = "Wärmepumpe lohnt sich im Altbau nicht"
        await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, _aenderung(neu))
        gleich.assert_awaited_once_with(ALT, neu)
        loeschen.assert_called_once()

    async def test_pruefung_wirft_aenderung_steht_stimmen_bleiben(
        self, test_settings, speicher
    ):
        speicher.add_test_data("commentary", [_beitrag(title=ALT)])
        loeschen = Mock()
        service = _aendern_service(
            test_settings, speicher, AsyncMock(side_effect=RuntimeError()), loeschen
        )
        neu = "Wärmepumpe lohnt sich im Altbau nicht"
        ergebnis = await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, _aenderung(neu))
        assert ergebnis is AenderErgebnis.GEAENDERT
        loeschen.assert_not_called()

    async def test_alter_titel_nicht_lesbar_stimmen_bleiben(
        self, test_settings, speicher
    ):
        speicher.add_test_data("commentary", [_beitrag(title=ALT)])
        gleich = AsyncMock(return_value=False)
        loeschen = Mock()
        service = _aendern_service(test_settings, speicher, gleich, loeschen)
        echtes_get = service.repository.get

        async def get(beitrag_id, eintrag_modell=None):
            if eintrag_modell is not None:
                raise RuntimeError()
            return await echtes_get(beitrag_id)

        service.repository.get = get
        await service.aendern(uuid.UUID(BEITRAG_ID), AUTOR, _aenderung("Anderes"))
        gleich.assert_not_awaited()
        loeschen.assert_not_called()

    async def test_nicht_autor_prueft_nichts(self, test_settings, speicher):
        speicher.add_test_data("commentary", [_beitrag(title=ALT)])
        gleich = AsyncMock(return_value=False)
        loeschen = Mock()
        service = _aendern_service(test_settings, speicher, gleich, loeschen)
        ergebnis = await service.aendern(
            uuid.UUID(BEITRAG_ID), "jemand-anders", _aenderung("Anderes")
        )
        assert ergebnis is AenderErgebnis.NICHT_AUTOR
        gleich.assert_not_awaited()
        loeschen.assert_not_called()
