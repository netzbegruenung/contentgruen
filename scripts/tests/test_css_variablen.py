"""
Jede CSS-Variable, die das Frontend mit var(--name) liest, ist auch irgendwo definiert
(#512). Eine undefinierte Variable faellt still weg: Der Karussell-Pfeil wurde ein
leerer Kreis, Radien und Farben verschwanden. Der Fallback in var(--x, wert) zaehlt
nicht als Definition: Er verdeckt den Tippfehler nur.

Die Variablen von Angular Material (--mat-*, --mdc-*) setzt Material selbst.
"""

import pathlib
import re

WURZEL = pathlib.Path(__file__).resolve().parents[2]
QUELLE = WURZEL / "mvp/frontend/gutgesagt-frontend/src"
ENDUNGEN = {".css", ".scss", ".ts", ".html"}
VON_MATERIAL = ("--mat-", "--mdc-")

GELESEN = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
# Definition in CSS (--x: …), als Bindung [style.--x] im Template oder als Name im Code
# ('--x', etwa fuer style.setProperty)
DEFINIERT = re.compile(
    r"(--[A-Za-z0-9_-]+)\s*:|\[style\.(--[A-Za-z0-9_-]+)\]|['\"](--[A-Za-z0-9_-]+)['\"]"
)


def _dateien(quelle: pathlib.Path) -> list[pathlib.Path]:
    return [
        p
        for p in quelle.rglob("*")
        if p.suffix in ENDUNGEN and not p.name.endswith(".spec.ts")
    ]


def undefinierte(quelle: pathlib.Path) -> list[str]:
    """Jede Stelle, die eine nirgends definierte Variable liest, als 'datei:zeile --name'."""
    texte = {datei: datei.read_text(encoding="utf-8") for datei in _dateien(quelle)}
    definiert = {
        name
        for text in texte.values()
        for t in DEFINIERT.finditer(text)
        for name in t.groups()
        if name
    }
    return sorted(
        f"{datei.relative_to(quelle)}:{text[: treffer.start()].count(chr(10)) + 1} {treffer.group(1)}"
        for datei, text in texte.items()
        for treffer in GELESEN.finditer(text)
        if treffer.group(1) not in definiert
        and not treffer.group(1).startswith(VON_MATERIAL)
    )


def test_jede_gelesene_css_variable_ist_definiert():
    assert undefinierte(QUELLE) == []


def test_findet_undefinierte_auch_mit_fallback(tmp_path):
    (tmp_path / "a.css").write_text(
        ".a { --da: 1px; margin: var(--da); color: var(--tippfehler, red); }"
    )
    (tmp_path / "b.html").write_text(
        '<i [style.--gebunden]="x" style="top: var(--gebunden)"></i>'
    )
    (tmp_path / "c.ts").write_text(
        "const X = '--im-code'; const y = 'var(--im-code) var(--mat-sys-primary)';"
    )

    assert undefinierte(tmp_path) == ["a.css:1 --tippfehler"]
