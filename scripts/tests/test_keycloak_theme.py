"""
Das Keycloak-Theme in keycloak-theme/gutgesagt/ läuft ohne Build auf dem Keycloak der
Netzbegrünung (docs/KEYCLOAK_REALM.md, Abschnitt Theme). Fehler fallen dort erst auf, wenn
jemand die Seite öffnet; diese Prüfungen fangen die häufigsten vorher ab.
"""

import pathlib
import re

WURZEL = pathlib.Path(__file__).resolve().parents[2]
THEME = WURZEL / "keycloak-theme/gutgesagt"
MESSAGES = sorted(THEME.glob("*/messages/messages_*.properties"))
CSS = THEME / "login/resources/css/gutgesagt.css"


def _properties(pfad: pathlib.Path) -> dict[str, str]:
    werte = {}
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        assert "=" in zeile, f"{pfad.name}: Zeile ohne '=': {zeile!r}"
        schluessel, wert = zeile.split("=", 1)
        assert schluessel.strip() not in werte, f"{pfad.name}: {schluessel} doppelt"
        werte[schluessel.strip()] = wert
    return werte


def test_es_gibt_texte_fuer_login_und_mail():
    teile = {p.parts[-3] for p in MESSAGES}
    assert teile == {"login", "email"}


def test_kein_gerader_apostroph_in_den_texten():
    # Keycloak schickt jeden Text durch Java-MessageFormat; ein ' verschluckt dort Text.
    for pfad in MESSAGES:
        for schluessel, wert in _properties(pfad).items():
            assert "'" not in wert, f"{pfad.name}: {schluessel} enthält ' (statt ’)"


def test_geschweifte_klammern_nur_als_platzhalter():
    for pfad in MESSAGES:
        for schluessel, wert in _properties(pfad).items():
            rest = re.sub(r"\{\d+\}", "", wert)
            assert "{" not in rest and "}" not in rest, f"{pfad.name}: {schluessel}"


def test_eltern_themes_sind_die_von_keycloak():
    # Nicht von fremden Themes erben: Gut gesagt hat ein eigenes Aussehen.
    login = _properties(THEME / "login/theme.properties")
    mail = _properties(THEME / "email/theme.properties")
    assert login["parent"] == "keycloak.v2"
    assert mail["parent"] == "base"
    assert "css/gutgesagt.css" in login["styles"].split()


def test_farben_stehen_nur_in_den_variablen():
    # Anpassungen am Aussehen sollen nur die --gg-Variablen oben in der Datei brauchen.
    text = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)
    for block in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
        auswahl, inhalt = block.group(1).strip(), block.group(2)
        if auswahl in (":root", ".pf-v5-theme-dark"):
            continue
        assert not re.search(
            r"#[0-9a-fA-F]{3,8}\b|rgba?\(", inhalt
        ), f"Farbwert außerhalb der Variablen in {auswahl}"


def test_css_verweist_nur_auf_vorhandene_dateien():
    for ziel in re.findall(r'url\("\.\./([^"]+)"\)', CSS.read_text(encoding="utf-8")):
        assert (THEME / "login/resources" / ziel).is_file(), ziel


def test_jeder_eigene_text_in_den_vorlagen_ist_da():
    # Ein fehlender Key fiele erst in der echten Mail oder Seite auf (Keycloak zeigt den Key).
    for teil in ("login", "email"):
        texte = _properties(THEME / teil / "messages/messages_de.properties")
        for vorlage in (THEME / teil).rglob("*.ftl"):
            for schluessel in re.findall(r'msg\("(gutgesagt\w+)"', vorlage.read_text()):
                assert schluessel in texte, f"{vorlage.name}: {schluessel} fehlt"
