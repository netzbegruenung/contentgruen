"""
Die Kennungen des CC0-Hinweises (#431) stehen an drei Stellen: im Dienst (der nur
bekannte annimmt), im Frontend (das sie mitschickt) und im Verzeichnis der
Wortlaute. Laufen sie auseinander, scheitert das Speichern oder eine Kennung ist
nicht mehr zuzuordnen.
"""

import pathlib
import re

WURZEL = pathlib.Path(__file__).resolve().parents[2]
DIENST = WURZEL / "mvp/backend/semantic-search-service/app/domain/cc0_hinweis.py"
FRONTEND = WURZEL / "mvp/frontend/gutgesagt-frontend/src/app/shared/consent-hinweis.ts"
VERZEICHNIS = WURZEL / "docs/CC0_HINWEIS_WORTLAUTE.md"

KENNUNG = r"\d{4}-\d{2}-\d{2}-[a-z]+"


def _dienst() -> set[str]:
    block = re.search(
        r"CC0_WORTLAUTE = frozenset\(\s*\{(.*?)\}", DIENST.read_text(), re.S
    )
    return set(re.findall(rf'"({KENNUNG})"', block.group(1)))


def _frontend() -> set[str]:
    return set(re.findall(rf"kennung: '({KENNUNG})'", FRONTEND.read_text()))


def _verzeichnis() -> set[str]:
    return set(re.findall(rf"^\| `({KENNUNG})` \|", VERZEICHNIS.read_text(), re.M))


def test_der_dienst_kennt_jede_kennung_des_verzeichnisses():
    assert _dienst() == _verzeichnis()


def test_das_frontend_schickt_nur_bekannte_kennungen():
    frontend = _frontend()
    assert frontend, "keine Kennung im Frontend gefunden"
    assert frontend <= _dienst()
