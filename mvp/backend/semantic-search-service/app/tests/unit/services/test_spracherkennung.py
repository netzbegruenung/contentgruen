"""
Spracherkennung beim Schreiben (#405): ein Sprachhinweis, wenn ein Beitrag oder eine
Aussage offenbar nicht deutsch ist.

Die Regeln (Mindestlänge, Schwelle) laufen gegen einen festen Erkenner. Die Klasse
``TestMitLingua`` prüft dieselben Fälle gegen das echte Lingua; fehlt es (etwa auf einer
Dev-VM, auf der requirements.txt noch nicht nachinstalliert ist), wird sie mit Grund
übersprungen, in der CI (`CI` gesetzt) scheitert sie stattdessen (TESTING_GUIDE.md).
"""

import importlib.util
import os

import pytest

from services.spracherkennung.spracherkennung import (
    MIN_WOERTER,
    Spracherkennung,
)

pytestmark = [pytest.mark.unit]

ENGLISCH = "Heat pumps are far too expensive for ordinary families."
DEUTSCH = "Wärmepumpen sind für normale Familien viel zu teuer."


class _FesterErkenner:
    """Gibt immer dieselben Werte zurück und merkt sich, ob er gefragt wurde."""

    def __init__(self, werte):
        self.werte = werte
        self.gefragt = []

    def __call__(self, text):
        self.gefragt.append(text)
        return self.werte


def _erkennung(werte):
    erkenner = _FesterErkenner(werte)
    return Spracherkennung(lambda: erkenner), erkenner


class TestRegeln:
    def test_meldet_fremde_sprache_ab_mindestlaenge(self):
        erkennung, _ = _erkennung({"en": 0.9, "de": 0.05, "fr": 0.05})

        assert erkennung.fremdsprache(ENGLISCH) == "en"

    def test_deutsch_ohne_hinweis(self):
        erkennung, _ = _erkennung({"de": 0.95, "en": 0.05})

        assert erkennung.fremdsprache(DEUTSCH) is None

    def test_kurzer_text_ohne_hinweis_und_ohne_erkennung(self):
        # Auf einzelnen Wörtern ist die Erkennung unsicher (74 % für Deutsch): gar nicht fragen.
        erkennung, erkenner = _erkennung({"en": 1.0})
        kurz = " ".join(["word"] * (MIN_WOERTER - 1))

        assert erkennung.fremdsprache(kurz) is None
        assert erkenner.gefragt == []

    def test_zahlen_und_zeichen_zaehlen_nicht_als_woerter(self):
        erkennung, erkenner = _erkennung({"en": 1.0})

        assert erkennung.fremdsprache("2030 – 80 % 🌍 CO2 #klima") is None
        assert erkenner.gefragt == []

    def test_unsicher_zwischen_deutsch_und_anderer_sprache_ohne_hinweis(self):
        # Deutsch ist nicht vorn, aber auch nicht abwegig: lieber kein Hinweis.
        erkennung, _ = _erkennung({"en": 0.55, "de": 0.45})

        assert erkennung.fremdsprache(ENGLISCH) is None

    def test_ohne_ergebnis_ohne_hinweis(self):
        erkennung, _ = _erkennung({})

        assert erkennung.fremdsprache(ENGLISCH) is None

    def test_erkenner_wird_einmal_gebaut(self):
        gebaut = []

        def bauen():
            gebaut.append(1)
            return lambda text: {"de": 1.0}

        erkennung = Spracherkennung(bauen)
        erkennung.laden()
        erkennung.fremdsprache(DEUTSCH)
        erkennung.fremdsprache(DEUTSCH)

        assert gebaut == [1]


def _lingua_fehlt():
    if importlib.util.find_spec("lingua") is None:
        return "lingua nicht installiert: pip install -r requirements.txt"
    return None


_GRUND = _lingua_fehlt()


@pytest.fixture(scope="module")
def lingua():
    if _GRUND is not None:
        if os.environ.get("CI"):
            pytest.fail(_GRUND, pytrace=False)
        pytest.skip(_GRUND)
    erkennung = Spracherkennung()
    erkennung.laden()
    return erkennung


class TestMitLingua:
    @pytest.mark.parametrize(
        "text",
        [
            DEUTSCH,
            "Die Grünen wollen uns das Autofahren verbieten.",
            "Wer heute dämmt, spart morgen Heizkosten.",
            "Windräder liefern günstigen Strom, auch für die Industrie.",
            # Anglizismen und ein englisches Zitat machen einen Text nicht englisch.
            "Das Narrativ vom Fake-Klimaschutz ist ein Framing der Lobby.",
            "Sie sagen „green deal“, meinen aber höhere Preise für alle.",
            "Der Bericht sagt: „We need more wind power now“, und das stimmt auch für uns.",
            "Ein Tempolimit rettet Leben und kostet fast nichts.",
        ],
    )
    def test_deutsch_ohne_hinweis(self, lingua, text):
        assert lingua.fremdsprache(text) is None

    @pytest.mark.parametrize(
        "text, sprache",
        [
            (ENGLISCH, "en"),
            ("The Greens want to ban cars and raise taxes for everyone.", "en"),
            ("Les Verts veulent interdire les voitures dans les villes.", "fr"),
            ("Yeşiller herkes için vergileri artırmak istiyor.", "tr"),
            # Mit nur vier Sprachen hielt Lingua diese beiden für Deutsch.
            ("Los Verdes quieren prohibir los coches en las ciudades.", "es"),
            ("De Groenen willen auto's in de steden verbieden.", "nl"),
            ("I Verdi vogliono vietare le auto nelle città italiane.", "it"),
            ("Zieloni chcą zakazać samochodów w miastach i podnieść podatki.", "pl"),
            ("Зелёные хотят запретить автомобили в городах.", "ru"),
            ("الخضر يريدون حظر السيارات في المدن الكبيرة", "ar"),
        ],
    )
    def test_fremde_sprache_mit_hinweis(self, lingua, text, sprache):
        assert lingua.fremdsprache(text) == sprache

    def test_kurz_ohne_hinweis(self, lingua):
        assert lingua.fremdsprache("Heat pumps are expensive") is None
