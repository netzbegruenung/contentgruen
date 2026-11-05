"""
NLI-Stufe der Pruefung auf dieselbe Aussage (#387): die Regel ohne Modell und ihr Einsatz
in StatementService mit einer Attrappe statt des Modells. Die Urteile des echten Modells
am Messset prueft tests/unit/test_nli_messset.py ueber die gespeicherte Messung.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest

from domain.models.content_origin import ContentOrigin
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from domain.models.statement import Statement, StatementSearchResult
from services.content.statement_service import StatementService
from services.dieselbe_behauptung import regel
from services.dieselbe_behauptung.regel import Richtung, Urteil
from services.dieselbe_behauptung.schatten import Schattenprotokoll
from tests.conftest import create_base_content_fields, create_statement_data

DIESELBE = Urteil(Richtung(0.99, 0.0), Richtung(0.98, 0.01))
EINSEITIG = Urteil(Richtung(0.99, 0.0), Richtung(0.40, 0.01))
WIDERSPRUCH = Urteil(Richtung(0.01, 0.97), Richtung(0.02, 0.95))
NEUTRAL = Urteil(Richtung(0.10, 0.10), Richtung(0.10, 0.10))


@pytest.mark.unit
class TestRegel:
    def test_dieselbe_behauptung_braucht_beide_richtungen(self):
        assert regel.ist_dieselbe_behauptung(DIESELBE, 0.95, 0.05)
        assert not regel.ist_dieselbe_behauptung(EINSEITIG, 0.95, 0.05)
        assert not regel.ist_dieselbe_behauptung(WIDERSPRUCH, 0.95, 0.05)

    def test_widerspruch_in_einer_richtung_reicht_nicht_fuer_dieselbe(self):
        urteil = Urteil(Richtung(0.97, 0.0), Richtung(0.96, 0.06))
        assert not regel.ist_dieselbe_behauptung(urteil, 0.95, 0.05)

    def test_widerspricht_schon_in_einer_richtung(self):
        urteil = Urteil(Richtung(0.3, 0.6), Richtung(0.3, 0.1))
        assert regel.widerspricht(urteil, 0.5)
        assert not regel.widerspricht(NEUTRAL, 0.5)

    @pytest.mark.parametrize(
        "text",
        ["Lohnt sich Balkonsolar?", "„Lohnt sich Balkonsolar?“ ", "Echt jetzt?)"],
    )
    def test_frage(self, text):
        assert regel.ist_frage(text)

    def test_behauptung_ist_keine_frage(self):
        assert not regel.ist_frage("Balkonsolar lohnt sich!")

    def test_frage_gegen_behauptung_wird_nicht_geprueft(self):
        """B09 im Messset: Eine Frage behauptet nichts (MESSSET.md, Regel 4)."""
        assert not regel.nli_darf_pruefen(
            "Funktionieren Wärmepumpen nur im Neubau?",
            "Wärmepumpen funktionieren nur im Neubau!",
        )

    def test_anderer_quantor_wird_nicht_geprueft(self):
        """WI07: Das Modell folgert "Manche ..." beidseitig, Regel 3 sagt verwandt."""
        assert not regel.nli_darf_pruefen(
            "Manche Windräder töten Vögel", "Windräder töten Vögel"
        )
        assert not regel.nli_darf_pruefen(
            "Balkonsolar lohnt sich nie", "Balkonsolar lohnt sich immer"
        )

    def test_gleiche_quantoren_werden_geprueft(self):
        assert regel.nli_darf_pruefen(
            "Die Bahn ist immer unpünktlich", "Die Bahn ist IMMER zu spät"
        )

    def test_entscheiden_normalisiert_gleich_ohne_urteil(self):
        assert regel.entscheiden(
            "Windräder töten Vögel!",
            "windräder töten vögel",
            0.5,
            None,
            kandidaten_ab=0.85,
            folgerung_ab=0.95,
            widerspruch_unter=0.05,
        )

    def test_entscheiden_unter_der_untergrenze_nie(self):
        assert not regel.entscheiden(
            "Windkraft bringt Vögel um",
            "Windräder töten Vögel",
            0.84,
            DIESELBE,
            kandidaten_ab=0.85,
            folgerung_ab=0.95,
            widerspruch_unter=0.05,
        )

    def test_entscheiden_ohne_urteil_nicht_dieselbe(self):
        assert not regel.entscheiden(
            "Windkraft bringt Vögel um",
            "Windräder töten Vögel",
            0.95,
            None,
            kandidaten_ab=0.85,
            folgerung_ab=0.95,
            widerspruch_unter=0.05,
        )


class AttrappenNli:
    """Urteilt nach einer Tabelle Kandidatentext -> Urteil; None = Modell fehlt."""

    def __init__(self, nach_kandidat=None, verfuegbar=True):
        self.nach_kandidat = nach_kandidat or {}
        self.verfuegbar = verfuegbar
        self.aufrufe = []

    async def urteile(self, paare):
        self.aufrufe.append(list(paare))
        if not self.verfuegbar:
            return None
        return [self.nach_kandidat.get(b, NEUTRAL) for _, b in paare]


def _treffer(text, score):
    return StatementSearchResult(
        **create_base_content_fields(),
        **create_statement_data(text=text),
        id=uuid.uuid4(),
        content_type=ContentType.STATEMENT,
        score=score,
    )


async def _anlegen(service, text):
    return await service.add_statement(
        Statement(text=text, replysuggestions=[]),
        "person-1",
        ContentStatus.VISIBLE,
        ContentOrigin.MANUALLY_CREATED,
    )


@pytest.mark.unit
class TestNliStufeImStatementService:
    @pytest.fixture
    def baue(self, test_settings, repository_factory):
        def bauen(modus, nli):
            settings = test_settings.model_copy(update={"dieselbe_aussage_nli": modus})
            return StatementService(
                settings, repository_factory=repository_factory, nli=nli
            )

        return bauen

    @pytest.mark.asyncio
    async def test_an_fuehrt_umformulierung_zusammen(self, baue):
        vorhanden = _treffer("Windräder töten Vögel", 0.93)
        nli = AttrappenNli({vorhanden.text: DIESELBE})
        service = baue("an", nli)
        service._repository.search = AsyncMock(return_value=[vorhanden])

        neu, statement_id, text = await _anlegen(service, "Windkraft bringt Vögel um")

        assert neu is False
        assert statement_id == vorhanden.id
        assert text == "Windräder töten Vögel", "der vorhandene Wortlaut bleibt"

    @pytest.mark.asyncio
    async def test_an_trennt_widerspruch_auch_ueber_der_schwelle(self, baue):
        """D11: 0,969 heute, im Messset liegen Widersprueche auch ueber 0,98."""
        gegenteil = _treffer("Die Grünen sind keine Verbotspartei", 0.99)
        service = baue("an", AttrappenNli({gegenteil.text: WIDERSPRUCH}))
        service._repository.search = AsyncMock(return_value=[gegenteil])

        neu, statement_id, _ = await _anlegen(
            service, "Die Grünen sind eine Verbotspartei"
        )

        assert neu is True
        assert statement_id != gegenteil.id

    @pytest.mark.asyncio
    async def test_an_prueft_frage_gegen_behauptung_nicht(self, baue):
        behauptung = _treffer("Wärmepumpen funktionieren nur im Neubau!", 0.97)
        nli = AttrappenNli({behauptung.text: DIESELBE})
        service = baue("an", nli)
        service._repository.search = AsyncMock(return_value=[behauptung])

        neu, _, _ = await _anlegen(service, "Funktionieren Wärmepumpen nur im Neubau?")

        assert neu is True
        assert nli.aufrufe == [], "das Modell urteilt nur ueber zugelassene Paare"

    @pytest.mark.asyncio
    async def test_an_prueft_hoechstens_so_viele_kandidaten_ab_der_untergrenze(
        self, baue, test_settings
    ):
        treffer = [_treffer(f"Aussage Nummer {i}", 0.95 - i * 0.01) for i in range(8)]
        treffer.append(_treffer("weit weg", test_settings.nli_kandidaten_ab - 0.01))
        nli = AttrappenNli()
        service = baue("an", nli)
        service._repository.search = AsyncMock(return_value=treffer)

        await _anlegen(service, "Eine ganz andere Aussage")

        assert len(nli.aufrufe) == 1
        assert [b for _, b in nli.aufrufe[0]] == [
            t.text for t in treffer[: test_settings.nli_kandidaten_hoechstens]
        ]

    @pytest.mark.asyncio
    async def test_an_nimmt_die_staerkste_folgerung(self, baue):
        schwaecher = _treffer("Windkraftanlagen töten Vögel", 0.95)
        staerker = _treffer("Windräder töten Vögel", 0.92)
        nli = AttrappenNli(
            {
                schwaecher.text: Urteil(Richtung(0.96, 0.0), Richtung(0.96, 0.0)),
                staerker.text: Urteil(Richtung(0.99, 0.0), Richtung(0.99, 0.0)),
            }
        )
        service = baue("an", nli)
        service._repository.search = AsyncMock(return_value=[schwaecher, staerker])

        _, statement_id, _ = await _anlegen(service, "Windkraft bringt Vögel um")

        assert statement_id == staerker.id

    @pytest.mark.asyncio
    async def test_an_ohne_modell_gilt_die_schwelle(self, baue, test_settings):
        """Kein Ausfall: Ist das Modell nicht verfuegbar, entscheidet die Schwelle."""
        fast_gleich = _treffer(
            "Deutschland kann das Klima nicht alleine retten",
            test_settings.statement_similarity_threshold,
        )
        service = baue("an", AttrappenNli(verfuegbar=False))
        service._repository.search = AsyncMock(return_value=[fast_gleich])

        neu, statement_id, _ = await _anlegen(
            service, "Deutschland kann nicht alleine das Klima retten!"
        )

        assert neu is False
        assert statement_id == fast_gleich.id

    @pytest.mark.asyncio
    async def test_normalisiert_gleich_braucht_kein_modell(self, baue):
        nli = AttrappenNli()
        service = baue("an", nli)
        neu, erste_id, _ = await _anlegen(service, "Windräder töten Vögel")
        wieder_neu, zweite_id, _ = await _anlegen(service, "windräder töten VÖGEL!")

        assert (neu, wieder_neu) == (True, False)
        assert zweite_id == erste_id
        assert nli.aufrufe == []

    @pytest.mark.asyncio
    async def test_schatten_entscheidet_nach_der_schwelle_und_zaehlt(self, baue):
        vorhanden = _treffer("Windräder töten Vögel", 0.93)
        nli = AttrappenNli({vorhanden.text: DIESELBE})
        service = baue("schatten", nli)
        service._repository.search = AsyncMock(return_value=[vorhanden])

        neu, statement_id, _ = await _anlegen(service, "Windkraft bringt Vögel um")
        await asyncio.gather(*service._schatten_tasks)

        assert neu is True, "im Schatten entscheidet die Schwelle"
        assert statement_id != vorhanden.id
        assert service.schattenprotokoll.zaehler == {"nur_nli": 1}

    @pytest.mark.asyncio
    async def test_schatten_ueberspringt_waehrend_ein_urteil_laeuft(self, baue):
        freigabe = asyncio.Event()

        class LangsameNli(AttrappenNli):
            async def urteile(self, paare):
                await freigabe.wait()
                return await super().urteile(paare)

        service = baue("schatten", LangsameNli())
        service._repository.search = AsyncMock(
            return_value=[_treffer("Windräder töten Vögel", 0.93)]
        )

        await _anlegen(service, "Windkraft bringt Vögel um")
        await _anlegen(service, "Windkraft tötet Vögel")
        freigabe.set()
        await asyncio.gather(*service._schatten_tasks)

        assert service.schattenprotokoll.zaehler == {
            "uebersprungen": 1,
            "beide_neu": 1,
        }

    @pytest.mark.asyncio
    async def test_vorhandene_finden_startet_keinen_schatten(self, baue):
        nli = AttrappenNli()
        service = baue("schatten", nli)
        service._repository.search = AsyncMock(
            return_value=[_treffer("Windräder töten Vögel", 0.93)]
        )

        await service.vorhandene_finden("Windkraft bringt Vögel um")

        assert not service._schatten_tasks
        assert nli.aufrufe == []

    @pytest.mark.asyncio
    async def test_aus_fragt_das_modell_nie(self, baue):
        nli = AttrappenNli()
        service = baue("aus", nli)
        service._repository.search = AsyncMock(
            return_value=[_treffer("Windräder töten Vögel", 0.93)]
        )

        await _anlegen(service, "Windkraft bringt Vögel um")
        treffer = [_treffer("Windräder schützen Vögel", 0.95)]
        assert (
            await service.ohne_widerspruch("Windräder töten Vögel", treffer) == treffer
        )
        assert nli.aufrufe == []

    @pytest.mark.asyncio
    async def test_ohne_widerspruch_laesst_gegenteile_weg(self, baue):
        passend = _treffer("Windkraft bringt Vögel um", 0.93)
        gegenteil = _treffer("Windräder schützen Vögel", 0.95)
        nli = AttrappenNli({gegenteil.text: WIDERSPRUCH})
        service = baue("schatten", nli)

        uebrig = await service.ohne_widerspruch(
            "Windräder töten Vögel", [gegenteil, passend]
        )

        assert uebrig == [passend]

    @pytest.mark.asyncio
    async def test_ohne_widerspruch_ohne_modell_laesst_alle(self, baue):
        treffer = [_treffer("Windräder schützen Vögel", 0.95)]
        service = baue("an", AttrappenNli(verfuegbar=False))

        assert (
            await service.ohne_widerspruch("Windräder töten Vögel", treffer) == treffer
        )


@pytest.mark.unit
class TestSchattenprotokoll:
    def test_protokolliert_nur_zaehler_ohne_text_und_id(self, caplog):
        import logging

        from services.dieselbe_behauptung import schatten

        protokoll = Schattenprotokoll()
        aussage = _treffer("Windräder töten Vögel", 0.93)
        with caplog.at_level(logging.INFO, logger=schatten.__name__):
            for _ in range(schatten.ZUSAMMENFASSUNG_ALLE):
                protokoll.vergleichen(aussage, None)

        zeilen = [r.getMessage() for r in caplog.records]
        assert len(zeilen) == 1
        assert "ohne_modell=100" in zeilen[0]
        assert str(aussage.id) not in zeilen[0]
        assert aussage.text not in zeilen[0]
