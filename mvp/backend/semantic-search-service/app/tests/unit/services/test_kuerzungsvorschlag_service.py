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
    def test_relativsatz_bleibt_stehen(self, service):
        # Entscheidung @BanSe 03.11.: Ein Relativsatz kann einschränken ("Nur Häuser,
        # die gedämmt sind, ..."), deshalb fällt er nie weg.
        text = "Nur Häuser, die gedämmt sind, sparen viel Energie."

        assert service.vorschlagen(text, aussage=None) == text

    @pytest.mark.parametrize(
        "text",
        [
            "Die Pumpe (die nur nachts läuft) spart Strom.",
            "Die Pumpe – die nur nachts läuft – spart Strom.",
        ],
    )
    def test_relativsatz_bleibt_auch_in_klammer_und_zwischen_strichen(
        self, service, text
    ):
        assert service.vorschlagen(text, aussage=None) == text

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
        # Die Einschübe ohne Verneinung und Zahl fallen weg, Zahl und Verneinung
        # bleiben in ihrem Satz.
        assert (
            service.vorschlagen(
                "Robert, unser Nachbar, heizt seit 2021 nicht mehr mit Öl "
                "(das war ihm zu teuer).",
                aussage=None,
            )
            == "Robert heizt seit 2021 nicht mehr mit Öl."
        )
        vorschlag = service.vorschlagen(LANG, aussage="Wärmepumpen sind zu teuer")
        assert "Das Heizungsgesetz ist kein Verbot" in vorschlag

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

    @pytest.mark.parametrize(
        "text",
        [
            "Das ist teuer... Die Wärmepumpe spart Geld.",
            "Er sagt: „Das geht.“ Die Wärmepumpe spart Geld.",
            "Ein Absatz ohne Schlusspunkt\n\nDie Wärmepumpe spart Geld.",
        ],
    )
    def test_satzgrenzen_auch_nach_auslassung_zitat_und_absatz(self, service, text):
        # Jeder Satz für sich: Beide zusammen passen nicht in die Grenze, einer allein
        # schon. Verschmolzen gäbe es keinen Vorschlag.
        knapp = KuerzungsvorschlagService(werkzeuge=service._werkzeuge, max_zeichen=35)

        vorschlag = knapp.vorschlagen(text, aussage=None)

        assert vorschlag is not None
        assert vorschlag in text.replace("\n", " ")

    def test_bewertet_wird_der_satz_ohne_seine_einschuebe(self, service):
        # Der erste Satz hat seinen Bezug zur Aussage nur im Einschub, der zweite im
        # Satz selbst; nur einer passt hinein.
        knapp = KuerzungsvorschlagService(werkzeuge=service._werkzeuge, max_zeichen=40)
        text = (
            "Mein Onkel (er kennt die Förderung für Wärmepumpen) fährt Rad. "
            "Die Wärmepumpe spart Geld."
        )

        assert (
            knapp.vorschlagen(text, aussage="Die Förderung für Wärmepumpen reicht")
            == "Die Wärmepumpe spart Geld."
        )

    def test_satz_mit_verneinung_faellt_nie_weg(self, service):
        # Entscheidung @BanSe 03.11.: Ohne den Satz mit der Verneinung kann der
        # Vorschlag das Gegenteil sagen. Er bleibt, auch wenn er wenig zentral ist.
        knapp = KuerzungsvorschlagService(werkzeuge=service._werkzeuge, max_zeichen=60)
        text = (
            "Die Wärmepumpe spart Geld. Die Wärmepumpe heizt gut. "
            "Öl lohnt sich nicht."
        )

        vorschlag = knapp.vorschlagen(text, aussage="Die Wärmepumpe")

        # Ein Wärmepumpen-Satz und der Satz mit Verneinung; beide Wärmepumpen-Sätze
        # passen nicht mehr dazu.
        assert vorschlag.startswith("Die Wärmepumpe ")
        assert vorschlag.endswith(". Öl lohnt sich nicht.")
        assert vorschlag.count("Wärmepumpe") == 1

    def test_passen_die_saetze_mit_verneinung_nicht_kein_vorschlag(self, service):
        knapp = KuerzungsvorschlagService(werkzeuge=service._werkzeuge, max_zeichen=30)
        text = (
            "Öl lohnt sich heute nicht mehr. Gas ist keine gute Lösung. "
            "Die Wärmepumpe spart Geld."
        )

        assert knapp.vorschlagen(text, aussage=None) is None

    def test_ohne_passenden_satz_kein_vorschlag(self, service):
        # Kein Satz passt in die Grenze, und abgeschnitten wird nicht.
        knapp = KuerzungsvorschlagService(werkzeuge=service._werkzeuge, max_zeichen=20)

        assert (
            knapp.vorschlagen("Die Wärmepumpe spart viel Geld.", aussage=None) is None
        )
