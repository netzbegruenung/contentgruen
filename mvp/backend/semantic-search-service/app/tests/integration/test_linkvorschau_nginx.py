"""
Linkvorschau ueber nginx und SSI (#360), mit nginx aus dem Image des Frontend-Dockerfiles.

Fuer /beitrag/<id> und /result setzt nginx in index.html ein, was der Suchdienst unter
/api/v1/linkvorschau/... liefert; ohne Antwort gilt der Block
"linkvorschau_allgemein". Hier steht fuer den Suchdienst ein zweiter nginx im selben
Docker-Netz unter dem Namen gutgesagt-semantic-search; er antwortet fest wie der echte
Endpunkt (200 mit Stueck, 204) oder mit einem Fehler und gibt fuer die Ergebnisseite
zurueck, was bei ihm ankommt: Adresse, X-Suchtext und Cookie.

Die Inhalte des Stuecks (Titel, Kuerzen, Maskieren) prueft
tests/unit/api/test_linkvorschau_api.py. Ohne Docker uebersprungen, im Pflichtmodus
(``stack.py``) ein Fehler, ausser in der CI.
"""

import pathlib
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from typing import Iterator

import pytest

from tests.integration import nginx, postgres, stack

pytestmark = pytest.mark.integration

INDEX = nginx.FRONTEND / "src" / "index.html"
SICHTBAR = "11111111-1111-4111-8111-111111111111"
NICHT_DA = "22222222-2222-4222-8222-222222222222"
KAPUTT = "33333333-3333-4333-8333-333333333333"
UNBEKANNT = "44444444-4444-4444-8444-444444444444"
# Status mit Rumpf, die der Suchdienst nicht schickt, die aber nie im <head> landen duerfen
MIT_RUMPF = {
    "55555555-5555-4555-8555-555555555401": "401",
    "55555555-5555-4555-8555-555555555406": "406",
    "55555555-5555-4555-8555-555555555413": "413",
    "55555555-5555-4555-8555-555555555501": "501",
    "55555555-5555-4555-8555-555555555302": "302",
}
ALLGEMEIN = '<meta property="og:title" content="Gut gesagt – Nie wieder sprachlos">'
SPEZIFISCH = '<meta property="og:title" content="Erfundener Beitrag">'
SUCHTEXT = "Waermepumpe-im-Altbau-360"
KONFIGURATIONEN = ["nginx.conf", "nginx.docker.conf"]


def _mit_rumpf(beitrag: str, status: str) -> str:
    antwort = (
        "302 http://example.invalid/RUMPF-302"
        if status == "302"
        else f"{status} 'RUMPF-{status}'"
    )
    return (
        f"    location = /api/v1/linkvorschau/beitrag/{beitrag} {{\n"
        f"        return {antwort};\n"
        "    }\n"
    )


MIT_RUMPF_LOCATIONS = "".join(_mit_rumpf(b, s) for b, s in MIT_RUMPF.items())

SUCHDIENST = f"""
server {{
    listen 8000;
    default_type text/html;
    location = /api/v1/linkvorschau/beitrag/{SICHTBAR} {{
        return 200 '{SPEZIFISCH}\\n';
    }}
    location = /api/v1/linkvorschau/beitrag/{NICHT_DA} {{
        return 204;
    }}
    location = /api/v1/linkvorschau/beitrag/{KAPUTT} {{
        return 500 'kaputt';
    }}
    location = /api/v1/linkvorschau/ergebnis {{
        return 200 '<meta name="echo" content="$request_uri|$http_x_suchtext|$http_cookie">\\n';
    }}
{MIT_RUMPF_LOCATIONS}
    location / {{
        return 404 'nicht gefunden';
    }}
}}
"""


@pytest.fixture(scope="module")
def docker_noetig():
    if postgres.docker_verfuegbar():
        return
    grund = "Docker fehlt: nginx laesst sich nicht starten"
    if stack.pflicht_ausser_in_ci():
        pytest.fail(grund)
    pytest.skip(grund)


def _warten(basis: str, name: str) -> None:
    frist = time.monotonic() + 30
    while True:
        try:
            urllib.request.urlopen(f"{basis}/hilfe", timeout=1).close()
            return
        except urllib.error.HTTPError:
            return
        except OSError:
            if time.monotonic() > frist:
                raise RuntimeError(
                    "nginx startet nicht:\n" + "\n".join(nginx.ausgabe(name))
                ) from None
            time.sleep(0.3)


@contextmanager
def _aufbauen(konfiguration: str, mit_suchdienst: bool) -> Iterator[tuple[str, str]]:
    """Frontend-nginx in einem eigenen Netz, wahlweise mit Suchdienst; liefert
    Basisadresse und Containername."""
    netz = f"gutgesagt-itest-netz-{uuid.uuid4().hex[:8]}"
    nginx.docker("network", "create", "--label", "gutgesagt-itest", netz)
    namen = []
    try:
        with tempfile.TemporaryDirectory() as ordner:
            if mit_suchdienst:
                conf = pathlib.Path(ordner) / "suchdienst.conf"
                conf.write_text(SUCHDIENST, encoding="utf-8")
                conf.chmod(0o644)
                pathlib.Path(ordner).chmod(0o755)
                suchdienst = f"gutgesagt-itest-suchdienst-{uuid.uuid4().hex[:8]}"
                namen.append(suchdienst)
                nginx.docker(
                    "run",
                    "--detach",
                    "--name",
                    suchdienst,
                    "--label",
                    "gutgesagt-itest",
                    "--network",
                    netz,
                    "--network-alias",
                    "gutgesagt-semantic-search",
                    "--volume",
                    f"{conf}:/etc/nginx/conf.d/default.conf:ro",
                    nginx.image(),
                    timeout=300,
                )
            name = nginx.starten(
                konfiguration,
                "--network",
                netz,
                "--volume",
                f"{INDEX}:/usr/share/nginx/html/index.html:ro",
            )
            namen.append(name)
            adresse = nginx.docker("port", name, "80/tcp").splitlines()[0]
            basis = f"http://{adresse}"
            _warten(basis, name)
            yield basis, name
    finally:
        for name in namen:
            nginx.entfernen(name)
        nginx.docker("network", "rm", netz)


