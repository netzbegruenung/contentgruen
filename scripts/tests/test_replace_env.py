"""
replace-env.sh setzt Commit und Version fuer den Footer in index.html ein, nicht in die
*.js-Dateien: Deren Name entsteht beim Build vor der Ersetzung, nginx liefert sie mit
"expires 1y" aus, und ein Browser zeigte so den Commit eines alten Builds (18.11.2026).
index.html liefert nginx ohne Cache. Der Test laesst das Skript gegen ein temporaeres
Verzeichnis laufen (HTML_DIR) und liest die echte index.html aus src/.
"""

import os
import pathlib
import re
import subprocess

import pytest

WURZEL = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = WURZEL / "mvp/frontend/gutgesagt-frontend"
SKRIPT = FRONTEND / "replace-env.sh"
INDEX = FRONTEND / "src/index.html"
# Vom Production-Build (check.sh frontend-build); fehlt er, wird der Test uebersprungen.
GEBAUT = FRONTEND / "dist/gutgesagt-frontend/browser/index.html"
NGINX = [FRONTEND / "nginx.conf", FRONTEND / "nginx.docker.conf"]

JS = "const e={baseUrl:'${API_BASE_URL}',useKeycloak:'${USE_KEYCLOAK}'};"


def _ausfuehren(
    verzeichnis: pathlib.Path, **umgebung: str
) -> subprocess.CompletedProcess:
    env = {"PATH": os.environ["PATH"], "HTML_DIR": str(verzeichnis), **umgebung}
    return subprocess.run(
        ["sh", str(SKRIPT)], env=env, check=True, capture_output=True, text=True
    )


def _bauen(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "index.html").write_text(
        INDEX.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "main-ABC123.js").write_text(JS, encoding="utf-8")
    return tmp_path


def test_commit_und_version_landen_in_index_html(tmp_path):
    verzeichnis = _bauen(tmp_path)

    _ausfuehren(
        verzeichnis,
        GIT_SHA="b5113050deadbeef",
        APP_VERSION="main",
        API_BASE_URL="https://api.example.org",
        USE_KEYCLOAK="true",
    )

    index = (verzeichnis / "index.html").read_text(encoding="utf-8")
    assert '<meta name="gutgesagt-commit" content="b5113050deadbeef">' in index
    assert '<meta name="gutgesagt-version" content="main">' in index
    assert "${" not in index
    js = (verzeichnis / "main-ABC123.js").read_text(encoding="utf-8")
    assert js == "const e={baseUrl:'https://api.example.org',useKeycloak:'true'};"


def test_ohne_build_args_dev_und_leere_version(tmp_path):
    """Der Footer macht daraus "v<package.json> · dev"."""
    verzeichnis = _bauen(tmp_path)

    _ausfuehren(verzeichnis)

    index = (verzeichnis / "index.html").read_text(encoding="utf-8")
    assert '<meta name="gutgesagt-commit" content="dev">' in index
    assert '<meta name="gutgesagt-version" content="">' in index


@pytest.mark.parametrize(
    "wert",
    ["a|b", "v1&2", 'v1"x', "v1<script>", 'v1&"><script>x</script>'],
)
def test_sonderzeichen_fallen_auf_dev_und_leer_zurueck(tmp_path, wert):
    """Review #704: "|" brach sed ab, "&" setzte den Platzhalter ein, '"' und "<" landeten roh im <head>."""
    verzeichnis = _bauen(tmp_path)

    ergebnis = _ausfuehren(verzeichnis, GIT_SHA=wert, APP_VERSION=wert)

    index = (verzeichnis / "index.html").read_text(encoding="utf-8")
    assert '<meta name="gutgesagt-commit" content="dev">' in index
    assert '<meta name="gutgesagt-version" content="">' in index
    assert "GIT_SHA has characters" in ergebnis.stderr
    assert "APP_VERSION has characters" in ergebnis.stderr


def test_erlaubte_zeichen_einer_tag_version_bleiben(tmp_path):
    verzeichnis = _bauen(tmp_path)

    _ausfuehren(verzeichnis, GIT_SHA="b511305", APP_VERSION="v1.2.3-beta.1+build_7")

    index = (verzeichnis / "index.html").read_text(encoding="utf-8")
    assert 'content="v1.2.3-beta.1+build_7"' in index


def test_fehlende_index_html_bricht_mit_meldung_ab(tmp_path):
    (tmp_path / "main-ABC123.js").write_text(JS, encoding="utf-8")

    ergebnis = subprocess.run(
        ["sh", str(SKRIPT)],
        env={"PATH": os.environ["PATH"], "HTML_DIR": str(tmp_path)},
        capture_output=True,
        text=True,
    )

    assert ergebnis.returncode != 0
    assert "index.html missing" in ergebnis.stderr


@pytest.mark.skipif(
    not GEBAUT.exists(),
    reason="kein Production-Build in dist/ (check.sh frontend-build)",
)
def test_production_build_laesst_die_meta_tags_stehen():
    """Optimierung und Critical-CSS-Inlining duerfen die Platzhalter nicht umschreiben."""
    gebaut = GEBAUT.read_text(encoding="utf-8")
    assert re.search(
        r'<meta name="gutgesagt-commit" content="\$\{GIT_SHA\}"\s*/?>', gebaut
    )
    assert re.search(
        r'<meta name="gutgesagt-version" content="\$\{APP_VERSION\}"\s*/?>', gebaut
    )


def test_kein_js_traegt_mehr_commit_oder_version():
    """Kaeme der Platzhalter zurueck in environment.prod.ts, waere er wieder langzeit-gecacht."""
    umgebungen = FRONTEND / "src/environments"
    for datei in [
        *umgebungen.glob("environment.*.ts"),
        umgebungen / "environment.ts.template",
    ]:
        text = datei.read_text(encoding="utf-8")
        assert "${GIT_SHA}" not in text and "${APP_VERSION}" not in text, datei.name


def test_nginx_liefert_index_html_ohne_cache():
    for conf in NGINX:
        text = conf.read_text(encoding="utf-8")
        block = text.split("location = /index.html {", 1)[1].split("}", 1)[0]
        assert 'Cache-Control "no-cache' in block, conf.name
