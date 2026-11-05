"""
Suchtestset (tests/regression/suche_testset.py) ohne Stack: Aufbau, Umfang, Bezug zum
Seed und die Auswertung von suche_messen.py an kleinen, von Hand gebauten Messungen.
Gemessen gegen einen Stack wird mit `python -m tests.regression.suche_messen`
(SUCHTESTSET.md).
"""

import json
from collections import Counter
from pathlib import Path

import pytest

from tests.regression.suche_messen import (
    VORLAEUFIG,
    FallMessung,
    Kandidat,
    als_json,
    angezeigt,
    auswerten,
    einordnen,
    faelle_text,
    je_phaenomen,
    tabellen,
    zerfaserung,
)
from tests.regression.suche_testset import (
    FAELLE,
    FORMEN,
    PHAENOMENE,
    QUELLEN,
    Fall,
)
from utils.text_normalisierung import text_normalisiert

REPO_WURZEL = next((p for p in Path(__file__).parents if (p / "mvp").is_dir()), None)
SEED_V1 = REPO_WURZEL / "mvp" / "data" / "seed" / "v1.0" if REPO_WURZEL else None
DOKU = Path(__file__).parents[1] / "regression" / "SUCHTESTSET.md"
OHNE_ERWARTUNG = {"verneinung", "fremd"}


class TestAufbau:
    def test_ids_eindeutig_und_fortlaufend(self):
        ids = [f.id for f in FAELLE]
        assert ids == [f"S{i:02d}" for i in range(1, len(FAELLE) + 1)]

    def test_felder_aus_den_erlaubten_werten(self):
        assert all(f.form in FORMEN for f in FAELLE)
        assert all(f.phaenomen in PHAENOMENE for f in FAELLE)
        assert all(f.quelle in QUELLEN for f in FAELLE)

    def test_keine_suchanfrage_doppelt(self):
        normalformen = Counter(text_normalisiert(f.anfrage) for f in FAELLE)
        assert [t for t, n in normalformen.items() if n > 1] == []

    def test_verneinung_und_fremd_erwarten_keinen_treffer_alle_anderen_einen(self):
        for fall in FAELLE:
            assert (not fall.erwartet) == (fall.phaenomen in OHNE_ERWARTUNG), fall.id

    def test_dieselbe_behauptung_nur_bei_saetzen_mit_erwartung(self):
        for fall in FAELLE:
            if fall.dieselbe_behauptung:
                assert fall.erwartet and fall.form == "satz", fall.id

    def test_umfang(self):
        """Etwa 30 Suchanfragen; ausdruecklich mit Tippfehlern, Umgangssprache,
        Schlagwoertern und Verneinungen (Kommentar zu #346 vom 28.10.2026)."""
        assert len(FAELLE) >= 30
        je_phaenomen_ = Counter(f.phaenomen for f in FAELLE)
        for phaenomen in ("tippfehler", "umgangssprache", "schlagwort", "verneinung"):
            assert je_phaenomen_[phaenomen] >= 3, phaenomen
        assert sum(1 for f in FAELLE if not f.erwartet) >= 5
        assert sum(1 for f in FAELLE if f.dieselbe_behauptung) >= 10
        assert {f.form for f in FAELLE} == set(FORMEN)


def _seed_aussagen() -> set:
    texte = set()
    for datei in sorted(SEED_V1.glob("statements_with_*/*.json")):
        for eintrag in json.loads(datei.read_text(encoding="utf-8")):
            texte.add(eintrag.get("text") or eintrag.get("statement"))
    return texte


@pytest.mark.skipif(SEED_V1 is None, reason="Seed nicht im Checkout")
class TestBezugZumSeed:
    def test_erwartete_aussagen_stehen_woertlich_im_seed(self):
        """Der Testbestand ist der Seed; sonst misst das Set ins Leere."""
        seed = _seed_aussagen()
        fehlend = {t for f in FAELLE for t in f.erwartet} - seed
        assert fehlend == set()

    def test_woertliche_faelle_sind_seed_aussagen(self):
        seed = {text_normalisiert(t) for t in _seed_aussagen()}
        for fall in FAELLE:
            if fall.quelle == "seed":
                assert text_normalisiert(fall.anfrage) in seed, fall.id


# ---------------------------------------------------------------------- #
# Auswertung an Hand gebauter Messungen
# ---------------------------------------------------------------------- #

A = "Windräder töten die Vögel!"


def _fall(id_="X01", erwartet=(A,), dieselbe=False, phaenomen="umformulierung"):
    return Fall(id_, "Anfrage", "satz", phaenomen, erwartet, dieselbe, "eigen")


def _k(schwellenwert, passt, rangwert=None, aussage=A, id_=None):
    return Kandidat(
        beitrag_id=id_ or f"b{schwellenwert}{passt}",
        typ="commentary",
        aussage_text=aussage,
        schwellenwert=schwellenwert,
        rangwert=schwellenwert if rangwert is None else rangwert,
        passt=passt,
    )


