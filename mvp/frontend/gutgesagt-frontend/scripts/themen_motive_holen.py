"""
Holt die Motive der Themen nach public/themen/ aus Fluent Emoji Flat (Album in
"Meine Beitraege", 20.11.).

Quelle und Commit wie bei den Meilensteinen (scripts/meilensteine_holen.py): So kommt
bei jedem Lauf dasselbe heraus, und die Motive passen im Stil zu den Medaillons. Die
Lizenz steht in public/themen/FLUENT-EMOJI-LIZENZ.txt.

Welches Thema welches Motiv zeigt, steht allein in
mvp/backend/semantic-search-service/app/domain/themen.json (Feld "motiv"); dieses
Skript holt nur die Dateien dazu. Europa holt es nicht: Fluent Emoji hat keine Flaggen,
das Motiv ist ein eigenes SVG (public/themen/europa.svg, HINWEIS-EUROPA.txt). Das Motiv
fuer Beitraege ohne Thema (ohne-thema.svg) steht im Frontend
(src/app/meine-beitraege/album/album.ts, OHNE_THEMA). Dass Liste, Skript und Dateien
zusammenpassen, prueft scripts/tests/test_themen_motive.py.

Aufruf (nur noetig, wenn sich ein Motiv aendern soll), ohne weitere Pakete:
    python3 mvp/frontend/gutgesagt-frontend/scripts/themen_motive_holen.py
"""

import pathlib
import sys
import urllib.parse
import urllib.request

COMMIT = "1ffb34c752ecf5d402f04cfb4b392c77f57c54bc"
QUELLE = f"https://raw.githubusercontent.com/microsoft/fluentui-emoji/{COMMIT}/"
ZIEL = pathlib.Path(__file__).resolve().parents[1] / "public" / "themen"

HINWEIS = (
    "<!-- Fluent Emoji (https://github.com/microsoft/fluentui-emoji), "
    "Copyright (c) Microsoft Corporation, MIT License; see FLUENT-EMOJI-LIZENZ.txt -->\n"
)

# Datei unter public/themen -> Pfad im Repository von Fluent Emoji.
MOTIVE = [
    ("klima.svg", "assets/Thermometer/Flat/thermometer_flat.svg"),
    ("energie-heizen.svg", "assets/Sun/Flat/sun_flat.svg"),
    ("verkehr.svg", "assets/Bicycle/Flat/bicycle_flat.svg"),
    ("landwirtschaft-ernaehrung.svg", "assets/Sheaf of rice/Flat/sheaf_of_rice_flat.svg"),
    ("natur-umwelt.svg", "assets/Deciduous tree/Flat/deciduous_tree_flat.svg"),
    ("wirtschaft-arbeit.svg", "assets/Hammer and wrench/Flat/hammer_and_wrench_flat.svg"),
    ("haushalt-steuern.svg", "assets/Coin/Flat/coin_flat.svg"),
    ("soziales.svg", "assets/Heart hands/Default/Flat/heart_hands_flat_default.svg"),
    ("wohnen.svg", "assets/House/Flat/house_flat.svg"),
    ("gesundheit.svg", "assets/Stethoscope/Flat/stethoscope_flat.svg"),
    ("bildung.svg", "assets/Books/Flat/books_flat.svg"),
    ("digitales.svg", "assets/Laptop/Flat/laptop_flat.svg"),
    ("migration.svg", "assets/Luggage/Flat/luggage_flat.svg"),
    ("demokratie-freiheit.svg", "assets/Ballot box with ballot/Flat/ballot_box_with_ballot_flat.svg"),
    ("extremismus.svg", "assets/Shield/Flat/shield_flat.svg"),
    ("frieden-sicherheit.svg", "assets/Dove/Flat/dove_flat.svg"),
    ("stadt-land.svg", "assets/Houses/Flat/houses_flat.svg"),
    ("gleichstellung-vielfalt.svg", "assets/Rainbow/Flat/rainbow_flat.svg"),
    ("ohne-thema.svg", "assets/Card index dividers/Flat/card_index_dividers_flat.svg"),
]


def holen(pfad: str) -> str:
    url = QUELLE + urllib.parse.quote(pfad)
    with urllib.request.urlopen(url, timeout=30) as antwort:
        return antwort.read().decode("utf-8")


def main() -> None:
    ZIEL.mkdir(parents=True, exist_ok=True)
    for datei, pfad in MOTIVE:
        (ZIEL / datei).write_text(HINWEIS + holen(pfad).strip() + "\n", encoding="utf-8")
    sys.stdout.write(f"{len(MOTIVE)} Motive in {ZIEL}\n")


if __name__ == "__main__":
    main()
