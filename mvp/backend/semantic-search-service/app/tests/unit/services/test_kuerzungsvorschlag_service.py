"""
Kürzungsvorschlag (#403): eine Kurzfassung aus den eigenen Sätzen eines Kommentars.

Die Tests laufen gegen das echte Sprachmodell. Fehlt es (etwa auf einer Dev-VM, auf der
requirements.txt noch nicht nachinstalliert ist), werden sie mit Grund übersprungen; in
der CI (`CI` gesetzt) scheitern sie stattdessen (TESTING_GUIDE.md).
"""

import importlib.util
import os
import re

import pytest

from services.gegenlesen.gegenlesen_service import SPACY_MODELL, Sprachwerkzeuge
from dtos.commentary import KURZFASSUNG_MAX
from services.kuerzungsvorschlag_service import KuerzungsvorschlagService

pytestmark = [pytest.mark.unit]


def _was_fehlt():
    for paket in ("spacy", SPACY_MODELL):
        if importlib.util.find_spec(paket) is None:
            return paket
    return None


_FEHLT = _was_fehlt()
if _FEHLT is not None:
    _GRUND = f"{_FEHLT} nicht installiert: pip install -r requirements.txt"
    if os.environ.get("CI"):
        pytest.fail(_GRUND, pytrace=False)
    pytest.skip(_GRUND, allow_module_level=True)


@pytest.fixture(scope="module")
def service():
    return KuerzungsvorschlagService(werkzeuge=Sprachwerkzeuge())


def _woerter(text):
    return re.findall(r"\w[\w-]*", text)


def _ist_teilfolge(kurz, lang):
    """Jedes Wort des Vorschlags kommt im Original vor, in derselben Reihenfolge."""
    rest = iter(_woerter(lang))
    return all(wort in rest for wort in _woerter(kurz))


#: Ein langer Kommentar (länger als die Kurzfassung) mit Einschüben, Verneinung und Zahlen.
LANG = (
    "Die Wärmepumpe, die im Keller steht, spart im Winter viel Geld. "
    "Robert, unser Nachbar, heizt seit 2021 nicht mehr mit Öl (das war ihm zu teuer). "
    "Das Heizungsgesetz ist kein Verbot – es gibt lange Übergangsfristen – sondern ein "
    "Fahrplan für die Wärmepumpe. "
    "Ich habe übrigens gestern lange mit meiner Tante telefoniert, die gerade aus dem "
    "Urlaub in Italien zurückgekommen ist und viel erzählt hat."
)


class TestNurWoerterDesOriginals:
    def test_vorschlag_besteht_nur_aus_woertern_des_originals_in_reihenfolge(
        self, service
    ):
        vorschlag = service.vorschlagen(LANG, aussage="Wärmepumpen sind zu teuer")

        assert vorschlag
        assert _ist_teilfolge(vorschlag, LANG)

    def test_vorschlag_passt_in_die_kurzfassung(self, service):
        vorschlag = service.vorschlagen(LANG, aussage=None)

        assert vorschlag
        assert len(vorschlag) <= KURZFASSUNG_MAX
        assert len(vorschlag) < len(LANG)

    def test_leerer_text_ergibt_keinen_vorschlag(self, service):
        assert service.vorschlagen("   ", aussage=None) is None


class TestEinschuebeFallenWeg:
    def test_relativsatz_faellt_weg_samt_kommas(self, service):
        vorschlag = service.vorschlagen(
            "Die Wärmepumpe, die im Keller steht, spart viel Geld.", aussage=None
        )

        assert vorschlag == "Die Wärmepumpe spart viel Geld."

    def test_apposition_faellt_weg(self, service):
        vorschlag = service.vorschlagen(
            "Robert, unser Nachbar, heizt mit Strom.", aussage=None
        )

        assert vorschlag == "Robert heizt mit Strom."

    def test_klammer_faellt_weg(self, service):
        vorschlag = service.vorschlagen(
            "Er heizt mit Strom (das ist gut für das Klima).", aussage=None
        )

        assert vorschlag == "Er heizt mit Strom."

    def test_einschub_zwischen_gedankenstrichen_faellt_weg(self, service):
        vorschlag = service.vorschlagen(
            "Das Gesetz ist ein Fahrplan – es gibt lange Fristen – für alle Häuser.",
            aussage=None,
        )

        assert vorschlag == "Das Gesetz ist ein Fahrplan für alle Häuser."

    def test_bindestrich_mit_leerzeichen_ist_kein_einschub(self, service):
        text = "Das Ost - West - Problem bleibt."

        assert service.vorschlagen(text, aussage=None) == text

    def test_verschachtelte_klammer_faellt_ganz_weg(self, service):
        vorschlag = service.vorschlagen(
            "Die Pumpe (sie ist (fast) leise) spart Geld.", aussage=None
        )

        assert vorschlag == "Die Pumpe spart Geld."


