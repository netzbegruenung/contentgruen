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
    assert {"--bg-main", "--flaeche", "--text", "--kopf"} <= set(
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


def _leuchtdichte(farbe: str) -> float:
    kanaele = [int(farbe[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [
        k / 12.92 if k <= 0.03928 else ((k + 0.055) / 1.055) ** 2.4 for k in kanaele
    ]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _kontrast(a: str, b: str) -> float:
    hell, dunkel = sorted((_leuchtdichte(a), _leuchtdichte(b)), reverse=True)
    return (hell + 0.05) / (dunkel + 0.05)


def test_warn_knoepfe_im_dunkeln_erreichen_aa():
    """Materials warn (#c62828) hat auf der dunklen Flaeche nur 2,89:1. Text-, Umriss- und
    Icon-Knoepfe mit color="warn" nehmen im Dunkeln --fehler, das 4,5:1 erreichen muss.
    """
    theme = _ohne_kommentare(THEME.read_text(encoding="utf-8"))
    dunkel = _block(theme, "html[data-theme='dark']")
    knopf = _werte(_block(dunkel, ".mat-mdc-outlined-button.mat-warn"))
    icon = _werte(_block(dunkel, ".mat-mdc-icon-button.mat-warn"))
    for name in (
        "--mat-button-text-label-text-color",
        "--mat-button-outlined-label-text-color",
        "--mat-button-outlined-outline-color",
    ):
        assert knopf.get(name) == "var(--fehler)", name
    assert icon.get("--mat-icon-button-icon-color") == "var(--fehler)"
    werte = theme_werte()
    assert _kontrast(werte["--fehler"], werte["--flaeche"]) >= 4.5


SERVICE = FRONTEND / "app/services/farbschema.service.ts"


def test_browserleiste_im_dunkeln_hat_den_dunklen_grund():
    """Die Leiste (meta theme-color) steht im Dunkeln auf --bg-main, im Skript von index.html
    und im FarbschemaService; sonst hebt sie sich nach einer neuen Palette als Streifen ab.
    """
    grund = theme_werte()["--bg-main"].lower()
    skript = re.search(
        r"schema === 'dark' \? '(#[0-9a-fA-F]{6})'", INDEX.read_text(encoding="utf-8")
    )
    service = re.search(
        r"dark: '(#[0-9a-fA-F]{6})'", SERVICE.read_text(encoding="utf-8")
    )
    assert (
        skript and service
    ), "Leistenfarbe in index.html oder farbschema.service.ts nicht gefunden"
    assert skript.group(1).lower() == grund, (skript.group(1), grund)
    assert service.group(1).lower() == grund, (service.group(1), grund)
