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
        [
            "Lohnt sich Balkonsolar?",
            "„Lohnt sich Balkonsolar?“ ",
            "Echt jetzt?)",
            # Suchanfragen ohne Fragezeichen: finites Verb an erster Stelle
            "Sind Wärmepumpen im Altbau sinnvoll",
            "„Lohnt sich Balkonsolar“",
            "gibt es den Klimawandel",
        ],
    )
    def test_frage(self, text):
        assert regel.ist_frage(text)

    @pytest.mark.parametrize(
        "text",
        [
            "Balkonsolar lohnt sich!",
            "Wärmepumpen sind im Altbau sinnvoll",
            # Substantive am Satzanfang, die auch Verbformen sein koennten
            "Kosten der Energiewende sind zu hoch",
            "Schaden durch Windräder ist gering",
        ],
    )
    def test_behauptung_ist_keine_frage(self, text):
        assert not regel.ist_frage(text)

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

    async def urteile(self, paare, warte_hoechstens=None):
        self.aufrufe.append(list(paare))
        self.gewartet = warte_hoechstens
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
    async def test_an_wartet_begrenzt_auf_das_modell(self, baue):
        """Belegt oder noch beim Laden: Das Modell antwortet nach der Wartezeit mit
        None, dann gilt die Schwelle (Test oben); unbegrenzt warten darf keine Suche."""
        nli = AttrappenNli()
        service = baue("an", nli)
        service._repository.search = AsyncMock(
            return_value=[_treffer("Windräder töten Vögel", 0.93)]
        )

        await _anlegen(service, "Windkraft bringt Vögel um")

        assert nli.gewartet is not None

    @pytest.mark.asyncio
    async def test_seeding_wartet_auf_das_modell(
        self, test_settings, repository_factory
    ):
        """Eine Regel fuer alle Wege: Das Seeding (nli_warten) laesst nicht nach der
        Wartezeit die Schwelle gelten, sondern wartet auf das Urteil."""
        nli = AttrappenNli()
        settings = test_settings.model_copy(update={"dieselbe_aussage_nli": "an"})
        service = StatementService(
            settings, repository_factory=repository_factory, nli=nli, nli_warten=True
        )
        service._repository.search = AsyncMock(
            return_value=[_treffer("Windräder töten Vögel", 0.93)]
        )

        await _anlegen(service, "Windkraft bringt Vögel um")

        assert nli.aufrufe and nli.gewartet is None

    def test_seeding_und_dienst_teilen_ein_modell(
        self, test_settings, repository_factory
    ):
        """Das Seeding baut einen eigenen StatementService; er bekommt dasselbe, im
        Hintergrund vorgeladene Modell statt eines zweiten, nie geladenen."""
        settings = test_settings.model_copy(update={"dieselbe_aussage_nli": "schatten"})
        dienst = StatementService(settings, repository_factory=repository_factory)
        seeding = StatementService(
            settings, repository_factory=repository_factory, nli_warten=True
        )

        assert seeding._nli is dienst._nli

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
    async def test_an_normalisiert_gleicher_altbestand_vor_jedem_urteil(self, baue):
        """Altbestand ohne Payload-Feld: normalisiert gleich zaehlt immer, auch wenn
        ein anderer Kandidat staerker gefolgert wuerde oder die Schwelle erreicht."""
        anderer = _treffer("Windkraftanlagen töten Vögel", 0.99)
        gleicher = _treffer("Windräder töten Vögel!", 0.93)
        service = baue("an", AttrappenNli({anderer.text: DIESELBE}))
        service._repository.finde_normalisiert_gleich = AsyncMock(return_value=None)
        service._repository.search = AsyncMock(return_value=[anderer, gleicher])

        _, statement_id, _ = await _anlegen(service, "windräder töten vögel")

        assert statement_id == gleicher.id

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
            async def urteile(self, paare, warte_hoechstens=None):
                await freigabe.wait()
                return await super().urteile(paare, warte_hoechstens)

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

    def test_aus_laedt_kein_modell(self, test_settings, repository_factory):
        settings = test_settings.model_copy(update={"dieselbe_aussage_nli": "aus"})
        service = StatementService(settings, repository_factory=repository_factory)

        service.nli_vorladen()  # ohne Modell nichts zu laden

        assert service._nli is None

    def test_schatten_baut_das_modell_ohne_es_zu_laden(
        self, test_settings, repository_factory
    ):
        from services.dieselbe_behauptung.nli_modell import NliModell

        settings = test_settings.model_copy(update={"dieselbe_aussage_nli": "schatten"})
        service = StatementService(settings, repository_factory=repository_factory)

        assert isinstance(service._nli, NliModell)
        assert service._nli._modell is None, "geladen wird erst mit vorladen/Urteil"

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
    async def test_ohne_widerspruch_prueft_nur_so_viele_wie_noetig(self, baue):
        """Vorschlaege: in Score-Reihenfolge stapelweise, bis genug uebrig sind - ohne
        Widerspruch reicht ein Stapel, statt den ganzen Vorrat zu pruefen."""
        treffer = [_treffer(f"Windkraft hilft {i}", 0.95 - i / 100) for i in range(9)]
        nli = AttrappenNli()
        service = baue("schatten", nli)

        uebrig = await service.ohne_widerspruch(
            "Windkraft hilft", treffer, hoechstens=3
        )

        assert uebrig == treffer[:3]
        assert [len(a) for a in nli.aufrufe] == [3]

    @pytest.mark.asyncio
    async def test_ohne_widerspruch_rueckt_nach_wenn_einer_wegfaellt(self, baue):
        treffer = [_treffer(f"Windkraft hilft {i}", 0.95 - i / 100) for i in range(9)]
        nli = AttrappenNli({treffer[1].text: WIDERSPRUCH})
        service = baue("schatten", nli)

        uebrig = await service.ohne_widerspruch(
            "Windkraft hilft", treffer, hoechstens=3
        )

        assert uebrig == [treffer[0], treffer[2], treffer[3]]
        assert [len(a) for a in nli.aufrufe] == [3, 1]

    @pytest.mark.asyncio
    async def test_ohne_widerspruch_rest_ungefiltert_wenn_modell_ausfaellt(self, baue):
        treffer = [_treffer(f"Windkraft hilft {i}", 0.95 - i / 100) for i in range(5)]

        class ErstDannWeg(AttrappenNli):
            async def urteile(self, paare, warte_hoechstens=None):
                if self.aufrufe:
                    self.aufrufe.append(list(paare))
                    return None
                return await super().urteile(paare, warte_hoechstens)

        service = baue("schatten", ErstDannWeg({treffer[0].text: WIDERSPRUCH}))

        uebrig = await service.ohne_widerspruch(
            "Windkraft hilft", treffer, hoechstens=3
        )

        assert uebrig == treffer[1:]

    @pytest.mark.asyncio
    async def test_ohne_widerspruch_wartet_nicht_unbegrenzt(self, baue):
        nli = AttrappenNli()
        service = baue("schatten", nli)

        await service.ohne_widerspruch(
            "Windräder töten Vögel", [_treffer("Windräder schützen Vögel", 0.95)]
        )

        assert nli.gewartet is not None

    @pytest.mark.asyncio
    async def test_ohne_widerspruch_bei_fehler_ungefiltert(self, baue):
        class KaputteNli(AttrappenNli):
            async def urteile(self, paare, warte_hoechstens=None):
                raise RuntimeError("weg")

        treffer = [_treffer("Windräder schützen Vögel", 0.95)]
        service = baue("an", KaputteNli())

        assert (
            await service.ohne_widerspruch("Windräder töten Vögel", treffer) == treffer
        )

    @pytest.mark.asyncio
    async def test_ohne_widerspruch_ohne_modell_laesst_alle(self, baue):
        treffer = [_treffer("Windräder schützen Vögel", 0.95)]
        service = baue("an", AttrappenNli(verfuegbar=False))

        assert (
            await service.ohne_widerspruch("Windräder töten Vögel", treffer) == treffer
        )


