"""Uebersicht der Rechtstext-Listen, erzeugt aus einer Datei je Eintrag (#500).

Aufruf: python3 scripts/rechtstexte_uebersicht.py luecken|staende

luecken: docs/rechtstexte-luecken/, je Abschnitt ein Ordner mit README.md (Ueberschrift und
Text des Abschnitts) und einer Datei je Eintrag, benannt nach seiner Nummer (D-N5.md):

    # D-N5

    - **Vorgang:** ...
    - **Eintrag / Entscheidung:** ...

Die Felder sind die Spalten der Tabelle; alle Eintraege eines Abschnitts haben dieselben.

staende: docs/nutzungsbedingungen-staende/, je Stand ein Ordner, benannt nach seinem Datum
(2026-10-30, fruehere Staende mit Monat: 2026-10). Darin stand.md mit dem Stand als
Ueberschrift und seinen Feldern, daneben eine Datei je Aenderung, benannt nach dem Ticket.

Die Uebersicht wird nicht eingecheckt: Eine Datei, die jeden Eintrag nennt, waere wieder
die Stelle, an der jeder PR anhaengt. Die Tests in scripts/tests/ pruefen die Ablage.
"""

import pathlib
import re
import sys

WURZEL = pathlib.Path(__file__).resolve().parent.parent
LUECKEN = WURZEL / "docs/rechtstexte-luecken"
STAENDE = WURZEL / "docs/nutzungsbedingungen-staende"

_FELD = re.compile(r"- \*\*(.+?):\*\*(?: (.*))?")
MONATE = [
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]


def _nach_nummer(name: str):
    """D-N4 < D-N4b < D-N10: Zahlen als Zahlen vergleichen."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def eintrag(datei: pathlib.Path) -> tuple[str, dict[str, str]]:
    """Ueberschrift und Felder einer Eintrag-Datei; anderes als Felder ist ein Fehler."""
    zeilen = [z for z in datei.read_text().splitlines() if z.strip()]
    if not zeilen or not zeilen[0].startswith("# "):
        raise ValueError(f"{datei}: erste Zeile muss '# <Nummer>' sein")
    felder = {}
    for zeile in zeilen[1:]:
        treffer = _FELD.fullmatch(zeile)
        if not treffer:
            raise ValueError(f"{datei}: keine Feldzeile '- **Feld:** Wert': {zeile}")
        felder[treffer.group(1)] = treffer.group(2) or ""
    return zeilen[0][2:].strip(), felder


def _tabelle(spalten: list[str], zeilen: list[list[str]]) -> str:
    kopf = "| " + " | ".join(spalten) + " |\n|" + "---|" * len(spalten) + "\n"
    return kopf + "".join("| " + " | ".join(z) + " |\n" for z in zeilen)


def abschnitte(wurzel: pathlib.Path = LUECKEN) -> list[pathlib.Path]:
    return sorted(d for d in wurzel.iterdir() if d.is_dir())


def _dateien_nach_nummer(ordner: pathlib.Path, ausser: str) -> list[pathlib.Path]:
    dateien = [d for d in ordner.glob("*.md") if d.name != ausser]
    return sorted(dateien, key=lambda d: _nach_nummer(d.stem))


def eintraege(abschnitt: pathlib.Path) -> list[pathlib.Path]:
    return _dateien_nach_nummer(abschnitt, ausser="README.md")


def luecken(wurzel: pathlib.Path = LUECKEN) -> str:
    teile = []
    for abschnitt in abschnitte(wurzel):
        zeilen, spalten = [], None
        for datei in eintraege(abschnitt):
            nummer, felder = eintrag(datei)
            if spalten is None:
                spalten = list(felder)
            if list(felder) != spalten:
                raise ValueError(f"{datei}: Felder {list(felder)} statt {spalten}")
            zeilen.append([nummer, *felder.values()])
        text = (abschnitt / "README.md").read_text().strip() + "\n\n"
        teile.append(text + _tabelle(["#", *(spalten or [])], zeilen))
    return "\n".join(teile)


def stand_als_ordner(stand: str) -> str:
    """'30. Oktober 2026' -> '2026-10-30', fruehere Staende 'Oktober 2026' -> '2026-10'."""
    treffer = re.fullmatch(r"(?:(\d{1,2})\. )?(\S+) (\d{4})", stand)
    if not treffer or treffer.group(2) not in MONATE:
        raise ValueError(f"kein Stand: {stand}")
    tag, monat, jahr = treffer.groups()
    ordner = f"{jahr}-{MONATE.index(monat) + 1:02d}"
    return f"{ordner}-{int(tag):02d}" if tag else ordner


def staende_ordner(wurzel: pathlib.Path = STAENDE) -> list[pathlib.Path]:
    """Neuester Stand zuerst."""
    return sorted((d for d in wurzel.iterdir() if d.is_dir()), reverse=True)


def stand(ordner: pathlib.Path) -> tuple[str, dict[str, str], list[str]]:
    """Stand, seine Felder und seine Aenderungen (eine je Datei, nach Ticket sortiert)."""
    name, felder = eintrag(ordner / "stand.md")
    aenderungen = _dateien_nach_nummer(ordner, ausser="stand.md")
    return name, felder, [" ".join(d.read_text().split()) for d in aenderungen]


def staende(wurzel: pathlib.Path = STAENDE) -> str:
    """Eine Tabelle je Feldsatz: Tagesstaende und fruehere Staende haben andere Spalten."""
    tabellen: dict[tuple[str, ...], list[list[str]]] = {}
    for ordner in staende_ordner(wurzel):
        name, felder, aenderungen = stand(ordner)
        zeile = [name, " ".join(aenderungen), *felder.values()]
        tabellen.setdefault(tuple(felder), []).append(zeile)
    return "\n".join(
        _tabelle(["Stand", "Was sich geändert hat", *spalten], zeilen)
        for spalten, zeilen in tabellen.items()
    )


if __name__ == "__main__":
    uebersichten = {"luecken": luecken, "staende": staende}
    art = sys.argv[1] if len(sys.argv) == 2 else ""
    if art not in uebersichten:
        sys.exit("Aufruf: rechtstexte_uebersicht.py luecken|staende")
    print(uebersichten[art](), end="")