@pytest.fixture(scope="module", params=KONFIGURATIONEN)
def frontend(request, docker_noetig):
    with _aufbauen(request.param, mit_suchdienst=True) as (basis, name):
        yield basis, name


def _holen(adresse: str, cookie: str = "") -> tuple[int, dict, str]:
    anfrage = urllib.request.Request(adresse)
    if cookie:
        anfrage.add_header("Cookie", cookie)
    with urllib.request.urlopen(anfrage, timeout=10) as antwort:
        return antwort.status, dict(antwort.headers), antwort.read().decode("utf-8")


def test_sichtbarer_beitrag_eigene_angaben(frontend):
    basis, _ = frontend
    status, kopf, text = _holen(f"{basis}/beitrag/{SICHTBAR}")
    assert status == 200
    assert SPEZIFISCH in text
    assert ALLGEMEIN not in text
    assert "<!--#" not in text
    assert "<app-root>" in text
    assert kopf["Cache-Control"] == "no-cache, no-store, must-revalidate"


@pytest.mark.parametrize("beitrag", [NICHT_DA, KAPUTT, UNBEKANNT, *MIT_RUMPF])
def test_ohne_vorschau_allgemeine_angaben(frontend, beitrag):
    """204 (gesperrt, geloescht, unbekannt), Fehler, unbekannter Pfad oder ein anderer
    Status mit Rumpf (401, 406, 413, 501, Umleitung) beim Suchdienst: die allgemeinen
    Angaben, die Seite laedt normal."""
    basis, _ = frontend
    status, _, text = _holen(f"{basis}/beitrag/{beitrag}")
    assert status == 200
    assert ALLGEMEIN in text
    assert "kaputt" not in text and "nicht gefunden" not in text
    assert "RUMPF" not in text
    assert "<!--#" not in text
    assert "<app-root>" in text


def test_ergebnisseite_suchtext_nur_im_header(frontend):
    basis, name = frontend
    status, kopf, text = _holen(
        f"{basis}/result?searchQuery={SUCHTEXT}&einwurf=x", cookie="sitzung=geheim"
    )
    assert status == 200
    # Adresse beim Suchdienst ohne Adresszusatz, der Suchtext im Header, kein Cookie
    assert f'content="/api/v1/linkvorschau/ergebnis|{SUCHTEXT}|"' in text
    assert ALLGEMEIN not in text
    assert kopf["Cache-Control"] == "no-cache, no-store, must-revalidate"
    # Und nicht im Protokoll des Frontends (#275)
    assert not [z for z in nginx.ausgabe(name) if SUCHTEXT in z]


def test_andere_seiten_unveraendert(frontend):
    basis, _ = frontend
    for pfad in ("/", "/hilfe", "/beitrag/keine-id", "/varianten/" + SICHTBAR):
        _, _, text = _holen(f"{basis}{pfad}")
        assert text == INDEX.read_text(encoding="utf-8"), pfad


def test_interne_adresse_von_aussen_nicht_erreichbar(frontend):
    basis, _ = frontend
    status, _, text = _holen(f"{basis}/_linkvorschau/beitrag/{SICHTBAR}")
    assert SPEZIFISCH not in text
    assert status in (204, 404)


@pytest.mark.usefixtures("docker_noetig")
@pytest.mark.parametrize("konfiguration", KONFIGURATIONEN)
def test_ohne_suchdienst_allgemeine_angaben(konfiguration):
    """Der Name gutgesagt-semantic-search loest nicht auf: nginx startet trotzdem,
    und nach der knappen Frist gelten die allgemeinen Angaben."""
    with _aufbauen(konfiguration, mit_suchdienst=False) as (basis, _):
        beginn = time.monotonic()
        status, _, text = _holen(f"{basis}/beitrag/{SICHTBAR}")
        dauer = time.monotonic() - beginn
    assert status == 200
    assert ALLGEMEIN in text
    assert dauer < 5


@pytest.mark.usefixtures("docker_noetig")
@pytest.mark.parametrize("konfiguration", KONFIGURATIONEN)
def test_ergebnisseite_ohne_suchdienst_allgemein_und_ohne_suchtext(konfiguration):
    with _aufbauen(konfiguration, mit_suchdienst=False) as (basis, name):
        status, _, text = _holen(f"{basis}/result?searchQuery={SUCHTEXT}")
        nginx.docker("stop", name)
        ausgabe = nginx.ausgabe(name)
    assert status == 200
    assert ALLGEMEIN in text
    assert SUCHTEXT not in text
    assert not [z for z in ausgabe if SUCHTEXT in z]
