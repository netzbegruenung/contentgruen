"""
Der Bericht ueber den Bestand (tests/regression/dieselbe_bericht.py, #614) entscheidet
wie StatementService, auch auf dem Weg ueber den Bestaetiger. Mit Attrappen statt
Modellen: hier laedt niemand ein Modell.
"""

import re
from unittest.mock import AsyncMock

import pytest

from services.content.statement_service import StatementService
from tests.regression import dieselbe_bericht
from tests.regression.dieselbe_bericht import Modelle, Paar
from tests.unit.services.test_nli_stufe import (
    DIESELBE,
    KNAPP,
    NEUTRAL,
    AttrappenNli,
    _treffer,
)

ERSTE_ZEILE = re.compile(r"^[0-9][0-9]* sichtbare Aussagen")


class PaarNli(AttrappenNli):
    """Urteilt nach einer Tabelle {Text, Kandidat} -> Urteil, sonst NEUTRAL."""

    async def urteile(self, paare, warte_hoechstens=None):
        self.aufrufe.append(list(paare))
        return [self.nach_kandidat.get(frozenset(p), NEUTRAL) for p in paare]


def _service(settings, repository_factory, aussagen, nli, bestaetiger=None):
    """Ein StatementService ueber dem Bestand aussagen; die Vektorsuche liefert je
    Text alle Aussagen mit ihrem Score (die eigene filtert der Bericht heraus)."""
    service = StatementService(
        settings,
        repository_factory=repository_factory,
        nli=nli,
        bestaetiger=bestaetiger,
    )
    service.get_all = AsyncMock(return_value=list(aussagen))
    service._repository.finde_normalisiert_gleich = AsyncMock(return_value=None)
    service._repository.search = AsyncMock(return_value=list(aussagen))
    return service


@pytest.fixture
def settings(test_settings):
    return test_settings.model_copy(update={"dieselbe_aussage_nli": "an"})


@pytest.mark.unit
class TestBerichtWieDerDienst:
    @pytest.mark.asyncio
    async def test_findet_paar_ueber_das_erste_modell(
        self, settings, repository_factory
    ):
        a = _treffer("Windräder töten Vögel", 0.93)
        b = _treffer("Windkraft bringt Vögel um", 0.93)
        nli = AttrappenNli({a.text: DIESELBE, b.text: DIESELBE})
        service = _service(settings, repository_factory, [a, b], nli)

        anzahl, paare = await dieselbe_bericht.paare_finden(service, Modelle(nli, None))

        assert anzahl == 2
        assert len(paare) == 1, "ein Paar zaehlt einmal, auch aus beiden Richtungen"
        assert paare[0].weg == "nli"

    @pytest.mark.asyncio
    async def test_findet_paar_ueber_den_bestaetiger(
        self, settings, repository_factory
    ):
        a = _treffer("Mit Bürgergeld hat man mehr als mit Arbeit", 0.93)
        b = _treffer("Bürgergeld lohnt sich mehr als Arbeit", 0.93)
        nli = AttrappenNli({a.text: KNAPP, b.text: KNAPP})
        bestaetiger = AttrappenNli({a.text: DIESELBE, b.text: DIESELBE})
        service = _service(
            settings.model_copy(update={"nli_bestaetiger": True}),
            repository_factory,
            [a, b],
            nli,
            bestaetiger,
        )

        _, paare = await dieselbe_bericht.paare_finden(
            service, Modelle(nli, bestaetiger)
        )

        assert [p.weg for p in paare] == ["bestaetiger"]
        assert paare[0].folgerung == DIESELBE.folgerung, "Folgerung des Bestaetigers"

    @pytest.mark.asyncio
    async def test_ohne_bestaetiger_nur_das_erste_modell(
        self, settings, repository_factory
    ):
        a = _treffer("Mit Bürgergeld hat man mehr als mit Arbeit", 0.93)
        b = _treffer("Bürgergeld lohnt sich mehr als Arbeit", 0.93)
        nli = AttrappenNli({a.text: KNAPP, b.text: KNAPP})
        service = _service(settings, repository_factory, [a, b], nli)

        _, paare = await dieselbe_bericht.paare_finden(service, Modelle(nli, None))

        assert paare == []

    @pytest.mark.asyncio
    async def test_entscheidet_wie_vorhandene_finden(
        self, settings, repository_factory
    ):
        """Bericht und Dienst teilen die Entscheidung: Je Aussage findet der Dienst
        das Paar, das der Bericht zeigt - ueber das erste Modell und ueber den
        Bestaetiger. Die Attrappen urteilen je Paar, nicht je Kandidat. Gleichheit gilt
        hier, weil jede Aussage hoechstens einen Partner hat: Der Bericht zaehlt alle
        Paare, der Dienst nimmt davon den staerksten."""
        buerger = (
            "Mit Bürgergeld hat man mehr als mit Arbeit",
            "Bürgergeld lohnt sich mehr als Arbeit",
        )
        wind = ("Windräder töten Vögel", "Windkraft bringt Vögel um")
        texte = [*buerger, *wind, "Sind Wärmepumpen im Altbau sinnvoll"]
        nli = PaarNli({frozenset(buerger): KNAPP, frozenset(wind): DIESELBE})
        bestaetiger = PaarNli({frozenset(buerger): DIESELBE})
        aussagen = [_treffer(t, 0.93) for t in texte]
        service = _service(
            settings.model_copy(update={"nli_bestaetiger": True}),
            repository_factory,
            aussagen,
            nli,
            bestaetiger,
        )
        _, paare = await dieselbe_bericht.paare_finden(
            service, Modelle(nli, bestaetiger)
        )
        im_bericht = {frozenset({p.a_id, p.b_id}) for p in paare}

        vom_dienst = set()
        for aussage in aussagen:
            andere = [t for t in aussagen if t.id != aussage.id]
            service._repository.search = AsyncMock(return_value=andere)
            vorhanden = await service.vorhandene_finden(aussage.text)
            if vorhanden is not None:
                vom_dienst.add(frozenset({str(aussage.id), str(vorhanden.id)}))

        assert vom_dienst == im_bericht
        assert len(im_bericht) == 2, "ein Paar je Weg, die Frage bleibt allein"

    @pytest.mark.asyncio
    async def test_paar_aus_beiden_wegen_zaehlt_ueber_das_erste_modell(
        self, settings, repository_factory
    ):
        """Findet eine Richtung das Paar nur ueber den Bestaetiger, die andere ueber
        das erste Modell, zaehlt es einmal und auf dem Weg des ersten Modells."""
        a = _treffer("Mit Bürgergeld hat man mehr als mit Arbeit", 0.93)
        b = _treffer("Bürgergeld lohnt sich mehr als Arbeit", 0.93)

        class RichtungsNli(AttrappenNli):
            async def urteile(self, paare, warte_hoechstens=None):
                return [self.nach_kandidat.get(p, NEUTRAL) for p in paare]

        # a -> b knapp (Bestaetiger), b -> a sicher (erstes Modell)
        nli = RichtungsNli({(a.text, b.text): KNAPP, (b.text, a.text): DIESELBE})
        bestaetiger = RichtungsNli({(a.text, b.text): DIESELBE})
        service = _service(
            settings.model_copy(update={"nli_bestaetiger": True}),
            repository_factory,
            [a, b],
            nli,
            bestaetiger,
        )

        _, paare = await dieselbe_bericht.paare_finden(
            service, Modelle(nli, bestaetiger)
        )

        assert [p.weg for p in paare] == ["nli"]
        assert paare[0].a_id == str(b.id)


