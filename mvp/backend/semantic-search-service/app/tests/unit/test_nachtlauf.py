"""
Pruefung des naechtlichen Laufs (tests/regression/nachtlauf.py) ohne Stack: Vergleich mit
dem Soll, Toleranz, Tor fuer Roadmap-Stufe 3, untere Grenze fuer aehnliche Aussagen und
Exit-Codes. Der Lauf selbst: .woodpecker/nacht.yaml, docs/CI.md.
"""

import re
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from tests.regression import nachtlauf
from tests.regression.nachtlauf import (
    ABWEICHUNG,
    SOLL,
    TOLERANZ_FAELLE,
    TOR_STUFE_3,
    UNTERE_GRENZE_AEHNLICHE,
    Pruefung,
    bericht,
    pruefen,
)
from tests.regression.suche_messen import (
    BESTAND_PASST_NICHT,
    AngezeigterBeitrag,
    FallMessung,
)
from tests.regression.suche_testset import Fall

A = "Windräder töten die Vögel!"
SCHWELLE = 0.8
DOKU = Path(__file__).parents[1] / "regression" / "SUCHTESTSET.md"


def _fall(id_, erwartet=(A,), dieselbe=False):
    return Fall(id_, "Anfrage", "satz", "umformulierung", erwartet, dieselbe, "eigen")


def _b(passt):
    return AngezeigterBeitrag("b", "commentary", A, 0.9, passt)


def _messungen(soll=SOLL):
    """Messungen, die genau das Soll ergeben."""
    messungen = []
    nr = iter(range(1000))

    def neu(erwartet, gezeigt, dieselbe=False, landet=None, aehnliche=()):
        messungen.append(
            FallMessung(
                _fall(f"X{next(nr):03}", erwartet, dieselbe),
                {SCHWELLE: gezeigt},
                (),
                landet,
                aehnliche,
            )
        )

    mit = soll["treffer"] + soll["fehltreffer"] + soll["keine"]
    aehnlich_mit = iter([True] * soll["aehnliche_erwartete_dabei"] + [False] * mit)
    neu_zerfasert = iter(
        [False] * soll["zerfaserung_neu"]
        + [True] * (soll["dieselbe_behauptung"] - soll["zerfaserung_neu"])
    )
    zerfaserung_offen = soll["dieselbe_behauptung"]
    for gezeigt, anzahl in (
        ((_b(True),), soll["treffer"]),
        ((_b(False),), soll["fehltreffer"]),
        ((), soll["keine"]),
    ):
        for _ in range(anzahl):
            dieselbe = zerfaserung_offen > 0
            zerfaserung_offen -= dieselbe
            neu(
                (A,),
                gezeigt,
                dieselbe=dieselbe,
                landet=next(neu_zerfasert) if dieselbe else None,
                aehnliche=(next(aehnlich_mit),),
            )
    aehnlich_ohne = iter(
        [(False,)] * soll["aehnliche_ohne_mit_vorschlag"] + [()] * 1000
    )
    for _ in range(soll["ohne_richtig_keine"]):
        neu((), (), aehnliche=next(aehnlich_ohne))
    for _ in range(soll["ohne_fehltreffer"]):
        neu((), (_b(False),), aehnliche=next(aehnlich_ohne))
    return messungen


def _rot(pruefungen):
    return [p.name for p in pruefungen if not p.ok]


class TestPruefen:
    def test_messung_wie_das_soll_ist_gruen(self):
        pruefungen = pruefen(_messungen(), SCHWELLE)

        assert _rot(pruefungen) == []
        assert {p.name for p in pruefungen} >= {
            "Treffer",
            "Fehltreffer",
            "keine",
            "Zerfaserung",
            "Tor Roadmap-Stufe 3: Recall@10",
            "Untere Grenze ähnliche Aussagen",
        }

    def test_abweichung_innerhalb_der_toleranz_ist_gruen(self):
        soll = dict(SOLL, treffer=SOLL["treffer"] - TOLERANZ_FAELLE)
        soll["keine"] += TOLERANZ_FAELLE

        assert _rot(pruefen(_messungen(soll), SCHWELLE)) == []

    def test_weniger_treffer_als_toleranz_ist_rot(self):
        weniger = TOLERANZ_FAELLE + 1
        soll = dict(SOLL, treffer=SOLL["treffer"] - weniger)
        soll["keine"] += weniger

        assert set(_rot(pruefen(_messungen(soll), SCHWELLE))) >= {"Treffer", "keine"}

    def test_besser_als_das_soll_ist_auch_rot(self):
        """Eine Verbesserung verschiebt die Ergebnisse auch: Soll nachziehen."""
        mehr = TOLERANZ_FAELLE + 1
        soll = dict(SOLL, treffer=SOLL["treffer"] + mehr)
        soll["keine"] -= mehr

        rot = [p for p in pruefen(_messungen(soll), SCHWELLE) if not p.ok]

        assert "Treffer" in [p.name for p in rot]
        assert "SOLL" in bericht(rot)

    def test_fehlender_fall_ist_rot(self):
        messungen = _messungen()
        messungen[0] = messungen[0]._replace(fehlt=(A,))

        assert "gemessene Fälle" in _rot(pruefen(messungen, SCHWELLE))

    def test_tor_fuer_stufe_3_unabhaengig_vom_soll(self):
        """Faellt Recall@10 unter das Tor, ist der Lauf rot, auch wenn das Soll es
        erlauben wuerde."""
        with patch.dict(TOR_STUFE_3, {"recall_bei_10": 0.99}):
            assert "Tor Roadmap-Stufe 3: Recall@10" in _rot(
                pruefen(_messungen(), SCHWELLE)
            )

    def test_untere_grenze_fuer_aehnliche_aussagen(self):
        with patch.object(nachtlauf, "UNTERE_GRENZE_AEHNLICHE", 0.99):
            assert "Untere Grenze ähnliche Aussagen" in _rot(
                pruefen(_messungen(), SCHWELLE)
            )

    def test_soll_haelt_tor_und_untere_grenze_ein(self):
        """Das Soll selbst darf nicht rot sein: Tor und Grenze liegen darunter."""
        mit = SOLL["treffer"] + SOLL["fehltreffer"] + SOLL["keine"]
        assert SOLL["aehnliche_erwartete_dabei"] / mit >= UNTERE_GRENZE_AEHNLICHE
        assert 0 < UNTERE_GRENZE_AEHNLICHE <= 1
        assert all(0 < wert <= 1 for wert in TOR_STUFE_3.values())


