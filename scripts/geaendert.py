"""Waehlt die Schritte von check.sh nach den Dateien, die sich gegenueber der Basis geaendert haben.

Aufruf: python3 scripts/geaendert.py [--base <ref>]   (aus scripts/check.sh --geaendert)
Gruende gehen nach stderr, fuer check.sh nach stdout eine Zeile ``schritte <name> ...`` und je
Frontend-Spec eine Zeile ``spec <pfad>`` (relativ zum Frontend); ohne spec-Zeilen laufen alle.
Im Zweifel laeuft mehr, nicht weniger. Nur fuer lokale Zwischenpruefungen, die CI prueft alles.
"""

import argparse
import ast
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass, field

WURZEL = pathlib.Path(__file__).resolve().parent.parent
SCHRITTE = ["retired-words", "lint", "unit", "integration", "frontend", "bff"]
FE = "mvp/frontend/gutgesagt-frontend"
PY = "mvp/backend/semantic-search-service"
ALLES = SCHRITTE[1:]
PYTHON = ["lint", "unit"]
PYTHON_MIT_DIENSTEN = ["lint", "unit", "integration"]

# Pfad-Praefix -> Schritte; der erste passende Eintrag gilt. Was keiner trifft und keine
# Doku ist, waehlt alles. Python-Module, die die Integrationstests importieren, waehlen
# zusaetzlich integration (_python_fuer_integration).
REGELN = [
    ("scripts/", ALLES),
    (".woodpecker/", ALLES),
    (FE + "/", ["frontend"]),
    (PY + "/requirements.txt", PYTHON_MIT_DIENSTEN),
    (PY + "/app/repositories/", PYTHON_MIT_DIENSTEN),
    (PY + "/app/infrastructure/database/", PYTHON_MIT_DIENSTEN),
    (PY + "/app/tests/integration/", PYTHON_MIT_DIENSTEN),
    # Gemeinsam fuer Unit- und Integrationstests
    (PY + "/app/tests/conftest.py", PYTHON_MIT_DIENSTEN),
    (PY + "/app/pytest.ini", PYTHON_MIT_DIENSTEN),
    (PY + "/", PYTHON),
    ("mvp/backend/postgres-app/", PYTHON_MIT_DIENSTEN),
    ("mvp/backend/BFF/", ["bff"]),
    ("mvp/backend/BFF.Tests/", ["bff"]),
    ("mvp/backend/GutGesagt.sln", ["bff"]),
    # Wartungsskripte: ihre Tests findet die Suche nach lesenden Tests unten
    ("mvp/scripts/", ["unit"]),
]
# Tests, die Dateien ausserhalb ihres Dienstes lesen (Wortlaute, Profilbilder, nginx), je Schritt
LESENDE_TESTS = {
    "unit": [
        PY + "/app/tests/unit/**/*.py",
        PY + "/app/tests/fixtures/**/*.py",
        PY + "/app/tests/*.py",
        "scripts/tests/*.py",
    ],
    "integration": [PY + "/app/tests/integration/**/*.py"],
}

# import ... from './x', export ... from './x', import('./x'), import './x'
_IMPORT = re.compile(
    r"""(?:from\s+|import\s*\(\s*|import\s+)['"](\.{1,2}/[^'"]+)['"]"""
)


@dataclass
class Auswahl:
    gruende: dict[str, list[str]] = field(default_factory=dict)
    # Specs relativ zum Frontend; None: alle (oder kein Frontend-Schritt)
    specs: list[str] | None = None

    @property
    def schritte(self) -> list[str]:
        return [s for s in SCHRITTE if s in self.gruende]

    def dazu(self, schritt: str, grund: str) -> None:
        self.gruende.setdefault(schritt, []).append(grund)


def _importe(datei: pathlib.Path) -> set[pathlib.Path]:
    """Die relativ importierten .ts-Dateien von ``datei``."""
    ziele = set()
    for ziel in _IMPORT.findall(datei.read_text(errors="replace")):
        basis = (datei.parent / ziel).resolve()
        for kandidat in (
            basis.with_name(basis.name + ".ts"),
            basis / "index.ts",
            basis,
        ):
            if kandidat.is_file() and kandidat.suffix == ".ts":
                ziele.add(kandidat)
                break
    return ziele