@pytest.mark.unit
class TestNliModellOhneModell:
    """Was ohne geladenes Modell gilt; das Modell selbst laedt hier niemand."""

    def test_wer_nicht_warten_will_bekommt_waehrend_des_ladens_none(self):
        from services.dieselbe_behauptung.nli_modell import NliModell

        modell = NliModell("gibt-es-nicht/modell")
        modell._laden = lambda: pytest.fail("darf nicht laden")

        assert modell.urteile_sync([("a", "b")], warte_hoechstens=0.1) is None

    def test_belegtes_modell_gibt_nach_der_wartezeit_none(self):
        from services.dieselbe_behauptung.nli_modell import NliModell

        modell = NliModell("gibt-es-nicht/modell")
        modell._modell = object()  # gilt als geladen
        modell._sperre.acquire()
        try:
            assert modell.urteile_sync([("a", "b")], warte_hoechstens=0.05) is None
        finally:
            modell._sperre.release()

    @pytest.mark.asyncio
    async def test_wartende_belegen_keinen_thread(self, monkeypatch):
        """Asynchron wartet ein Aufruf in der Ereignisschleife auf die Sperre, nicht in
        einem Thread des gemeinsamen Executors (den brauchen auch andere)."""
        from services.dieselbe_behauptung.nli_modell import NliModell

        modell = NliModell("gibt-es-nicht/modell")
        modell._modell = object()  # gilt als geladen
        threads = []
        monkeypatch.setattr(
            asyncio, "to_thread", lambda *a, **k: threads.append(a) or pytest.fail()
        )
        modell._sperre.acquire()
        try:
            assert await modell.urteile([("a", "b")], warte_hoechstens=0.1) is None
        finally:
            modell._sperre.release()
        assert threads == []

    @pytest.mark.asyncio
    async def test_gibt_die_sperre_nach_dem_urteil_frei(self):
        from services.dieselbe_behauptung.nli_modell import NliModell

        modell = NliModell("gibt-es-nicht/modell")
        modell._modell = object()
        modell._rechnen = lambda paare: [NEUTRAL for _ in paare]

        assert await modell.urteile([("a", "b")], warte_hoechstens=0.1) == [NEUTRAL]
        assert modell._sperre.acquire(blocking=False)
        modell._sperre.release()

    def test_ein_modell_je_name_und_prozess(self):
        from services.dieselbe_behauptung.nli_modell import nli_modell

        assert nli_modell("gibt-es-nicht/a") is nli_modell("gibt-es-nicht/a")
        assert nli_modell("gibt-es-nicht/a") is not nli_modell("gibt-es-nicht/b")

    def test_scheitert_das_laden_gilt_die_schwelle(self, monkeypatch):
        import transformers

        from services.dieselbe_behauptung.nli_modell import NliModell

        def scheitern(*args, **kwargs):
            raise OSError("kein Modell")

        monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", scheitern)
        modell = NliModell("gibt-es-nicht/modell")

        assert modell.urteile_sync([("a", "b")]) is None
        assert modell.verfuegbar is False


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
