"""
Erzeugt die Profilbilder unter public/avatars/ aus Fluent Emoji 3D (#437).

Quelle ist github.com/microsoft/fluentui-emoji (MIT, Copyright Microsoft
Corporation), fest auf einen Commit: So kommt bei jedem Lauf dasselbe heraus,
und eine neue Fassung von Fluent Emoji aendert die Bilder nicht unbemerkt. Die
Lizenz steht in public/avatars/FLUENT-EMOJI-LIZENZ.txt.

Jedes Bild ist ein Kreis in Sand (#F5F1E9) mit dem Emoji in der Mitte, etwa
72 % so breit wie der Kreis, als PNG mit 128 px Kantenlaenge; was ueber den Kreis
hinausragt, schneidet der Kreis ab. Motive, die schon in der Vorlage gerade
abgeschnitten sind (ANGESCHNITTEN), laufen an diesen Kanten weich in den Sand aus,
statt mit einer harten Linie zu enden. Die Reihenfolge
und die Dateinamen muessen zu BILDER in src/app/services/profilbild.service.ts
passen; das prueft scripts/tests/test_profilbilder.py.

Aufruf (nur noetig, wenn sich ein Bild aendern soll), mit der venv des
Suchdienstes, die Pillow mitbringt:
    mvp/backend/semantic-search-service/venv/bin/python \\
        mvp/frontend/gutgesagt-frontend/scripts/profilbilder_holen.py
"""

import io
import pathlib
import sys
import urllib.parse
import urllib.request

from PIL import Image, ImageChops, ImageDraw

COMMIT = "1ffb34c752ecf5d402f04cfb4b392c77f57c54bc"
QUELLE = f"https://raw.githubusercontent.com/microsoft/fluentui-emoji/{COMMIT}/"
ZIEL = pathlib.Path(__file__).resolve().parents[1] / "public" / "avatars"

KANTE = 128
ANTEIL = 0.72
SAND = (0xF5, 0xF1, 0xE9, 0xFF)

# Datei unter public/avatars -> Pfad im Repository von Fluent Emoji. Die Hauttoene
# sind gleich verteilt: je vier Mal Light, Medium-Light, Medium, Medium-Dark, Dark.
MENSCHEN = [
    ("mensch-01.png", "assets/Woman/Medium/3D/woman_3d_medium.png"),
    ("mensch-02.png", "assets/Man/Dark/3D/man_3d_dark.png"),
    ("mensch-03.png", "assets/Person/Light/3D/person_3d_light.png"),
    (
        "mensch-04.png",
        "assets/Old woman/Medium-Dark/3D/old_woman_3d_medium-dark.png",
    ),
    ("mensch-05.png", "assets/Old man/Medium-Light/3D/old_man_3d_medium-light.png"),
    ("mensch-06.png", "assets/Older person/Dark/3D/older_person_3d_dark.png"),
    (
        "mensch-07.png",
        "assets/Woman with headscarf/Medium-Light/3D/"
        "woman_with_headscarf_3d_medium-light.png",
    ),
    (
        "mensch-08.png",
        "assets/Person beard/Medium-Dark/3D/person_beard_3d_medium-dark.png",
    ),
    ("mensch-09.png", "assets/Woman curly hair/Dark/3D/woman_curly_hair_3d_dark.png"),
    ("mensch-10.png", "assets/Man white hair/Light/3D/man_white_hair_3d_light.png"),
    (
        "mensch-11.png",
        "assets/Person in manual wheelchair/Medium/3D/"
        "person_in_manual_wheelchair_3d_medium.png",
    ),
    ("mensch-12.png", "assets/Woman red hair/Light/3D/woman_red_hair_3d_light.png"),
    ("mensch-13.png", "assets/Man bald/Medium-Dark/3D/man_bald_3d_medium-dark.png"),
    (
        "mensch-14.png",
        "assets/Person blonde hair/Medium-Light/3D/"
        "person_blonde_hair_3d_medium-light.png",
    ),
    ("mensch-15.png", "assets/Man curly hair/Medium/3D/man_curly_hair_3d_medium.png"),
    ("mensch-16.png", "assets/Person deaf/Dark/3D/person_deaf_3d_dark.png"),
    (
        "mensch-17.png",
        "assets/Person with white cane/Medium-Light/3D/"
        "person_with_white_cane_3d_medium-light.png",
    ),
    (
        "mensch-18.png",
        "assets/Person white hair/Medium-Dark/3D/person_white_hair_3d_medium-dark.png",
    ),
    ("mensch-19.png", "assets/Man red hair/Medium/3D/man_red_hair_3d_medium.png"),
    (
        "mensch-20.png",
        "assets/Person curly hair/Light/3D/person_curly_hair_3d_light.png",
    ),
]