class TestVerneinungenUndZahlenBleiben:
    def test_verneinung_im_einschub_bleibt_im_satz(self, service):
        text = "Die Pumpe, die nicht laut ist, spart Geld."

        assert service.vorschlagen(text, aussage=None) == text

    def test_zahl_im_einschub_bleibt_im_satz(self, service):
        text = "Die Förderung, die 2024 kam, deckt die Hälfte."

        assert service.vorschlagen(text, aussage=None) == text

    def test_verneinung_und_zahl_bleiben_im_gekuerzten_vorschlag(self, service):
        vorschlag = service.vorschlagen(LANG, aussage="Wärmepumpen sind zu teuer")

        # Jeder Satz des Vorschlags, der im Original eine Verneinung oder Zahl hatte,
        # hat sie noch.
        for satz, merkmale in (
            ("Robert", ("2021", "nicht")),
            ("Heizungsgesetz", ("kein",)),
        ):
            if satz in vorschlag:
                for merkmal in merkmale:
                    assert merkmal in vorschlag

    @pytest.mark.parametrize(
        "text",
        [
            "Wärmepumpen, die weder laut noch teuer sind, helfen.",
            "Häuser, die kaum Energie brauchen, sparen Geld.",
            "Die Förderung, die die Hälfte deckt, hilft.",
            "Die Pumpe, die zwanzig Prozent spart, hilft.",
        ],
    )
    def test_weitere_verneinungen_und_zahlwoerter_bleiben(self, service, text):
        assert service.vorschlagen(text, aussage=None) == text

    def test_zahl_am_satzende_bleibt_im_satz(self, service):
        # spaCy trennt "2024." als eigenen Satz ab; er gehört zum Satz davor.
        vorschlag = service.vorschlagen(
            "Das Gesetz (§ 71 GEG) gilt ab 2024.", aussage=None
        )

        assert vorschlag is not None
        assert vorschlag.endswith("ab 2024.")


class TestZentraleSaetzeBleiben:
    def test_abschweifender_satz_faellt_zuerst_weg(self, service):
        vorschlag = service.vorschlagen(LANG, aussage="Wärmepumpen sind zu teuer")

        assert "Tante" not in vorschlag
        assert "Wärmepumpe" in vorschlag

    def test_saetze_bleiben_in_originalreihenfolge(self, service):
        vorschlag = service.vorschlagen(LANG, aussage="Wärmepumpen sind zu teuer")
        positionen = [
            LANG.index(w) for w in ("Wärmepumpe", "Heizungsgesetz") if w in vorschlag
        ]

        assert positionen == sorted(positionen)

    def test_abschweifender_satz_fuellt_nicht_auf_wenn_zentrale_zu_lang_sind(
        self, service
    ):
        knapp = KuerzungsvorschlagService(werkzeuge=service._werkzeuge, max_zeichen=60)
        text = (
            "Die Wärmepumpe spart im Winter viel Geld und schont dabei das Klima. "
            "Die Wärmepumpe heizt auch alte Häuser zuverlässig und spart dabei Geld. "
            "Meine Tante war im Urlaub."
        )

        assert knapp.vorschlagen(text, aussage=None) is None

    def test_ohne_passenden_satz_kein_vorschlag(self, service):
        # Kein Satz passt in die Grenze, und abgeschnitten wird nicht.
        knapp = KuerzungsvorschlagService(werkzeuge=service._werkzeuge, max_zeichen=20)

        assert (
            knapp.vorschlagen("Die Wärmepumpe spart viel Geld.", aussage=None) is None
        )
