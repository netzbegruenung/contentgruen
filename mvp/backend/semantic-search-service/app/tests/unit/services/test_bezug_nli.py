"""
Bezug einer Aussage zur Suchanfrage (services/search/bezug_nli.py), mit einer Attrappe
statt des Modells. Scores und Urteile sind die am Startbestand gemessenen
(tests/regression/SUCHTESTSET.md, Abschnitt Bezug): Aehnlichkeit der Einbettung,
Folgerung hin/rueck aus NLI_MODELL.
"""

from dataclasses import dataclass

import pytest

from services.dieselbe_behauptung.regel import Richtung, Urteil
from services.search.bezug_nli import AussageBezug

MIGRANTEN = "Migranten machen unsere Städte unsicher."
BIO = "Bio ist nur was für Reiche."
MEINUNG = "Man darf ja gar nichts mehr sagen."

# Grenzen wie in core/config.py
AB, SICHER_AB, FOLGERUNG_AB = 0.87, 0.92, 0.2


@dataclass
class Treffer:
    text: str
    score: float


def _urteil(hin_f, rueck_f, hin_w=0.0, rueck_w=0.0):
    return Urteil(Richtung(hin_f, hin_w), Richtung(rueck_f, rueck_w))


class AttrappenNli:
    """Urteilt nach einer Tabelle (Anfrage, Kandidat) -> Urteil; None = Modell fehlt."""

    def __init__(self, urteile=None, verfuegbar=True, scheitert=False):
        self.tabelle = urteile or {}
        self.verfuegbar = verfuegbar
        self.scheitert = scheitert
        self.aufrufe = []

    async def urteile(self, paare, warte_hoechstens=None):
        self.aufrufe.append(list(paare))
        if self.scheitert:
            raise RuntimeError("kaputt")
        if not self.verfuegbar:
            return None
        return [self.tabelle[paar] for paar in paare]


def _bezug(nli):
    return AussageBezug(nli, AB, SICHER_AB, FOLGERUNG_AB)


async def _ohne(bezug, anfrage, treffer):
    return await bezug.ohne_bezug(anfrage, treffer, lambda t: t.text, lambda t: t.score)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_open_source_ist_unsicher_hat_keinen_bezug_zu_migranten():
    # Der Befund von Produktion 0.9.0: "Erkannt als Migranten machen unsere Städte
    # unsicher." Unter der Untergrenze, das Modell wird gar nicht gefragt.
    nli = AttrappenNli()
    treffer = [Treffer(MIGRANTEN, 0.862)]
    assert await _ohne(_bezug(nli), "Open Source ist unsicher!", treffer) == {0}
    assert nli.aufrufe == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_untergrenze_gilt_auch_ohne_modell():
    treffer = [Treffer(MIGRANTEN, 0.862)]
    assert await _ohne(_bezug(None), "Open Source ist unsicher!", treffer) == {0}
    unverfuegbar = AttrappenNli(verfuegbar=False)
    assert await _ohne(_bezug(unverfuegbar), "Windows ist unsicher", treffer) == {0}


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "anfrage,aussage,score",
    [
        ("Ausländer machen unsere Städte unsicher", MIGRANTEN, 0.967),
        ("Wegen der Migranten ist es in unseren Städten gefährlich", MIGRANTEN, 0.966),
        ("Bio können sich nur Reiche leisten", BIO, 0.970),
    ],
)
async def test_umformulierung_ab_sicher_ab_bleibt_ohne_modell(anfrage, aussage, score):
    nli = AttrappenNli()
    assert await _ohne(_bezug(nli), anfrage, [Treffer(aussage, score)]) == set()
    assert nli.aufrufe == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gleicher_satzbau_ohne_folgerung_faellt_weg():
    anfrage = "Golf ist nur was für Reiche"
    nli = AttrappenNli({(anfrage, BIO): _urteil(0.03, 0.03, 0.28, 0.25)})
    assert await _ohne(_bezug(nli), anfrage, [Treffer(BIO, 0.907)]) == {0}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_umformulierung_mit_folgerung_in_einer_richtung_bleibt():
    anfrage = "In diesem Land darf man seine Meinung nicht mehr sagen"
    nli = AttrappenNli({(anfrage, MEINUNG): _urteil(0.43, 0.00)})
    assert await _ohne(_bezug(nli), anfrage, [Treffer(MEINUNG, 0.901)]) == set()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nur_das_band_geht_ans_modell():
    anfrage = "Golf ist nur was für Reiche"
    nli = AttrappenNli({(anfrage, BIO): _urteil(0.03, 0.03)})
    treffer = [
        Treffer("sehr nah", 0.95),
        Treffer(BIO, 0.907),
        Treffer(MIGRANTEN, 0.85),
    ]
    assert await _ohne(_bezug(nli), anfrage, treffer) == {1, 2}
    assert nli.aufrufe == [[(anfrage, BIO)]]


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "nli", [None, AttrappenNli(verfuegbar=False), AttrappenNli(scheitert=True)]
)
async def test_ohne_urteil_bleibt_das_band(nli):
    # Lieber die Aussage zeigen, als sie wegzulassen, weil das Modell gerade belegt ist.
    treffer = [Treffer(BIO, 0.907)]
    assert await _ohne(_bezug(nli), "Golf ist nur was für Reiche", treffer) == set()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "anfrage", ["Migration Kriminalität", "Ist Open Source unsicher?", "unsicher"]
)
async def test_fragen_und_schlagwoerter_prueft_es_nicht(anfrage):
    nli = AttrappenNli()
    treffer = [Treffer(MIGRANTEN, 0.80)]
    assert await _ohne(_bezug(nli), anfrage, treffer) == set()
    assert nli.aufrufe == []
