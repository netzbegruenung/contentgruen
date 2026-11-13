"""
Die dunklen Grundflaechen stehen zweimal: als Inline-Style in index.html, damit der Dunkelmodus
nicht hell aufblitzt, solange das Stylesheet noch laedt (#663), und im Block
html[data-theme='dark'] in theme/custom-theme.scss. Aendert jemand die Dunkel-Palette nur im
Theme, blitzt die alte Farbe beim Laden auf. Dieser Test haelt beide gleich.
"""

import pathlib
import re

WURZEL = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = WURZEL / "mvp/frontend/gutgesagt-frontend/src"
INDEX = FRONTEND / "index.html"
THEME = FRONTEND / "theme/custom-theme.scss"

VARIABLE = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;]+);")


def _block(text: str, anfang: str) -> str:
    """Der Inhalt der geschweiften Klammern nach `anfang`, mit verschachtelten Bloecken."""
    start = text.index(anfang)
    offen = text.index("{", start)
    tiefe = 0
    for stelle in range(offen, len(text)):
        if text[stelle] == "{":
            tiefe += 1
        elif text[stelle] == "}":
            tiefe -= 1
            if tiefe == 0:
                return text[offen + 1 : stelle]
    raise ValueError(f"Block {anfang!r} nicht geschlossen")


def _ohne_kommentare(text: str) -> str:
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL))


def _werte(block: str) -> dict[str, str]:
    return {name: " ".join(wert.split()) for name, wert in VARIABLE.findall(block)}


def inline_werte() -> dict[str, str]:
    stil = re.search(
        r"<style>(.*?)</style>", INDEX.read_text(encoding="utf-8"), re.DOTALL
    )
    assert stil, "index.html ohne <style>-Block"
    return _werte(_block(stil.group(1), "html[data-theme='dark']"))


def theme_werte() -> dict[str, str]:
    theme = _ohne_kommentare(THEME.read_text(encoding="utf-8"))
    return _werte(_block(theme, "html[data-theme='dark']"))


def test_inline_style_hat_die_grundflaechen():
    assert {"--bg-main", "--bg-card", "--text-primary", "--such-band"} <= set(
        inline_werte()
    )


def test_inline_style_und_theme_nennen_dieselben_dunklen_werte():
    theme = theme_werte()
    abweichend = {
        name: (wert, theme.get(name))
        for name, wert in inline_werte().items()
        if theme.get(name) != wert
    }
    assert (
        not abweichend
    ), f"index.html weicht vom Theme ab (inline, Theme): {abweichend}"