@pytest.mark.unit
class TestModelleUndAusgabe:
    def test_wege_wie_in_der_stufe(self):
        from services.dieselbe_behauptung import stufe

        assert dieselbe_bericht.WEG_NLI == stufe.WEG_NLI
        assert dieselbe_bericht.WEG_BESTAETIGER == stufe.WEG_BESTAETIGER

    def test_weg_bei_nli_aus_sagt_dass_der_dienst_nicht_prueft(self, settings):
        weg = dieselbe_bericht.weg_beschreiben(
            settings.model_copy(update={"dieselbe_aussage_nli": "aus"}), False
        )

        assert "der Dienst prueft so nicht" in weg
        assert "prueft so nicht" not in dieselbe_bericht.weg_beschreiben(
            settings, False
        )

    def test_bestaetiger_nur_mit_schalter(self, settings, monkeypatch):
        from services.dieselbe_behauptung import nli_modell as modul

        geladen = []

        class Modell:
            def __init__(self, name):
                self.name = name

            def laden_abwarten(self):
                geladen.append(self.name)
                return True

        monkeypatch.setattr(modul, "nli_modell", lambda name, tok=None: Modell(name))

        ohne = dieselbe_bericht.modelle_laden(settings)
        mit = dieselbe_bericht.modelle_laden(
            settings.model_copy(update={"nli_bestaetiger": True})
        )

        assert ohne.bestaetiger is None
        assert mit.bestaetiger is not None
        assert len(geladen) == 3

    def test_bestaetiger_fehlt_bricht_ab(self, settings, monkeypatch):
        from services.dieselbe_behauptung import nli_modell as modul

        class Modell:
            def __init__(self, name, tok=None):
                self.tok = tok

            def laden_abwarten(self):
                return self.tok is None  # nur der Bestaetiger hat einen Tokenizer

        monkeypatch.setattr(modul, "nli_modell", Modell)

        with pytest.raises(SystemExit, match="Bestaetiger"):
            dieselbe_bericht.modelle_laden(
                settings.model_copy(update={"nli_bestaetiger": True})
            )

    def test_erste_zeile_bleibt_lesbar_fuer_das_ausroll_skript(self, settings):
        weg = dieselbe_bericht.weg_beschreiben(
            settings.model_copy(update={"nli_bestaetiger": True}), True
        )
        paare = [
            Paar("1", "a", "2", "b", 0.93, 0.99, "nli"),
            Paar("3", "c", "4", "d", 0.91, 0.97, "bestaetiger"),
        ]

        zeilen = dieselbe_bericht.ausgabe(12, paare, weg, mit_paaren=True)

        assert ERSTE_ZEILE.match(zeilen[0])
        assert "12 sichtbare Aussagen, 2 Paare" in zeilen[0]
        assert "davon 1 ueber den Bestaetiger" in zeilen[0]
        assert "erstes Modell und Bestaetiger" in zeilen[0]
        assert "SEMANTIC_SEARCH_DIESELBE_AUSSAGE_NLI=an" in zeilen[0]
        assert "SEMANTIC_SEARCH_NLI_BESTAETIGER=true" in zeilen[0]
        assert zeilen[1].startswith("- 0.930 / 0.990: „a“ (1)")
        assert zeilen[2].startswith("- 0.910 / 0.970 [Bestaetiger]: „c“")

    def test_weg_ohne_bestaetiger(self, settings):
        weg = dieselbe_bericht.weg_beschreiben(settings, False)

        assert "nur erstes Modell" in weg
        assert "SEMANTIC_SEARCH_NLI_BESTAETIGER=false" in weg
        zeilen = dieselbe_bericht.ausgabe(0, [], weg, mit_paaren=True)
        assert zeilen == [
            "0 sichtbare Aussagen, 0 Paare waeren nach der NLI-Stufe dieselbe Aussage, "
            f"davon 0 ueber den Bestaetiger ({weg})."
        ]