class TestBericht:
    def test_tabelle_mit_soll_gemessen_und_ergebnis(self):
        text = bericht(
            [
                Pruefung("Treffer", "29/33 ±1", "29/33", True),
                Pruefung("keine", "2 ±1", "5", False, "weniger Treffer"),
            ]
        )

        assert "| Prüfung | Soll | gemessen | Ergebnis |" in text
        assert "| Treffer | 29/33 ±1 | 29/33 | ok |" in text
        assert "| keine | 2 ±1 | 5 | ROT: weniger Treffer |" in text


class TestMain:
    def _main(self, messungen, capsys):
        with patch.object(
            nachtlauf, "messen", AsyncMock(return_value=messungen)
        ), patch("core.logging.initialize_logging"), patch.object(
            nachtlauf, "schwelle_heute", return_value=SCHWELLE
        ):
            code = nachtlauf.main([])
        return code, capsys.readouterr()

    def test_gruen(self, capsys):
        code, ausgabe = self._main(_messungen(), capsys)

        assert code == 0
        assert "| Treffer |" in ausgabe.out
        assert "| Schwelle | Treffer |" in ausgabe.out  # Tabelle von suche_messen

    def test_rot_bei_abweichung(self, capsys):
        soll = dict(SOLL, treffer=SOLL["treffer"] - 3)
        soll["keine"] += 3

        code, ausgabe = self._main(_messungen(soll), capsys)

        assert code == ABWEICHUNG
        assert "ROT" in ausgabe.out

    def test_bestand_passt_nicht(self, capsys):
        alle_fehlen = [m._replace(fehlt=(A,)) for m in _messungen()]

        code, _ = self._main(alle_fehlen, capsys)

        assert code == BESTAND_PASST_NICHT


class TestSollWieDoku:
    def test_soll_ist_die_zeile_von_heute_in_suchtestset_md(self):
        """Das Soll ist die dokumentierte Messung am Seed, keine zweite Wahrheit."""
        zeile = next(
            z for z in DOKU.read_text(encoding="utf-8").splitlines() if "(heute)" in z
        )
        zellen = [z.strip() for z in zeile.strip("|").split("|")]
        mit = SOLL["treffer"] + SOLL["fehltreffer"] + SOLL["keine"]
        ohne = SOLL["ohne_richtig_keine"] + SOLL["ohne_fehltreffer"]

        assert zellen[1] == f"{SOLL['treffer']}/{mit}"
        assert zellen[2:4] == [str(SOLL["fehltreffer"]), str(SOLL["keine"])]
        assert zellen[4] == (
            f"{SOLL['ohne_richtig_keine']}/{ohne} / {SOLL['ohne_fehltreffer']}"
        )
        assert SOLL["gemessen"] == mit + ohne

    def test_doku_nennt_zerfaserung_und_aehnliche_aussagen_wie_das_soll(self):
        text = re.sub(r"\s+", " ", DOKU.read_text(encoding="utf-8"))
        mit = SOLL["treffer"] + SOLL["fehltreffer"] + SOLL["keine"]

        assert f"{SOLL['zerfaserung_neu']} der {SOLL['dieselbe_behauptung']} " in text
        assert f"{SOLL['aehnliche_erwartete_dabei']} von {mit}" in text


@pytest.mark.parametrize("name", ["recall_bei_10", "praezision"])
def test_tor_hat_beide_kennzahlen(name):
    assert name in TOR_STUFE_3
