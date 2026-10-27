"""
Das Zugriffsprotokoll des Webservers der Anwendung (nginx im Frontend-Image, #275).

Je Suche eine Zeile mit genauer Uhrzeit liesse sich, je Tag durchgezaehlt, mit dem
Anlagezeitpunkt der Aussage verbinden, die dieselbe Suche angelegt hat, und ueber
die IP-Adresse mit einer Person. Schlimmer noch stand der Suchtext selbst im
Protokoll: in der Adresse (``/result?searchQuery=...``) bei jedem direkten Aufruf
der Ergebnisseite und als verweisende Seite bei jeder Anfrage, die diese Seite
ausloest. Der Webserver schreibt deshalb keine Zeile fuer die Suche und von jeder
anderen Anfrage nur den Pfad, ohne Adresszusatz und ohne verweisende Seite.

Startet nginx aus dem Image des Frontend-Dockerfiles mit beiden Konfigurationen
(``nginx.conf`` fuer Test und Produktion, ``nginx.docker.conf`` fuer den Dev-Stack)
und liest das Protokoll aus ``docker logs``. Ohne Docker uebersprungen, in der CI
und im Pflichtmodus (``stack.py``) ein Fehler.
"""

import os
import re
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from typing import Iterator

import pytest

from tests.integration import postgres, stack

pytestmark = pytest.mark.integration

FRONTEND = postgres.REPO_WURZEL / "mvp" / "frontend" / "gutgesagt-frontend"
SUCHTEXT = "Waermepumpe-im-Altbau-275"
SUCHE = "/api/v1/search/searchByText"


def _image() -> str:
    dockerfile = (FRONTEND / "Dockerfile").read_text(encoding="utf-8")
    return re.findall(r"^FROM\s+(\S+)", dockerfile, re.MULTILINE)[-1]


def _docker(*argumente: str, timeout: int = 60) -> str:
    return subprocess.run(
        ["docker", *argumente],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    ).stdout.strip()


@pytest.fixture(scope="module", autouse=True)
def _docker_noetig():
    if postgres.docker_verfuegbar():
        return
    grund = "Docker fehlt: nginx laesst sich nicht starten"
    if os.environ.get("CI") or stack.pflicht():
        pytest.fail(grund)
    pytest.skip(grund)


@contextmanager
def _nginx(konfiguration: str) -> Iterator[tuple[str, str]]:
    """nginx mit der Konfiguration starten; liefert Basisadresse und Containername.

    ``gutgesagt-bff`` zeigt auf den Container selbst: nginx.docker.conf braucht den
    Namen beim Start, eine Antwort des BFF braucht der Test nicht.
    """
    name = f"gutgesagt-itest-nginx-{uuid.uuid4().hex[:8]}"
    try:
        _docker(
            "run",
            "--detach",
            "--name",
            name,
            "--label",
            "gutgesagt-itest",
            "--add-host",
            "gutgesagt-bff:127.0.0.1",
            "--volume",
            f"{FRONTEND / konfiguration}:/etc/nginx/conf.d/default.conf:ro",
            "--publish",
            "127.0.0.1::80",
            _image(),
            timeout=300,
        )
        adresse = _docker("port", name, "80/tcp").splitlines()[0]
        basis = f"http://{adresse}"
        frist = time.monotonic() + 30
        while True:
            try:
                urllib.request.urlopen(f"{basis}/", timeout=1)
                break
            except urllib.error.HTTPError:
                break
            except OSError:
                if time.monotonic() > frist:
                    raise RuntimeError(
                        f"nginx startet nicht: {_docker('logs', name)}"
                    ) from None
                time.sleep(0.3)
        yield basis, name
    finally:
        subprocess.run(["docker", "rm", "--force", name], capture_output=True)


def _anfrage(adresse: str, methode: str = "GET", referer: str = "") -> None:
    anfrage = urllib.request.Request(adresse, method=methode, data=None)
    if referer:
        anfrage.add_header("Referer", referer)
    try:
        urllib.request.urlopen(anfrage, timeout=5)
    except urllib.error.HTTPError:
        pass  # 404/405/502 sind hier egal, es zaehlt nur die Logzeile.


def _zugriffe(name: str) -> list[str]:
    """Die Ausgabe des Containers auf stdout: Zugriffsprotokoll und Startmeldungen."""
    return subprocess.run(
        ["docker", "logs", name], capture_output=True, text=True, timeout=30
    ).stdout.splitlines()


@pytest.mark.parametrize("konfiguration", ["nginx.conf", "nginx.docker.conf"])
def test_protokoll_ohne_suchtext(konfiguration):
    ergebnisseite = f"/result?searchQuery={SUCHTEXT}"
    with _nginx(konfiguration) as (basis, name):
        _anfrage(f"{basis}{ergebnisseite}")
        _anfrage(f"{basis}/favicon.ico", referer=f"{basis}{ergebnisseite}")

        zugriffe = _zugriffe(name)

    assert any("/result" in zeile for zeile in zugriffe), zugriffe
    assert any("/favicon.ico" in zeile for zeile in zugriffe), zugriffe
    assert not [zeile for zeile in zugriffe if SUCHTEXT in zeile]


def test_keine_zeile_je_suche():
    with _nginx("nginx.docker.conf") as (basis, name):
        _anfrage(f"{basis}{SUCHE}", methode="POST")
        _anfrage(f"{basis}/api/v1/metrics/getMetrics")

        zugriffe = _zugriffe(name)

    assert any("/api/v1/metrics/getMetrics" in zeile for zeile in zugriffe), zugriffe
    assert not [zeile for zeile in zugriffe if "searchByText" in zeile]


def test_browser_schickt_den_suchtext_nicht_als_verweisende_seite():
    """Fuer den vorgelagerten Webserver, dessen Format nicht hier im Repo steht.

    Ohne Vorgabe schicken Browser bei Anfragen an dieselbe Seite die volle Adresse
    der Ergebnisseite als Referer mit. ``strict-origin`` laesst nur den Ursprung
    uebrig; die Angabe muss vor der ersten Anfrage der Seite stehen.
    """
    index = (FRONTEND / "src" / "index.html").read_text(encoding="utf-8")
    kopf = index[: index.index("<link")]

    assert re.search(r'<meta name="referrer" content="strict-origin">', kopf)
