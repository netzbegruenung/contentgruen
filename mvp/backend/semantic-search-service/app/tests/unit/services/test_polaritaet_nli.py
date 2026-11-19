"""
Polaritaetsstrafe der Suche mit dem NLI-Modell (#574): aus, schatten, an und der
Rueckfall auf die Wortlisten, mit einer Attrappe statt des Modells.
"""

import asyncio
from dataclasses import dataclass

import pytest

from services.dieselbe_behauptung.regel import Richtung, Urteil
from services.polarity_filter_service import PolarityFilterService
from services.search import polaritaet_nli
from services.search.polaritaet_nli import NliPolaritaet, strafe

WIDERSPRUCH = Urteil(Richtung(0.01, 0.97), Richtung(0.02, 0.95))
NEUTRAL = Urteil(Richtung(0.10, 0.10), Richtung(0.10, 0.10))
# Widerspruch nur in einer Richtung: zaehlt nicht (beide Richtungen muessen widersprechen).
EINSEITIG = Urteil(Richtung(0.10, 0.99), Richtung(0.30, 0.30))
# Beidseitig, aber unsicher: unter einer Grenze von 0,9.
UNSICHER = Urteil(Richtung(0.10, 0.85), Richtung(0.10, 0.80))

# Die Wortlisten sehen "nicht wichtig" als Gegenteil von "wichtig", das Gegenteil
# "kann warten" aber nicht.
ANFRAGE = "Klimaschutz ist wichtig"
GEGENTEIL = "Klimaschutz kann warten"
PASSEND = "Klimaschutz ist bedeutend"
VERNEINT = "Klimaschutz ist nicht wichtig"


@dataclass
class Treffer:
    id: str
    text: str
    score: float


class AttrappenNli:
    """Urteilt nach einer Tabelle Kandidatentext -> Urteil; None = Modell fehlt."""

    def __init__(self, nach_kandidat=None, verfuegbar=True, scheitert=False):
        self.nach_kandidat = nach_kandidat or {}
        self.verfuegbar = verfuegbar
        self.scheitert = scheitert
        self.aufrufe = []

    async def urteile(self, paare, warte_hoechstens=None):
        self.aufrufe.append(list(paare))
        self.gewartet = warte_hoechstens
        if self.scheitert:
            raise RuntimeError("kaputt")
        if not self.verfuegbar:
            return None
        return [self.nach_kandidat.get(b, NEUTRAL) for _, b in paare]


def _treffer():
    return [
        Treffer("g", GEGENTEIL, 0.95),
        Treffer("p", PASSEND, 0.93),
        Treffer("v", VERNEINT, 0.97),
    ]


async def _gewichten(polaritaet, treffer, regel=None):
    return await polaritaet.gewichten(
        regel or PolarityFilterService(enable_filtering=True),
        ANFRAGE,
        treffer,
        lambda t: t.text,
    )


def test_strafe_wie_die_regel_mit_dem_widerspruch_als_sicherheit():
    assert strafe(0.5) == pytest.approx(0.65)
    assert strafe(1.0) == pytest.approx(0.3)
    assert strafe(0.0) == 1.0


@pytest.mark.unit
class TestAn:
    @pytest.mark.asyncio
    async def test_straft_gegenteil_ohne_verneinungswort(self):
        nli = AttrappenNli({GEGENTEIL: WIDERSPRUCH, VERNEINT: WIDERSPRUCH})
        ergebnis, metadaten = await _gewichten(
            NliPolaritaet(nli, "an", 0.5), _treffer()
        )

        assert [t.id for t in ergebnis] == ["p", "v", "g"]
        assert metadaten["g"].polarity_mismatch_detected
        assert metadaten["g"].original_score == 0.95
        assert ergebnis[2].score == pytest.approx(0.95 * strafe(0.95))
        assert not metadaten["p"].polarity_mismatch_detected
        assert metadaten["p"].adjusted_score == 0.93

    @pytest.mark.asyncio
    async def test_ohne_widerspruch_keine_strafe_auch_wenn_die_wortliste_straft(self):
        """Das Modell ersetzt die Wortlisten: sieht es keinen Widerspruch, bleibt der
        Score, auch bei "keine"."""
        nli = AttrappenNli()
        ergebnis, metadaten = await _gewichten(
            NliPolaritaet(nli, "an", 0.5), _treffer()
        )

        assert [t.score for t in ergebnis] == [0.97, 0.95, 0.93]
        assert not any(m.polarity_mismatch_detected for m in metadaten.values())

    @pytest.mark.asyncio
    async def test_widerspruch_in_einer_richtung_reicht_nicht(self):
        """Umgangssprachliche Umformulierungen liest das Modell oft in einer Richtung
        als Widerspruch (S02 im Suchtestset)."""
        nli = AttrappenNli({GEGENTEIL: EINSEITIG})
        _, metadaten = await _gewichten(NliPolaritaet(nli, "an", 0.5), _treffer())

        assert not metadaten["g"].polarity_mismatch_detected

    @pytest.mark.asyncio
    async def test_unter_der_grenze_keine_strafe(self):
        nli = AttrappenNli({GEGENTEIL: UNSICHER})
        _, metadaten = await _gewichten(NliPolaritaet(nli, "an", 0.9), _treffer())

        assert not metadaten["g"].polarity_mismatch_detected

    @pytest.mark.asyncio
    async def test_wartet_nicht_unbegrenzt(self):
        nli = AttrappenNli()
        await _gewichten(NliPolaritaet(nli, "an", 0.5), _treffer())

        assert nli.gewartet == polaritaet_nli.SUCHE_WARTET_HOECHSTENS
        assert nli.aufrufe == [[(ANFRAGE, t.text) for t in _treffer()]]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "nli",
        [AttrappenNli(verfuegbar=False), AttrappenNli(scheitert=True)],
        ids=["nicht verfuegbar", "scheitert"],
    )
    async def test_ohne_urteil_gelten_die_wortlisten(self, nli):
        ergebnis, metadaten = await _gewichten(
            NliPolaritaet(nli, "an", 0.5), _treffer()
        )

        assert metadaten["v"].polarity_mismatch_detected, "keine: Wortliste straft"
        assert metadaten["v"].query_polarity != "nli"
        assert not metadaten["g"].polarity_mismatch_detected

    @pytest.mark.asyncio
    async def test_ohne_polaritaetsfilter_straft_auch_das_modell_nicht(self):
        nli = AttrappenNli({GEGENTEIL: WIDERSPRUCH})
        ergebnis, metadaten = await _gewichten(
            NliPolaritaet(nli, "an", 0.5),
            _treffer(),
            PolarityFilterService(enable_filtering=False),
        )

        assert metadaten == {}
        assert nli.aufrufe == []
        assert [t.score for t in ergebnis] == [0.95, 0.93, 0.97]


