"""
Holt die Motive der Meilensteine nach public/meilensteine/ aus Fluent Emoji Flat (#351).

Quelle ist github.com/microsoft/fluentui-emoji (MIT, Copyright Microsoft
Corporation), fest auf denselben Commit wie die Profilbilder
(scripts/profilbilder_holen.py): So kommt bei jedem Lauf dasselbe heraus. Die Lizenz
steht in public/meilensteine/FLUENT-EMOJI-LIZENZ.txt.

Die SVGs bleiben, wie sie sind, bis auf einen Hinweis auf Quelle und Lizenz am Anfang.
Einzige Ausnahme ist die Sprechblase fuer "Erste Gegenrede": Sie bekommt ein
Ausrufezeichen, damit sie nach Gegenrede aussieht und nicht nach Plaudern. Das
Medaillon drumherum (erreicht tannengruen, offen grau gestrichelt) zeichnet die
Komponente selbst (src/app/meine-beitraege/meilensteine.component.html).

Die Dateinamen muessen zu den Bildern in
mvp/backend/semantic-search-service/app/domain/meilensteine.py passen; das prueft
scripts/tests/test_meilenstein_bilder.py.

Aufruf (nur noetig, wenn sich ein Motiv aendern soll), ohne weitere Pakete:
    python3 mvp/frontend/gutgesagt-frontend/scripts/meilensteine_holen.py
"""

import pathlib
import sys
import urllib.parse
import urllib.request

COMMIT = "1ffb34c752ecf5d402f04cfb4b392c77f57c54bc"
QUELLE = f"https://raw.githubusercontent.com/microsoft/fluentui-emoji/{COMMIT}/"
ZIEL = pathlib.Path(__file__).resolve().parents[1] / "public" / "meilensteine"

HINWEIS = (
    "<!-- Fluent Emoji (https://github.com/microsoft/fluentui-emoji), "
    "Copyright (c) Microsoft Corporation, MIT License; see FLUENT-EMOJI-LIZENZ.txt -->\n"
)

# Ein Ausrufezeichen in der Mitte der Sprechblase (viewBox 32 x 32), im Grau der
# Fluent-Umrisse; eigenes Werk.
AUSRUFEZEICHEN = (
    '<rect x="14.5" y="8" width="3" height="10" rx="1.5" fill="#212121"/>'
    '<circle cx="16" cy="21.5" r="1.75" fill="#212121"/>'
)

# Datei unter public/meilensteine -> Pfad im Repository von Fluent Emoji.
# Neutrale Alltagsmotive; keine Figuren, Waffen, Partei- oder Kirchensymbole.
MOTIVE = [
    ("korb.svg", "assets/Basket/Flat/basket_flat.svg"),
    ("sanduhr.svg", "assets/Hourglass not done/Flat/hourglass_not_done_flat.svg"),
    ("sprechblase.svg", "assets/Speech balloon/Flat/speech_balloon_flat.svg"),
    ("butter.svg", "assets/Butter/Flat/butter_flat.svg"),
    ("vogel.svg", "assets/Bird/Flat/bird_flat.svg"),
    ("lautsprecher.svg", "assets/Loudspeaker/Flat/loudspeaker_flat.svg"),
    ("laufschuh.svg", "assets/Running shoe/Flat/running_shoe_flat.svg"),
    ("hundert.svg", "assets/Hundred points/Flat/hundred_points_flat.svg"),
    ("handschlag.svg", "assets/Handshake/Flat/handshake_flat.svg"),
    ("fueller.svg", "assets/Fountain pen/Flat/fountain_pen_flat.svg"),
    ("nase.svg", "assets/Nose/Default/Flat/nose_flat_default.svg"),
]

# Motive, die ueber dem Original noch etwas bekommen.
ZUSAETZE = {"sprechblase.svg": AUSRUFEZEICHEN}


def holen(pfad: str) -> str:
    url = QUELLE + urllib.parse.quote(pfad)
    with urllib.request.urlopen(url, timeout=30) as antwort:
        return antwort.read().decode("utf-8")


def bearbeiten(datei: str, svg: str) -> str:
    svg = svg.strip() + "\n"
    zusatz = ZUSAETZE.get(datei)
    if zusatz:
        ende = svg.rindex("</svg>")
        svg = svg[:ende] + zusatz + "\n" + svg[ende:]
    return HINWEIS + svg


def main() -> None:
    ZIEL.mkdir(parents=True, exist_ok=True)
    for datei, pfad in MOTIVE:
        (ZIEL / datei).write_text(bearbeiten(datei, holen(pfad)), encoding="utf-8")
    sys.stdout.write(f"{len(MOTIVE)} Motive in {ZIEL}\n")


if __name__ == "__main__":
    main()
