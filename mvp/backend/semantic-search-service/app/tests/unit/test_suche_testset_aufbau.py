"""
Suchtestset (tests/regression/suche_testset.py) ohne Stack: Aufbau, Umfang, Bezug zum
Seed und die Auswertung von suche_messen.py an kleinen, von Hand gebauten Messungen.
Gemessen gegen einen Stack wird mit `python -m tests.regression.suche_messen`
(SUCHTESTSET.md).
"""

import asyncio
import json
import uuid
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from domain.models.content_type import ContentType
from tests.regression import suche_messen
from tests.regression.aehnlichkeit_messen import VORSCHLAG_SCHWELLE
from tests.regression.suche_messen import (
    AEHNLICHE_AB,
    AEHNLICHE_ANZAHL,
    BESTAND_PASST_NICHT,
    HINWEIS,
    AehnlicheAussagen,
    AngezeigterBeitrag,
    FallMessung,
    _Erwartung,
    aehnliche_aussagen,
    als_json,
    angezeigte_beitraege,
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
    SEED,
    STARTBESTAND,
    Fall,
    am_seed_gemessen,
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
    def test_erwartete_aussagen_stehen_woertlich_im_seed_oder_im_startbestand(self):
        """Gemessen wird am Seed und am Startbestand; sonst misst das Set ins Leere."""
        bekannt = _seed_aussagen() | set(STARTBESTAND)
        texte = {t for f in FAELLE for t in f.erwartet + f.nur_mit + f.nur_ohne}
        assert texte - bekannt == set()

    def test_woertliche_faelle_sind_seed_aussagen(self):
        seed = {text_normalisiert(t) for t in _seed_aussagen()}
        for fall in FAELLE:
            if fall.quelle == "seed":
                assert text_normalisiert(fall.anfrage) in seed, fall.id

    def test_woertliche_faelle_aus_dem_startbestand(self):
        start = {text_normalisiert(t) for t in STARTBESTAND}
        for fall in FAELLE:
            if fall.quelle == "start":
                assert text_normalisiert(fall.anfrage) in start, fall.id

    def test_startbestand_hat_30_aussagen_und_zwoelf_des_seeds(self):
        assert len(set(STARTBESTAND)) == len(STARTBESTAND) == 30
        assert len(set(STARTBESTAND) & _seed_aussagen()) == 12

    def test_seed_im_set_ist_der_seed(self):
        """am_seed_gemessen() rechnet mit SEED; der muss zum Seed im Checkout passen."""
        assert set(SEED) == _seed_aussagen()

    def test_faelle_zum_startbestand_zaehlen_am_seed_nicht(self):
        """Das Soll des naechtlichen Laufs (gemessen am Seed) bleibt, wenn Faelle zum
        Startbestand dazukommen; die Zahl gegen das Soll prueft test_nachtlauf.py."""
        assert not any(am_seed_gemessen(f) for f in FAELLE if f.quelle == "start")


# ---------------------------------------------------------------------- #
# Auswertung an Hand gebauter Messungen
# ---------------------------------------------------------------------- #

A = "Windräder töten die Vögel!"


def _fall(id_="X01", erwartet=(A,), dieselbe=False, phaenomen="umformulierung"):
    return Fall(id_, "Anfrage", "satz", phaenomen, erwartet, dieselbe, "eigen")


def _k(passt, aussage=A, score=0.9):
    return AngezeigterBeitrag(
        beitrag_id=f"b{score}{passt}{aussage[:3]}",
        typ="commentary",
        aussage_text=aussage,
        score=score,
        passt=passt,
    )


def _m(fall, je_schwelle, fehlt=(), landet=None, aehnliche=()):
    return FallMessung(fall, je_schwelle, fehlt, landet, aehnliche)


class TestAuswertung:
    @pytest.mark.parametrize(
        "erwartet, gezeigt, einordnung",
        [
            ((A,), [_k(True), _k(False)], "treffer"),
            ((A,), [_k(False), _k(True)], "fehltreffer"),
            ((A,), [], "keine"),
            ((), [_k(False)], "fehltreffer"),
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
    def test_einordnen(self, erwartet, gezeigt, einordnung):
        assert einordnen(_fall(erwartet=erwartet), gezeigt) == einordnung

    def _messungen(self):
        direkt_passend = _k(True, aussage="", score=0.6)
        return [
            _m(_fall("X01"), {0.8: (_k(True), _k(False)), 0.84: (_k(True),)}),
            _m(_fall("X02"), {0.8: (_k(False), direkt_passend), 0.84: (_k(False),)}),
            _m(_fall("X03"), {0.8: (), 0.84: ()}),
            _m(
                _fall("X04", erwartet=(), phaenomen="fremd"),
                {0.8: (_k(False, aussage=""),), 0.84: ()},
            ),
            # Aussage fehlt im Bestand: zaehlt nirgends mit.
            _m(_fall("X05"), {0.8: (_k(False),), 0.84: (_k(False),)}, fehlt=(A,)),
            # Fremd, aber der Bestand hat eine Aussage dazu (nur_ohne): ebenso.
            _m(
                _fall("X06", erwartet=(), phaenomen="fremd"),
                {0.8: (_k(False),), 0.84: (_k(False),)},
            )._replace(ausgeschlossen=(A,)),
        ]

    def test_auswerten_zaehlt_je_fall_und_je_beitrag(self):
        a = auswerten(self._messungen(), 0.8)

        assert (a.faelle, a.mit_erwartung, a.ohne_erwartung) == (4, 3, 1)
        assert (a.treffer, a.fehltreffer, a.keine) == (1, 1, 1)
        assert (a.ohne_richtig_keine, a.ohne_fehltreffer) == (0, 1)
        # Angezeigt: X01 zwei, X02 zwei, X04 einer; passend zwei davon.
        assert a.praezision == pytest.approx(2 / 5)
        # X01 und X02 haben einen passenden Beitrag, X03 nicht.
        assert a.recall_seite == pytest.approx(2 / 3)
        # Unter den ersten 5 bzw. 10: X01 auf Platz 1, X02 auf Platz 2.
        assert a.recall_bei == {5: pytest.approx(2 / 3), 10: pytest.approx(2 / 3)}
        assert (a.direkt_passend, a.direkt_angezeigt) == (1, 2)

    def test_andere_schwelle_andere_anzeige(self):
        a = auswerten(self._messungen(), 0.84)

        assert (a.treffer, a.fehltreffer, a.keine) == (1, 1, 1)
        assert (a.ohne_richtig_keine, a.ohne_fehltreffer) == (1, 0)
        assert a.recall_seite == pytest.approx(1 / 3)

    def test_recall_bei_k_zaehlt_nur_die_ersten_k_der_ergebnisseite(self):
        weit_hinten = (_k(False, score=0.99),) * 5 + (_k(True),)
        a = auswerten([_m(_fall("X01"), {0.8: weit_hinten})], 0.8)

        assert a.recall_bei == {5: 0.0, 10: 1.0}
        assert a.recall_seite == 1.0

    def test_nicht_gemessene_schwelle_ist_ein_fehler(self):
        with pytest.raises(KeyError):
            auswerten(self._messungen(), 0.9)

    def test_ohne_angezeigte_beitraege_keine_praezision(self):
        leer = [_m(_fall("X01"), {0.8: ()})]

        assert auswerten(leer, 0.8).praezision is None

    def test_je_phaenomen(self):
        tabelle = je_phaenomen(self._messungen(), 0.8)

        assert tabelle == {
            "umformulierung": {
                "treffer": 1,
                "fehltreffer": 1,
                "keine": 1,
                "mit_erwartung": 3,
                "gefunden@10": 2,
            },
            "fremd": {
                "treffer": 0,
                "fehltreffer": 1,
                "keine": 0,
                "mit_erwartung": 0,
                "gefunden@10": 0,
            },
        }

    def test_zerfaserung(self):
        gefunden = {0.8: (_k(True),)}
        messungen = [
            _m(_fall("X01", dieselbe=True), gefunden, landet=True),
            _m(_fall("X02", dieselbe=True), gefunden, landet=False),
            _m(_fall("X03", dieselbe=True), {0.8: ()}, landet=False),
            _m(_fall("X04", dieselbe=True), {0.8: ()}, landet=True),
            # Nicht geprueft (None) zaehlt nicht als neu.
            _m(_fall("X05", dieselbe=True), {0.8: ()}, landet=None),
            _m(_fall("X06"), {0.8: ()}),
        ]

        z = zerfaserung(messungen, 0.8)

        assert (z.dieselbe_behauptung, z.davon_neu) == (5, 2)
        assert (z.ohne_treffer, z.ohne_treffer_dieselbe, z.ohne_treffer_neu) == (
            4,
            3,
            1,
        )

    def test_aehnliche_aussagen(self):
        messungen = [
            _m(_fall("X01"), {0.8: ()}, aehnliche=(False, True)),
            _m(_fall("X02"), {0.8: ()}, aehnliche=(False,)),
            _m(_fall("X03"), {0.8: ()}),
            _m(
                _fall("X04", erwartet=(), phaenomen="fremd"),
                {0.8: ()},
                aehnliche=(False,),
            ),
            _m(_fall("X05", erwartet=(), phaenomen="fremd"), {0.8: ()}),
            # Aussage fehlt im Bestand: zaehlt nicht mit.
            _m(_fall("X06"), {0.8: ()}, fehlt=(A,), aehnliche=(True,)),
        ]

        assert aehnliche_aussagen(messungen) == AehnlicheAussagen(
            mit_erwartung=3,
            erwartete_dabei=1,
            ohne_erwartung=2,
            ohne_mit_vorschlag=1,
        )

    def test_aehnliche_aussagen_wie_im_beitragsformular(self):
        """Anzahl wie VORSCHLAG_ANZAHL im Frontend, untere Grenze wie die Vorschlagsschwelle
        des Dienstes (aussage_vorschlag_schwelle, #387) und VORSCHLAG_SCHWELLE im Messset.
        """
        if REPO_WURZEL is None:
            pytest.skip("Frontend nicht im Checkout")
        ts = (
            REPO_WURZEL
            / "mvp/frontend/gutgesagt-frontend/src/app/services/statement.service.ts"
        ).read_text(encoding="utf-8")

        assert f"VORSCHLAG_ANZAHL = {AEHNLICHE_ANZAHL};" in ts
        assert "VORSCHLAG_MIN_AEHNLICHKEIT" not in ts
        assert AEHNLICHE_AB == VORSCHLAG_SCHWELLE

    def test_ausgabe_nennt_wo_bewertet_ist_und_was_nicht_gemessen_wurde(self):
        text = tabellen(self._messungen(), (0.8, 0.84), aktuell=0.8)

        assert text.startswith(HINWEIS)
        assert "#288" in HINWEIS and "Startbestand" in HINWEIS
        assert "| 0.80 (heute) |" in text
        assert "- X05: " in text.split("Aussage fehlt im Bestand")[1]
        assert "- X06: " in text.split("der Bestand hat eine Aussage dazu")[1]

    def test_faelle_text_und_json(self):
        messungen = self._messungen()

        text = faelle_text(messungen, 0.8)
        assert "| X01 | umformulierung | treffer |" in text
        assert "direkt (2)" in text  # X02: erster passender auf Platz 2
        with patch.object(suche_messen, "schwelle_heute", return_value=0.8):
            daten = als_json(messungen, (0.8,), umgebung={"modell": "m"})
        assert daten["hinweis"] == HINWEIS
        assert daten["umgebung"] == {"modell": "m"}
        assert [f["id"] for f in daten["faelle"]] == [m.fall.id for m in messungen]
        assert daten["auswertung"][0]["treffer"] == 1
        # Fuer Vergleiche je Phaenomen (Stemmer, Verneinung) ohne das Set zu laden.
        x02 = daten["faelle"][1]
        assert (x02["phaenomen"], x02["erwartet"]) == ("umformulierung", [A])
        assert x02["einordnung"]["0.80"] == "fehltreffer"
        assert daten["je_phaenomen"]["fremd"]["fehltreffer"] == 1
        json.dumps(daten)

    def test_main_meldet_wenn_kein_fall_mit_erwartung_gemessen_ist(self, capsys):
        """Leere oder falsche Sammlung, Startbestand ohne passende Faelle: Exit-Code
        statt Zahlen, die nach einer Messung aussehen (naechtlicher Lauf, #391)."""
        alle_fehlen = [m._replace(fehlt=(A,)) for m in self._messungen()]

        with patch.object(
            suche_messen, "messen", AsyncMock(return_value=alle_fehlen)
        ), patch("core.logging.initialize_logging"):
            code = suche_messen.main(["--schwellen", "0.8,0.84"])

        assert code == BESTAND_PASST_NICHT
        assert "Kein Fall mit Erwartung" in capsys.readouterr().err


class TestAngezeigteBeitraege:
    """Was die Ergebnisseite aus dem Ergebnis des Orchestrators zeigt."""

    @staticmethod
    def _spec(typ, feld):
        return SimpleNamespace(content_type=typ, result_field=feld)

    @staticmethod
    def _treffer(feld, beitrag_id, aussage_id=None, score=0.9):
        return SimpleNamespace(
            **{feld: SimpleNamespace(id=beitrag_id)},
            statement_id=aussage_id,
            statement_text="Aussage" if aussage_id else None,
            score=score,
        )

    def test_reihenfolge_der_ergebnisseite_ohne_bilder_und_passt(self):
        erwartete_aussage, andere_aussage = uuid.uuid4(), uuid.uuid4()
        specs = [
            self._spec(ContentType.POST, "post_result"),
            self._spec(ContentType.IMAGE, "image_result"),
            self._spec(ContentType.GENERIC_TEXT, "generictext_result"),
            self._spec(ContentType.COMMENTARY, "commentary_result"),
        ]
        ergebnis = {
            ContentType.POST: [self._treffer("post_result", "p1", andere_aussage)],
            ContentType.IMAGE: [self._treffer("image_result", "b1", erwartete_aussage)],
            ContentType.GENERIC_TEXT: [
                self._treffer("generictext_result", "h1", erwartete_aussage)
            ],
            ContentType.COMMENTARY: [
                # Direkt gefunden, haengt aber an der erwarteten Aussage.
                self._treffer("commentary_result", "k1"),
                self._treffer("commentary_result", "k2"),
            ],
        }
        orchestrator = SimpleNamespace(results_for=lambda typ: ergebnis[typ])
        erwartung = _Erwartung(
            aussage_ids=frozenset({str(erwartete_aussage)}),
            beitrag_ids=frozenset({"k1"}),
            fehlt=(),
        )

        gezeigt = angezeigte_beitraege(orchestrator, specs, erwartung)

        assert [(b.beitrag_id, b.passt) for b in gezeigt] == [
            ("k1", True),
            ("k2", False),
            ("h1", True),
            ("p1", False),
        ]
        assert gezeigt[0].aussage_text == ""  # direkter Treffer
        assert gezeigt[2].aussage_text == "Aussage"


class TestErwartung:
    """Welche Aussagen eines Falls im Bestand stehen, fehlen oder ihn ausschliessen."""

    @staticmethod
    def _erwartung(fall, bestand):
        aussagen = {
            t: SimpleNamespace(id=f"id-{t}", replysuggestions=[SimpleNamespace(id="k")])
            for t in bestand
        }
        im_bestand = AsyncMock(side_effect=lambda _dienste, t: aussagen.get(t))
        with patch.object(suche_messen, "_aussage_im_bestand", im_bestand):
            return asyncio.run(suche_messen._erwartung(None, fall, {}))

    def test_nur_mit_fehlt_dann_zaehlt_der_fall_nicht(self):
        fall = _fall(erwartet=(), phaenomen="verneinung")._replace(nur_mit=("B",))

        assert self._erwartung(fall, {A}).fehlt == ("B",)
        assert self._erwartung(fall, {A, "B"}).fehlt == ()

    def test_nur_ohne_im_bestand_schliesst_den_fall_aus(self):
        fall = _fall(erwartet=(), phaenomen="fremd")._replace(nur_ohne=("W",))

        assert self._erwartung(fall, {A, "W"}).ausgeschlossen == ("W",)
        assert self._erwartung(fall, {A}).ausgeschlossen == ()

    def test_nicht_gezaehlter_fall_sucht_nicht(self):
        """Am Seed zaehlen die Faelle zum Startbestand nicht: keine Suche je Schwelle."""
        erwartung = _Erwartung(
            frozenset(), frozenset(), fehlt=(), ausgeschlossen=("W",)
        )
        suche = AsyncMock()
        with patch.object(
            suche_messen, "_erwartung", AsyncMock(return_value=erwartung)
        ), patch("api.v1.search.aussagetreffer_finden", suche):
            messung = asyncio.run(
                suche_messen.fall_messen(None, _fall(erwartet=()), (0.8, 0.84))
            )

        suche.assert_not_called()
        assert messung.ausgeschlossen == ("W",)
        assert messung.angezeigt == {}
        assert als_json([messung], (0.8,))["faelle"][0]["einordnung"] == {}
        assert suche_messen.gemessen([messung]) == []

    def test_erwartete_aussagen_wie_bisher(self):
        erwartung = self._erwartung(_fall(erwartet=(A, "B")), {A})

        assert erwartung.aussage_ids == frozenset({f"id-{A}"})
        assert erwartung.beitrag_ids == frozenset({"k"})
        assert erwartung.fehlt == ("B",)


class TestDoku:
    def test_doku_nennt_den_befehl_zum_neu_messen(self):
        text = DOKU.read_text(encoding="utf-8")
        assert "python -m tests.regression.suche_messen" in text
        assert "#288" in text
