"""
Kein Log-Aufruf setzt eine gefangene Ausnahme in den Text der Zeile (#422).

Der Formatter laesst den Fehlertext im Traceback weg (core/logging.py); steht die
Ausnahme aber als ``f"...: {e}"`` oder ``str(e)`` im Text, steht ihr Fehlertext trotzdem
in der Zeile, samt der Eingabewerte, die sie oft traegt. Erlaubt ist ``type(e)``
(meist ``type(e).__name__``), ``exc_info=e`` und die Zahl der Fehler einer
pydantic-ValidationError (``e.error_count()``).

Ein Waechter, kein Beweis: Er sieht nur Aufrufe, deren Ziel "log" im Namen traegt,
innerhalb des ``except``-Blocks, der die Ausnahme benennt. Ein Fehlertext, der erst in
eine Variable oder an eine Hilfsfunktion geht und von dort ins Log, den sieht er nicht.
"""

import ast
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[3]
LOG_METHODEN = {
    "debug",
    "info",
    "warning",
    "warn",
    "error",
    "exception",
    "critical",
    "log",
}
KEYWORDS_OHNE_LOGTEXT = {"exc_info", "stack_info", "stacklevel"}
ERLAUBTE_ATTRIBUTE = {"error_count"}


def _quelldateien() -> list[Path]:
    return [
        pfad
        for pfad in APP.rglob("*.py")
        if not {"tests", "venv", ".venv", "__pycache__"}
        & set(pfad.relative_to(APP).parts)
    ]


def _ist_log_aufruf(knoten: ast.AST) -> bool:
    if not isinstance(knoten, ast.Call) or not isinstance(knoten.func, ast.Attribute):
        return False
    if knoten.func.attr not in LOG_METHODEN:
        return False
    ziel = ast.unparse(knoten.func.value).lower()
    return "log" in ziel


def _namen_ausser_typ(knoten: ast.AST, name: str) -> list[ast.Name]:
    """Vorkommen von ``name`` in ``knoten``, ausser in type(name) und name.error_count()."""
    if (
        isinstance(knoten, ast.Call)
        and isinstance(knoten.func, ast.Name)
        and knoten.func.id == "type"
    ):
        return []
    if (
        isinstance(knoten, ast.Attribute)
        and knoten.attr in ERLAUBTE_ATTRIBUTE
        and isinstance(knoten.value, ast.Name)
    ):
        return []
    if isinstance(knoten, ast.Name):
        return [knoten] if knoten.id == name else []
    gefunden: list[ast.Name] = []
    for kind in ast.iter_child_nodes(knoten):
        gefunden.extend(_namen_ausser_typ(kind, name))
    return gefunden


def _fundstellen() -> list[str]:
    funde = []
    for pfad in _quelldateien():
        baum = ast.parse(pfad.read_text(encoding="utf-8"), filename=str(pfad))
        for handler in ast.walk(baum):
            if not isinstance(handler, ast.ExceptHandler) or not handler.name:
                continue
            for aufruf in (k for teil in handler.body for k in ast.walk(teil)):
                if not _ist_log_aufruf(aufruf):
                    continue
                argumente = list(aufruf.args) + [
                    kw.value
                    for kw in aufruf.keywords
                    if kw.arg not in KEYWORDS_OHNE_LOGTEXT
                ]
                if any(_namen_ausser_typ(arg, handler.name) for arg in argumente):
                    funde.append(f"{pfad.relative_to(APP)}:{aufruf.lineno}")
    return sorted(funde)


def test_kein_log_aufruf_schreibt_den_fehlertext_einer_ausnahme():
    assert _fundstellen() == []


def test_waechter_erkennt_die_ausnahme_im_text(tmp_path, monkeypatch):
    """Gegenprobe: der Waechter schlaegt an, wo er soll, und nur dort."""
    (tmp_path / "beispiel.py").write_text(
        "def f(logger):\n"
        "    try:\n"
        "        pass\n"
        "    except ValueError as e:\n"
        "        logger.error(f'kaputt: {e}', exc_info=True)\n"
        "        logger.error('kaputt: %s', str(e))\n"
        "        logger.error(f'kaputt: {type(e).__name__}', exc_info=e)\n"
        "        logger.warning(f'{e.error_count()} Fehler')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys.modules[__name__], "APP", tmp_path)

    assert _fundstellen() == ["beispiel.py:5", "beispiel.py:6"]