@pytest.mark.unit
class TestNurUeberBehauptungen:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "anfrage",
        ["Ist Klimaschutz wichtig?", "Klimaschutz wichtig", "Lohnt sich Klimaschutz"],
        ids=["fragezeichen", "schlagwoerter", "frage-ohne-fragezeichen"],
    )
    async def test_frage_und_schlagwoerter_nach_der_regel(self, anfrage):
        nli = AttrappenNli({GEGENTEIL: WIDERSPRUCH})
        _, metadaten = await NliPolaritaet(nli, "an", 0.5).gewichten(
            PolarityFilterService(enable_filtering=True),
            anfrage,
            _treffer(),
            lambda t: t.text,
        )

        assert nli.aufrufe == []
        assert not metadaten["g"].polarity_mismatch_detected

    @pytest.mark.asyncio
    async def test_widerspruch_schliesst_die_antworten_aus(self):
        nli = AttrappenNli({GEGENTEIL: WIDERSPRUCH})
        _, metadaten = await _gewichten(NliPolaritaet(nli, "an", 0.5), _treffer())

        assert metadaten["g"].antworten_ausschliessen
        assert not metadaten["p"].antworten_ausschliessen

    @pytest.mark.asyncio
    async def test_die_regel_schliesst_keine_antworten_aus(self):
        _, metadaten = await _gewichten(
            NliPolaritaet(AttrappenNli(verfuegbar=False), "an", 0.5), _treffer()
        )

        assert metadaten["v"].polarity_mismatch_detected
        assert not metadaten["v"].antworten_ausschliessen


@pytest.mark.unit
class TestAusUndSchatten:
    @pytest.mark.asyncio
    async def test_aus_nur_wortlisten_ohne_modell(self):
        nli = AttrappenNli({GEGENTEIL: WIDERSPRUCH})
        _, metadaten = await _gewichten(NliPolaritaet(nli, "aus", 0.5), _treffer())

        assert nli.aufrufe == []
        assert metadaten["v"].polarity_mismatch_detected
        assert not metadaten["g"].polarity_mismatch_detected

    @pytest.mark.asyncio
    async def test_schatten_wortlisten_entscheiden_modell_wird_gezaehlt(self):
        nli = AttrappenNli({GEGENTEIL: WIDERSPRUCH, VERNEINT: WIDERSPRUCH})
        polaritaet = NliPolaritaet(nli, "schatten", 0.5)

        _, metadaten = await _gewichten(polaritaet, _treffer())
        await asyncio.gather(*polaritaet._schatten_tasks)

        assert metadaten["v"].polarity_mismatch_detected
        assert not metadaten["g"].polarity_mismatch_detected
        assert polaritaet.zaehler == {
            "beide_strafe": 1,
            "nur_nli": 1,
            "beide_keine": 1,
        }

    @pytest.mark.asyncio
    async def test_schatten_ueberspringt_waehrend_ein_urteil_laeuft(self):
        polaritaet = NliPolaritaet(AttrappenNli(), "schatten", 0.5)
        polaritaet._schatten_laeuft = True

        await _gewichten(polaritaet, _treffer())

        assert polaritaet.zaehler == {"uebersprungen": 1}

    @pytest.mark.asyncio
    async def test_schatten_wartet_nicht_und_zaehlt_belegt(self):
        nli = AttrappenNli(verfuegbar=False)
        nli.geladen = True  # geladen, aber die Sperre ist nicht frei
        polaritaet = NliPolaritaet(nli, "schatten", 0.5)

        await _gewichten(polaritaet, _treffer())
        await asyncio.gather(*polaritaet._schatten_tasks)

        assert nli.gewartet == polaritaet_nli.SCHATTEN_WARTET_HOECHSTENS == 0
        assert polaritaet.zaehler == {"belegt": 1}

    @pytest.mark.asyncio
    async def test_schatten_ohne_modell_wird_gezaehlt(self):
        polaritaet = NliPolaritaet(AttrappenNli(verfuegbar=False), "schatten", 0.5)

        await _gewichten(polaritaet, _treffer())
        await asyncio.gather(*polaritaet._schatten_tasks)

        assert polaritaet.zaehler == {"ohne_modell": 1}
