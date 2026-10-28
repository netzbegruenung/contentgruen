"""
Regeln fuer den Seed v1.0 unter mvp/data/seed/ (#340, docs/VISION.md "Bestand").

Der Seed ist Testdaten fuer die Entwicklung, nie Bestand in Test oder Produktion.
Er folgt trotzdem den Regeln aus "Ton und Schreiben":

- Nutzung 0: Kein Zaehler ist vorbelegt, ``add_metadata.py`` wuerfelt nichts.
- Nichts erfinden: keine Ich-, Familien- oder Nachbarschaftsgeschichten; eigene
  Erlebnisse nur als Platzhalter "[Hier ein eigenes Erlebnis: …]".
- Kein Sarkasmus: kein Stil "sarkastisch", "bissig" gibt es im Seed nicht.
- Keine echten Personen in Aussagen und Beitraegen.
- Titel: ein Satz mit Haltung, 3-120 Zeichen, keine Frage.
- Ein Hinweis "nur Dev" steht in der README des Seeds.

Die Woerterlisten sind Stolperdraehte, kein Beweis: Sie fangen die Muster, die der
alte KI-Seed hatte. Die Tests mit absichtlichen Verstoessen belegen, dass jede
Regel ihren Fehler meldet.
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO_WURZEL = next((p for p in Path(__file__).parents if (p / "mvp").is_dir()), None)
SEED = REPO_WURZEL / "mvp" / "data" / "seed" if REPO_WURZEL else None
SEED_V1 = SEED / "v1.0" if SEED else None

PLATZHALTER = re.compile(r"\[Hier ein eigenes Erlebnis: [^\]]*\]")
# Woran man eine erfundene Geschichte aus dem eigenen Umfeld erkennt.
ERLEBNIS = re.compile(
    r"\b(mein|meine|meinem|meinen|meiner|unser|unsere|unserem|unserer)\s+"
    r"(Nachbar\w*|Schwager|Schwägerin|Bruder|Schwester|Onkel|Tante|Oma|Opa|"
    r"Eltern|Vater|Mutter|Kolleg\w*|Chef\w*|Förster|Freund\w*|Sohn|"
    r"Tochter|Dorf|Straße|Viertel|Betrieb|Firma)\b"
    r"|\bbei uns (im|in der|auf dem) \w+"
    r"|\b(ging mir|kenne ich|true story)\b",
    re.IGNORECASE,
)
# Personen, die der alte Seed namentlich nannte oder denen er Zitate zuschrieb.
PERSONEN = re.compile(
    r"\b(Habeck|Söder|Baerbock|Lindner|Scholz|Merz|Merkel|Özdemir|Nouripour|"
    r"Kretschmann|Putin|Trump)\b"
)
VERBOTENE_STILE = {"sarkastisch", "bissig"}
TITEL_MIN, TITEL_MAX = 3, 120


def _seed_dateien() -> list[Path]:
    if SEED_V1 is None:
        return []
    return sorted(SEED_V1.glob("statements_with_*/*.json"))


def _beitraege(aussage: dict) -> list[dict]:
    return aussage.get("commentaries", []) + aussage.get("generic_texts", [])


def verstoesse_aussage(aussage: dict) -> list[str]:
    """Alle Regelverstoesse einer Aussage samt ihrer Beitraege."""
    fehler = []
    if PERSONEN.search(aussage["statement"]):
        fehler.append(f"Person in Aussage: {aussage['statement']}")
    if aussage.get("metadata", {}).get("usage_count", 0) != 0:
        fehler.append(f"Nutzung nicht 0: {aussage['statement']}")
    for beitrag in _beitraege(aussage):
        titel = beitrag["title"]
        if beitrag.get("metadata", {}).get("usage_count", 0) != 0:
            fehler.append(f"Nutzung nicht 0: {titel}")
        if beitrag.get("style") in VERBOTENE_STILE:
            fehler.append(f"Stil {beitrag['style']}: {titel}")
        if not TITEL_MIN <= len(titel) <= TITEL_MAX:
            fehler.append(f"Titellaenge {len(titel)}: {titel}")
        if "?" in titel:
            fehler.append(f"Titel ist eine Frage: {titel}")
        for feld in ("title", "text", "short_text", "long_text"):
            text = PLATZHALTER.sub("", beitrag.get(feld) or "")
            if treffer := ERLEBNIS.search(text):
                fehler.append(f"Erlebnis '{treffer.group(0)}' in {feld}: {titel}")
            if treffer := PERSONEN.search(text):
                fehler.append(f"Person '{treffer.group(0)}' in {feld}: {titel}")
    return fehler


def _add_metadata():
    spec = importlib.util.spec_from_file_location(
        "add_metadata", SEED / "add_metadata.py"
    )
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.mark.skipif(SEED is None, reason="Seed nicht im Checkout")
class TestSeedRegeln:
    def test_seed_dateien_vorhanden(self):
        assert _seed_dateien()

    @pytest.mark.parametrize("datei", _seed_dateien(), ids=lambda p: p.name)
    def test_seed_datei_folgt_regeln(self, datei: Path):
        fehler = []
        for aussage in json.loads(datei.read_text(encoding="utf-8")):
            fehler += verstoesse_aussage(aussage)
        assert fehler == []

    def test_readme_nennt_nur_dev(self):
        readme = (SEED / "README.md").read_text(encoding="utf-8")
        assert "Nur für die Entwicklung" in readme
        assert "nie in Test oder Produktion" in readme

    def test_add_metadata_setzt_nutzung_null_und_ist_wiederholbar(self):
        modul = _add_metadata()

        def daten():
            return [
                {
                    "statement": "Eine Aussage zum Testen",
                    "metadata": {"usage_count": 7},
                    "commentaries": [{"title": "Ein Titel", "text": "Ein Text"}],
                    "generic_texts": [{"title": "Ein Titel", "text": "Ein Text"}],
                }
            ]

        erste, zweite = daten(), daten()
        modul.metadaten_ergaenzen(erste)
        modul.metadaten_ergaenzen(zweite)

        assert erste == zweite
        assert erste[0]["metadata"]["usage_count"] == 0
        for beitrag in _beitraege(erste[0]):
            assert beitrag["metadata"]["usage_count"] == 0
            assert beitrag["metadata"]["created_at"]


class TestVerstoesseErkannt:
    def _aussage(self, **beitrag) -> dict:
        return {
            "statement": "Windräder töten Vögel",
            "commentaries": [{"title": "Windräder sind besser als ihr Ruf", **beitrag}],
        }

    def test_verstoesse_aussage_mit_platzhalter_meldet_nichts(self):
        aussage = self._aussage(
            text="Glasscheiben sind für Vögel gefährlicher. "
            "[Hier ein eigenes Erlebnis: mein Nachbar und sein Windrad]"
        )
        assert verstoesse_aussage(aussage) == []

    def test_verstoesse_aussage_mit_eigenem_nachbarn_meldet_erlebnis(self):
        aussage = self._aussage(text="Mein Nachbar spart 200 Euro im Jahr.")
        assert any("Erlebnis" in f for f in verstoesse_aussage(aussage))

    def test_verstoesse_aussage_mit_dorfgeschichte_meldet_erlebnis(self):
        aussage = self._aussage(long_text="Bei uns im Dorf sind alle überzeugt.")
        assert any("Erlebnis" in f for f in verstoesse_aussage(aussage))

    def test_verstoesse_aussage_mit_stil_sarkastisch_meldet_stil(self):
        aussage = self._aussage(text="Ein Text", style="sarkastisch")
        assert any("Stil" in f for f in verstoesse_aussage(aussage))

    def test_verstoesse_aussage_mit_vorbelegter_nutzung_meldet_nutzung(self):
        aussage = self._aussage(text="Ein Text", metadata={"usage_count": 3})
        assert any("Nutzung" in f for f in verstoesse_aussage(aussage))

    def test_verstoesse_aussage_mit_echter_person_meldet_person(self):
        aussage = self._aussage(text="Söder wollte das auch.")
        assert any("Person" in f for f in verstoesse_aussage(aussage))

    def test_verstoesse_aussage_mit_frage_als_titel_meldet_frage(self):
        aussage = self._aussage(text="Ein Text", title="Lohnt sich das?")
        assert any("Frage" in f for f in verstoesse_aussage(aussage))