def _specs_zu(geaenderte_ts: set[pathlib.Path], src: pathlib.Path) -> set[pathlib.Path]:
    """Specs, die eine der Dateien sind oder sie direkt oder ueber andere importieren."""
    importiert_von: dict[pathlib.Path, set[pathlib.Path]] = {}
    for datei in src.rglob("*.ts"):
        for ziel in _importe(datei.resolve()):
            importiert_von.setdefault(ziel, set()).add(datei.resolve())
    erreicht, offen = set(geaenderte_ts), list(geaenderte_ts)
    while offen:
        for nutzer in importiert_von.get(offen.pop(), ()):
            if nutzer not in erreicht:
                erreicht.add(nutzer)
                offen.append(nutzer)
    return {d for d in erreicht if d.name.endswith(".spec.ts")}


def _frontend(pfade: list[str], wurzel: pathlib.Path, auswahl: Auswahl) -> None:
    fe = (wurzel / FE).resolve()
    src = fe / "src" / "app"
    if '"paths"' in _lesen(fe / "tsconfig.json"):
        # Importe ueber Aliase verfolgt _importe nicht
        auswahl.dazu("frontend", "tsconfig.json kennt Pfad-Aliase, alle Specs")
        return
    ts, unzuordenbar = set(), None
    for pfad in pfade:
        datei = (wurzel / pfad).resolve()
        # Template und Styles gehoeren zur gleichnamigen Komponente
        komponente = datei.with_suffix(".ts")
        if datei.is_relative_to(src) and komponente.is_file():
            ts.add(komponente)
        else:
            unzuordenbar = pfad
    if unzuordenbar:
        auswahl.dazu(
            "frontend", f"{unzuordenbar}: nicht einer Komponente zuzuordnen, alle Specs"
        )
        return
    specs = _specs_zu(ts, src)
    if not specs:
        auswahl.dazu(
            "frontend", "keine Spec erreicht die geaenderten Dateien, alle Specs"
        )
        return
    auswahl.dazu("frontend", f"{len(specs)} Specs zu {len(ts)} geaenderten Dateien")
    auswahl.specs = sorted(str(s.relative_to(fe)) for s in specs)


def _lesen(datei: pathlib.Path) -> str:
    return datei.read_text(errors="replace") if datei.is_file() else ""


def _python_module(app: pathlib.Path) -> dict[str, pathlib.Path]:
    """Modulname (wie ihn pytest mit pythonpath=app importiert) -> Datei."""
    module = {}
    for datei in app.rglob("*.py"):
        teile = datei.relative_to(app).with_suffix("").parts
        if "venv" in teile or "__pycache__" in teile:
            continue
        if teile[-1] == "__init__":
            teile = teile[:-1]
        if teile:
            module[".".join(teile)] = datei
    return module


def _python_importe(name: str, datei: pathlib.Path, module: dict) -> set[str]:
    try:
        baum = ast.parse(_lesen(datei))
    except SyntaxError:
        return set()
    paket = name.split(".") if datei.name == "__init__.py" else name.split(".")[:-1]
    namen = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            namen |= {a.name for a in knoten.names}
        elif isinstance(knoten, ast.ImportFrom):
            basis = paket[: len(paket) - knoten.level + 1] if knoten.level else []
            modul = ".".join(basis + ([knoten.module] if knoten.module else []))
            namen |= {modul} | {f"{modul}.{a.name}" for a in knoten.names}
    # "import a.b.c" laedt auch a und a.b
    mit_paketen = {
        ".".join(n.split(".")[:i]) for n in namen for i in range(1, n.count(".") + 2)
    }
    return {n for n in mit_paketen if n in module}


def _python_fuer_integration(wurzel: pathlib.Path) -> set[pathlib.Path]:
    """Die Python-Dateien, die die Integrationstests direkt oder ueber andere importieren."""
    module = _python_module(wurzel / PY / "app")
    erreicht = {n for n in module if n.startswith("tests.integration")}
    offen = list(erreicht)
    while offen:
        name = offen.pop()
        for ziel in _python_importe(name, module[name], module):
            if ziel not in erreicht:
                erreicht.add(ziel)
                offen.append(ziel)
    return {module[n].resolve() for n in erreicht}


def _doku(pfad: str) -> bool:
    return pfad.endswith(".md") or pfad.startswith("docs/")


def _regel(pfad: str):
    for praefix, schritte in REGELN:
        if pfad.startswith(praefix):
            return schritte
    return [] if _doku(pfad) else ALLES