class TestAuswertung:
    def test_angezeigt_nur_ueber_der_schwelle_nach_rang_und_hoechstens_k(self):
        direkt = _k(0.9, False, rangwert=0.63, aussage="")
        auf_der_schwelle = _k(0.8, True)
        oben, mitte = _k(0.85, True), _k(0.82, False)

        gezeigt = angezeigt([mitte, direkt, auf_der_schwelle, oben], 0.8, k=2)

        # Wie die Suche: "<= Schwelle" faellt weg, ein direkter Treffer steht mit
        # seinem gedaempften Rang hinten, obwohl sein Rohscore hoeher ist.
        assert gezeigt == [oben, mitte]

    @pytest.mark.parametrize(
        "erwartet, kandidaten, einordnung",
        [
            ((A,), [_k(0.9, True), _k(0.85, False)], "treffer"),
            ((A,), [_k(0.9, False), _k(0.85, True)], "fehltreffer"),
            ((A,), [], "keine"),
            ((), [_k(0.9, False)], "fehltreffer"),
            ((), [], "keine"),
        ],
        ids=[
            "erster-passt",
            "erster-passt-nicht",
            "nichts",
            "ohne-erwartung-etwas",
            "ohne-erwartung-nichts",
        ],
    )
    def test_einordnen(self, erwartet, kandidaten, einordnung):
        assert einordnen(_fall(erwartet=erwartet), kandidaten) == einordnung

    def _messungen(self):
        return [
            FallMessung(_fall("X01"), (_k(0.9, True), _k(0.81, False)), (), None),
            FallMessung(_fall("X02"), (_k(0.85, False), _k(0.82, True)), (), None),
            FallMessung(_fall("X03"), (_k(0.7, True),), (), None),
            FallMessung(
                _fall("X04", erwartet=(), phaenomen="fremd"),
                (_k(0.83, False),),
                (),
                None,
            ),
            # Aussage fehlt im Bestand: zaehlt nirgends mit.
            FallMessung(_fall("X05"), (_k(0.95, False),), (A,), None),
        ]

    def test_auswerten_zaehlt_je_fall_und_je_beitrag(self):
        a = auswerten(self._messungen(), 0.8)

        assert (a.faelle, a.mit_erwartung, a.ohne_erwartung) == (4, 3, 1)
        assert (a.treffer, a.fehltreffer, a.keine) == (1, 1, 1)
        assert (a.ohne_richtig_keine, a.ohne_fehltreffer) == (0, 1)
        # Angezeigt: X01 zwei, X02 zwei, X04 einer; passend zwei davon.
        assert a.praezision == pytest.approx(2 / 5)
        # X01 und X02 haben einen passenden unter den ersten k, X03 nicht.
        assert a.recall_at_k == pytest.approx(2 / 3)

    def test_hoehere_schwelle_zeigt_weniger(self):
        a = auswerten(self._messungen(), 0.84)

        assert (a.treffer, a.fehltreffer, a.keine) == (1, 1, 1)
        assert (a.ohne_richtig_keine, a.ohne_fehltreffer) == (1, 0)
        assert a.recall_at_k == pytest.approx(1 / 3)

    def test_ohne_angezeigte_beitraege_keine_praezision(self):
        a = auswerten(self._messungen(), 0.99)

        assert a.praezision is None
        assert a.keine == 3

    def test_je_phaenomen(self):
        tabelle = je_phaenomen(self._messungen(), 0.8)

        assert tabelle == {
            "umformulierung": {"treffer": 1, "fehltreffer": 1, "keine": 1},
            "fremd": {"treffer": 0, "fehltreffer": 1, "keine": 0},
        }

    def test_zerfaserung(self):
        messungen = [
            FallMessung(_fall("X01", dieselbe=True), (_k(0.9, True),), (), True),
            FallMessung(_fall("X02", dieselbe=True), (_k(0.9, True),), (), False),
            FallMessung(_fall("X03", dieselbe=True), (_k(0.7, True),), (), False),
            FallMessung(_fall("X04", dieselbe=True), (), (), True),
            FallMessung(_fall("X05"), (), (), None),
        ]

        z = zerfaserung(messungen, 0.8)

        assert (z.dieselbe_behauptung, z.davon_neu) == (4, 2)
        assert (z.ohne_treffer, z.ohne_treffer_dieselbe, z.ohne_treffer_neu) == (
            3,
            2,
            1,
        )

    def test_ausgabe_ist_als_vorlaeufig_gekennzeichnet(self):
        text = tabellen(self._messungen(), (0.8, 0.84), aktuell=0.8)

        assert text.startswith(VORLAEUFIG)
        assert "#288" in VORLAEUFIG
        assert "| 0.80 (heute) |" in text
        assert "X05" in text  # nicht gemessen, mit Grund

    def test_faelle_text_und_json(self):
        messungen = self._messungen()

        assert "| X01 | umformulierung | treffer |" in faelle_text(messungen, 0.8)
        daten = als_json(messungen, (0.8,))
        assert daten["hinweis"] == VORLAEUFIG
        assert [f["id"] for f in daten["faelle"]] == [m.fall.id for m in messungen]
        assert daten["auswertung"][0]["treffer"] == 1
        json.dumps(daten)


class TestDoku:
    def test_doku_nennt_den_befehl_zum_neu_messen(self):
        text = DOKU.read_text(encoding="utf-8")
        assert "python -m tests.regression.suche_messen" in text
        assert "#288" in text
