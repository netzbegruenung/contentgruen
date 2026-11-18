"""
replace-env.sh setzt Commit und Version fuer den Footer in index.html ein, nicht in die
*.js-Dateien: Deren Name entsteht beim Build vor der Ersetzung, nginx liefert sie mit
"expires 1y" aus, und ein Browser zeigte so den Commit eines alten Builds (18.11.2026).
index.html liefert nginx ohne Cache. Der Test laesst das Skript gegen ein temporaeres
Verzeichnis laufen (HTML_DIR) und liest die echte index.html aus src/.
"""

import os
import pathlib
import subprocess

WURZEL = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = WURZEL / "mvp/frontend/gutgesagt-frontend"
SKRIPT = FRONTEND / "replace-env.sh"
INDEX = FRONTEND / "src/index.html"
NGINX = [FRONTEND / "nginx.conf", FRONTEND / "nginx.docker.conf"]

JS = "const e={baseUrl:'${API_BASE_URL}',useKeycloak:'${USE_KEYCLOAK}'};"


def _ausfuehren(verzeichnis: pathlib.Path, **umgebung: str) -> None:
    env = {"PATH": os.environ["PATH"], "HTML_DIR": str(verzeichnis), **umgebung}
    subprocess.run(["sh", str(SKRIPT)], env=env, check=True)


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