def _lesende_tests(wurzel: pathlib.Path) -> dict[str, dict[pathlib.Path, str]]:
    return {
        schritt: {
            datei: datei.read_text(errors="replace")
            for muster in muster_liste
            for datei in wurzel.glob(muster)
        }
        for schritt, muster_liste in LESENDE_TESTS.items()
    }


def _merkmale(pfad: str) -> set[str]:
    """Woran ein Test erkennbar ist, der die Datei liest: eine Zeichenkette, die mit dem
    Dateinamen oder den letzten zwei Ordnern endet ("src/app/shared/x.ts", "public/avatars").
    """
    teile = pathlib.PurePosixPath(pfad).parts
    return {teile[-1]} | ({"/".join(teile[-3:-1])} if len(teile) > 2 else set())


def waehlen(pfade: list[str], wurzel: pathlib.Path) -> Auswahl:
    """Die Schritte fuer die geaenderten ``pfade`` (relativ zu ``wurzel``) und warum."""
    auswahl = Auswahl()
    auswahl.dazu("retired-words", "immer")
    alles = []
    for pfad in pfade:
        schritte = _regel(pfad)
        if schritte == ALLES:
            alles.append(pfad)
            continue
        for schritt in schritte:
            if schritt != "frontend":
                auswahl.dazu(schritt, pfad)
    if alles:
        for schritt in ALLES:
            if schritt != "frontend":
                auswahl.dazu(schritt, f"{alles[0]}: wirkt auf alles")
    python = [p for p in pfade if p.startswith(PY + "/app/") and p.endswith(".py")]
    if python:
        erreicht = _python_fuer_integration(wurzel)
        for pfad in python:
            datei = (wurzel / pfad).resolve()
            if datei in erreicht:
                auswahl.dazu("integration", f"tests/integration erreicht {pfad}")
            elif not datei.exists():
                auswahl.dazu("integration", f"{pfad} geloescht, Importe unbekannt")
    tests = _lesende_tests(wurzel)
    for pfad in pfade:
        for schritt, inhalte in tests.items():
            for datei, text in inhalte.items():
                if pfad != str(datei.relative_to(wurzel)) and any(
                    re.search(rf"""["'/]{re.escape(m)}["']""", text)
                    for m in _merkmale(pfad)
                ):
                    auswahl.dazu(schritt, f"{datei.name} liest {pfad}")
                    break
    fe = [p for p in pfade if p.startswith(FE + "/")]
    if alles:
        auswahl.dazu("frontend", f"{alles[0]}: wirkt auf alles, alle Specs")
    elif fe:
        _frontend(fe, wurzel, auswahl)
    return auswahl


def _git(*argumente: str) -> list[str]:
    # quotePath aus: Pfade mit Umlauten kommen sonst in Anfuehrungszeichen
    aus = subprocess.run(
        ["git", "-C", str(WURZEL), "-c", "core.quotePath=false", *argumente],
        capture_output=True,
        text=True,
        check=True,
    )
    return aus.stdout.splitlines()


def geaenderte_pfade(basis: str) -> list[str]:
    """Seit dem Abzweig von ``basis`` geaendert: Commits, Arbeitsbaum und neue Dateien."""
    abzweig = _git("merge-base", basis, "HEAD")[0]
    pfade = _git("diff", "--name-only", "--no-renames", abzweig)
    pfade += _git("ls-files", "--others", "--exclude-standard")
    return sorted(set(pfade))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="origin/main")
    basis = parser.parse_args(argv).base
    try:
        pfade = geaenderte_pfade(basis)
    except subprocess.CalledProcessError as fehler:
        print(f"--geaendert: git scheitert ({fehler.stderr.strip()})", file=sys.stderr)
        return 2
    auswahl = waehlen(pfade, WURZEL)
    print(f"{len(pfade)} geaenderte Dateien gegenueber {basis}", file=sys.stderr)
    for schritt in SCHRITTE:
        gruende = auswahl.gruende.get(schritt)
        if not gruende:
            print(f"  {schritt}: ausgelassen", file=sys.stderr)
            continue
        weitere = f" (+{len(gruende) - 1} weitere)" if len(gruende) > 1 else ""
        print(f"  {schritt}: {gruende[0]}{weitere}", file=sys.stderr)
    print("schritte " + " ".join(auswahl.schritte))
    for spec in auswahl.specs or []:
        print(f"spec {spec}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
