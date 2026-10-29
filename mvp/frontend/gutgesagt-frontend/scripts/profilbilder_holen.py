"""
Erzeugt die Profilbilder unter public/avatars/ aus Fluent Emoji 3D (#437).

Quelle ist github.com/microsoft/fluentui-emoji (MIT, Copyright Microsoft
Corporation), fest auf einen Commit: So kommt bei jedem Lauf dasselbe heraus,
und eine neue Fassung von Fluent Emoji aendert die Bilder nicht unbemerkt. Die
Lizenz steht in public/avatars/FLUENT-EMOJI-LIZENZ.txt.

Jedes Bild ist ein Kreis in Sand (#F5F1E9) mit dem Emoji in der Mitte, etwa
72 % so breit wie der Kreis, als PNG mit 128 px Kantenlaenge; was ueber den Kreis
hinausragt, schneidet der Kreis ab. Motive, die schon in der Vorlage gerade
abgeschnitten sind (etwa alle Fassungen von "deaf"), sind bewusst nicht dabei.
Die Reihenfolge und die Dateinamen muessen zu BILDER in src/app/services/profilbild.service.ts
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

from PIL import Image, ImageDraw

COMMIT = "1ffb34c752ecf5d402f04cfb4b392c77f57c54bc"
QUELLE = f"https://raw.githubusercontent.com/microsoft/fluentui-emoji/{COMMIT}/"
ZIEL = pathlib.Path(__file__).resolve().parents[1] / "public" / "avatars"

KANTE = 128
ANTEIL = 0.72
SAND = (0xF5, 0xF1, 0xE9, 0xFF)

# Datei unter public/avatars -> Pfad im Repository von Fluent Emoji. Hauttoene leicht
# an der westeuropaeischen Bevoelkerung orientiert und trotzdem vielfaeltig: 10 hell
# oder mittelhell (darunter drei rothaarig, eine blond, zwei mit weissem Haar), 5
# mittel, 5 mitteldunkel oder dunkel. In der Liste gemischt, damit das Raster nicht
# nach Hautton sortiert wirkt.
MENSCHEN = [
    ("mensch-01.png", "assets/Woman red hair/Light/3D/woman_red_hair_3d_light.png"),
    ("mensch-02.png", "assets/Man/Medium/3D/man_3d_medium.png"),
    ("mensch-03.png", "assets/Man curly hair/Dark/3D/man_curly_hair_3d_dark.png"),
    (
        "mensch-04.png",
        "assets/Person blonde hair/Light/3D/person_blonde_hair_3d_light.png",
    ),
    (
        "mensch-05.png",
        "assets/Woman with headscarf/Medium/3D/woman_with_headscarf_3d_medium.png",
    ),
    ("mensch-06.png", "assets/Old man/Light/3D/old_man_3d_light.png"),
    ("mensch-07.png", "assets/Woman curly hair/Dark/3D/woman_curly_hair_3d_dark.png"),
    ("mensch-08.png", "assets/Man red hair/Light/3D/man_red_hair_3d_light.png"),
    (
        "mensch-09.png",
        "assets/Person in manual wheelchair/Medium/3D/person_in_manual_wheelchair_3d_medium.png",
    ),
    (
        "mensch-10.png",
        "assets/Person white hair/Medium-Light/3D/person_white_hair_3d_medium-light.png",
    ),
    ("mensch-11.png", "assets/Man bald/Medium-Dark/3D/man_bald_3d_medium-dark.png"),
    (
        "mensch-12.png",
        "assets/Person red hair/Medium-Light/3D/person_red_hair_3d_medium-light.png",
    ),
    ("mensch-13.png", "assets/Person beard/Medium/3D/person_beard_3d_medium.png"),
    ("mensch-14.png", "assets/Woman/Medium-Light/3D/woman_3d_medium-light.png"),
    (
        "mensch-15.png",
        "assets/Older person/Medium-Dark/3D/older_person_3d_medium-dark.png",
    ),
    ("mensch-16.png", "assets/Man white hair/Light/3D/man_white_hair_3d_light.png"),
    ("mensch-17.png", "assets/Old woman/Medium/3D/old_woman_3d_medium.png"),
    (
        "mensch-18.png",
        "assets/Person curly hair/Medium-Light/3D/person_curly_hair_3d_medium-light.png",
    ),
    ("mensch-19.png", "assets/Person/Dark/3D/person_3d_dark.png"),
    (
        "mensch-20.png",
        "assets/Person with white cane/Light/3D/person_with_white_cane_3d_light.png",
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


def holen(pfad: str) -> Image.Image:
    url = QUELLE + urllib.parse.quote(pfad)
    with urllib.request.urlopen(url, timeout=30) as antwort:
        return Image.open(io.BytesIO(antwort.read())).convert("RGBA")


def _eingepasst(groesse: tuple[int, int], seite: int) -> tuple[int, int]:
    """Groesse so skaliert, dass die laengere Seite genau `seite` ist."""
    breite, hoehe = groesse
    faktor = seite / max(breite, hoehe)
    return max(1, round(breite * faktor)), max(1, round(hoehe * faktor))


def profilbild(emoji: Image.Image) -> Image.Image:
    # Viermal so gross zeichnen und dann verkleinern: so wird der Kreisrand glatt.
    gross = KANTE * 4
    kreis = Image.new("L", (gross, gross), 0)
    ImageDraw.Draw(kreis).ellipse((0, 0, gross - 1, gross - 1), fill=255)
    bild = Image.new("RGBA", (gross, gross), SAND)
    # Die Quellbilder haben einen transparenten Rand; 72 % gelten fuer das Motiv selbst.
    emoji = emoji.crop(emoji.getchannel("A").getbbox())
    seite = round(gross * ANTEIL)
    emoji = emoji.resize(_eingepasst(emoji.size, seite), Image.Resampling.LANCZOS)
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
        profilbild(holen(pfad)).save(ziel, optimize=True)
        summe += ziel.stat().st_size
    sys.stdout.write(
        f"{len(BILDER)} Profilbilder in {ZIEL}, zusammen {summe // 1024} KiB\n"
    )


if __name__ == "__main__":
    main()