# Natur und Tiere, keine politischen Symbole.
MOTIVE = [
    ("igel.png", "assets/Hedgehog/3D/hedgehog_3d.png"),
    ("sonnenblume.png", "assets/Sunflower/3D/sunflower_3d.png"),
    ("laubbaum.png", "assets/Deciduous tree/3D/deciduous_tree_3d.png"),
    ("daumen-hoch.png", "assets/Thumbs up/Default/3D/thumbs_up_3d_default.png"),
    ("setzling.png", "assets/Seedling/3D/seedling_3d.png"),
    ("schmetterling.png", "assets/Butterfly/3D/butterfly_3d.png"),
    ("biene.png", "assets/Honeybee/3D/honeybee_3d.png"),
    ("marienkaefer.png", "assets/Lady beetle/3D/lady_beetle_3d.png"),
    ("eule.png", "assets/Owl/3D/owl_3d.png"),
    ("fuchs.png", "assets/Fox/3D/fox_3d.png"),
    ("katze.png", "assets/Cat face/3D/cat_face_3d.png"),
    ("hund.png", "assets/Dog face/3D/dog_face_3d.png"),
    ("schildkroete.png", "assets/Turtle/3D/turtle_3d.png"),
    ("pilz.png", "assets/Mushroom/3D/mushroom_3d.png"),
    ("kleeblatt.png", "assets/Four leaf clover/3D/four_leaf_clover_3d.png"),
    ("sonne.png", "assets/Sun/3D/sun_3d.png"),
    (
        "erde.png",
        "assets/Globe showing europe-africa/3D/globe_showing_europe-africa_3d.png",
    ),
    ("fahrrad.png", "assets/Bicycle/3D/bicycle_3d.png"),
    ("tulpe.png", "assets/Tulip/3D/tulip_3d.png"),
    ("tannenbaum.png", "assets/Evergreen tree/3D/evergreen_tree_3d.png"),
]

BILDER = MENSCHEN + MOTIVE

# Die Vorlage zeigt eine Nahaufnahme, rechts, unten und oben gerade abgeschnitten; das
# gilt fuer alle Fassungen von "deaf" in Fluent Emoji, und ein Ausschnitt durch den
# Kreis wuerde das Gesicht treffen. Anteil des Motivs, ueber den die Kante auslaeuft:
ANGESCHNITTEN = {"mensch-16.png"}
AUSLAUF = 0.18
AUSLAUF_OBEN = 0.10


def holen(pfad: str) -> Image.Image:
    url = QUELLE + urllib.parse.quote(pfad)
    with urllib.request.urlopen(url, timeout=30) as antwort:
        return Image.open(io.BytesIO(antwort.read())).convert("RGBA")


def _eingepasst(groesse: tuple[int, int], seite: int) -> tuple[int, int]:
    """Groesse so skaliert, dass die laengere Seite genau `seite` ist."""
    breite, hoehe = groesse
    faktor = seite / max(breite, hoehe)
    return max(1, round(breite * faktor)), max(1, round(hoehe * faktor))


def _rampe(laenge: int, auslauf: int, ab_ende: bool) -> list[int]:
    """Deckkraft 255 im Inneren, auf den letzten (oder ersten) `auslauf` Pixeln linear auf null."""
    werte = [255] * laenge
    for i in range(auslauf):
        werte[laenge - 1 - i if ab_ende else i] = round(255 * i / auslauf)
    return werte


def _auslaufen(emoji: Image.Image) -> Image.Image:
    """Rechts, unten und oben laeuft das Motiv in den Grund aus; links bleibt es."""
    breite, hoehe = emoji.size
    rechts = _rampe(breite, max(1, round(breite * AUSLAUF)), ab_ende=True)
    unten = _rampe(hoehe, max(1, round(hoehe * AUSLAUF)), ab_ende=True)
    oben = _rampe(hoehe, max(1, round(hoehe * AUSLAUF_OBEN)), ab_ende=False)
    verlauf = Image.new("L", (breite, hoehe))
    verlauf.putdata(
        [
            rechts[x] * unten[y] * oben[y] // (255 * 255)
            for y in range(hoehe)
            for x in range(breite)
        ]
    )
    emoji.putalpha(ImageChops.multiply(emoji.getchannel("A"), verlauf))
    return emoji


def profilbild(emoji: Image.Image, angeschnitten: bool = False) -> Image.Image:
    # Viermal so gross zeichnen und dann verkleinern: so wird der Kreisrand glatt.
    gross = KANTE * 4
    kreis = Image.new("L", (gross, gross), 0)
    ImageDraw.Draw(kreis).ellipse((0, 0, gross - 1, gross - 1), fill=255)
    bild = Image.new("RGBA", (gross, gross), SAND)
    # Die Quellbilder haben einen transparenten Rand; 72 % gelten fuer das Motiv selbst.
    emoji = emoji.crop(emoji.getchannel("A").getbbox())
    seite = round(gross * ANTEIL)
    emoji = emoji.resize(_eingepasst(emoji.size, seite), Image.Resampling.LANCZOS)
    if angeschnitten:
        emoji = _auslaufen(emoji)
    links = (gross - emoji.width) // 2
    oben = (gross - emoji.height) // 2
    bild.alpha_composite(emoji, (links, oben))
    bild.putalpha(kreis)
    return bild.resize((KANTE, KANTE), Image.Resampling.LANCZOS)


def main() -> None:
    ZIEL.mkdir(parents=True, exist_ok=True)
    summe = 0
    for datei, pfad in BILDER:
        ziel = ZIEL / datei
        profilbild(holen(pfad), datei in ANGESCHNITTEN).save(ziel, optimize=True)
        summe += ziel.stat().st_size
    sys.stdout.write(
        f"{len(BILDER)} Profilbilder in {ZIEL}, zusammen {summe // 1024} KiB\n"
    )


if __name__ == "__main__":
    main()
