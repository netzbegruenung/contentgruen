"""
Das Zugriffsprotokoll des Webservers der Anwendung (nginx im Frontend-Image, #275).

Je Suche eine Zeile mit genauer Uhrzeit liesse sich, je Tag durchgezaehlt, mit dem
Anlagezeitpunkt der Aussage verbinden, die dieselbe Suche angelegt hat, und ueber
die IP-Adresse mit einer Person. Schlimmer noch stand der Suchtext selbst im
Protokoll: in der Adresse (``/result?searchQuery=...``) bei jedem direkten Aufruf
der Ergebnisseite und als verweisende Seite bei jeder Anfrage, die diese Seite
ausloest. Der Webserver schreibt deshalb keine Zeile fuer die Suche und fuer die
Ergebnisseite, von jeder anderen Anfrage nur den Pfad, ohne Adresszusatz und ohne
verweisende Seite, und ins Fehlerprotokoll keine Zeile fuer fehlende Dateien (sie
truege Adresse und verweisende Seite).

Startet nginx aus dem Image des Frontend-Dockerfiles mit beiden Konfigurationen
(``nginx.conf`` fuer Test und Produktion, ``nginx.docker.conf`` fuer den Dev-Stack)
samt ``nginx.protokoll.conf`` und liest Zugriffs- und Fehlerprotokoll aus
``docker logs`` (stdout und stderr). Ohne Docker uebersprungen, in der CI
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
    lauf = subprocess.run(
        ["docker", *argumente],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if lauf.returncode:
        raise RuntimeError(
            f"docker {argumente[0]}: Exit {lauf.returncode}: {lauf.stderr.strip()}"
        )
    return lauf.stdout.strip()


@pytest.fixture(scope="module")
def docker_noetig():
    if postgres.docker_verfuegbar():
        return
    grund = "Docker fehlt: nginx laesst sich nicht starten"
    if os.environ.get("CI") or stack.pflicht():
        pytest.fail(grund)
    pytest.skip(grund)


# Den freien Port waehlt Docker aus dem Bereich, aus dem auch der Kernel die
# Absenderports ausgehender Verbindungen nimmt. Haelt eine davon (etwa ein
# paralleler Testlauf) den Port gerade, scheitert ``docker run`` im rootless
# Docker an RootlessKit; ein neuer Versuch bekommt einen anderen Port (#383).
PORT_BELEGT = "address already in use"
VERSUCHE = 5


def _starten(konfiguration: str) -> str:
    """Container starten, bei belegtem Port neu; liefert den Containernamen."""
    versuch = 1
    while True:
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
                "--volume",
                f"{FRONTEND / 'nginx.protokoll.conf'}:/etc/nginx/conf.d/00-protokoll.conf:ro",
                "--publish",
                "127.0.0.1::80",
                _image(),
                timeout=300,
            )
            return name
        except RuntimeError as fehler:
            # Der gescheiterte Container bleibt angelegt liegen.
            _entfernen(name)
            if PORT_BELEGT not in str(fehler) or versuch == VERSUCHE:
                raise
        versuch += 1


def _entfernen(name: str) -> None:
    subprocess.run(["docker", "rm", "--force", name], capture_output=True)


@contextmanager
def _nginx(konfiguration: str) -> Iterator[tuple[str, str]]:
    """nginx mit der Konfiguration starten; liefert Basisadresse und Containername.

    ``gutgesagt-bff`` zeigt auf den Container selbst: nginx.docker.conf braucht den
    Namen beim Start, eine Antwort des BFF braucht der Test nicht.
    """
    name = _starten(konfiguration)
    try:
        adresse = _docker("port", name, "80/tcp").splitlines()[0]
        basis = f"http://{adresse}"
        frist = time.monotonic() + 30
        while True:
            try:
                urllib.request.urlopen(f"{basis}/", timeout=1).close()
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
        _entfernen(name)


def _anfrage(adresse: str, methode: str = "GET", referer: str = "") -> None:
    anfrage = urllib.request.Request(adresse, method=methode, data=None)
    if referer:
        anfrage.add_header("Referer", referer)
    try:
        urllib.request.urlopen(anfrage, timeout=5).close()
    except urllib.error.HTTPError as fehler:
        fehler.close()  # 404/405/502 sind hier egal, es zaehlt nur die Logzeile.


def _zugriffe(name: str) -> list[str]:
    """Die ganze Ausgabe des Containers: Zugriffsprotokoll (stdout),
    Fehlerprotokoll (stderr) und Startmeldungen. Beide Stroeme landen im
    ``json-file``-Protokoll von Docker.

    Erst nach dem Anhalten gelesen: Docker meldet den Container erst als
    angehalten, wenn es beide Stroeme ganz uebernommen hat. Sofort gelesen
    koennten unter Last die letzten Zeilen noch fehlen."""
    _docker("stop", name)
    ausgabe = subprocess.run(
        ["docker", "logs", name], capture_output=True, text=True, timeout=30
    )
    return (ausgabe.stdout + ausgabe.stderr).splitlines()


@pytest.mark.usefixtures("docker_noetig")
@pytest.mark.parametrize("konfiguration", ["nginx.conf", "nginx.docker.conf"])
def test_protokoll_ohne_suchtext(konfiguration):
    ergebnisseite = f"/result?searchQuery={SUCHTEXT}"
    with _nginx(konfiguration) as (basis, name):
        _anfrage(f"{basis}/hilfe?von={SUCHTEXT}")
        # favicon.ico gibt es nicht: 404, frueher mit Zeile im Fehlerprotokoll.
        _anfrage(f"{basis}/favicon.ico", referer=f"{basis}{ergebnisseite}")

        zugriffe = _zugriffe(name)

    assert any("/hilfe" in zeile for zeile in zugriffe), zugriffe
    assert any("/favicon.ico" in zeile for zeile in zugriffe), zugriffe
    assert not [zeile for zeile in zugriffe if SUCHTEXT in zeile]


@pytest.mark.usefixtures("docker_noetig")
@pytest.mark.parametrize("konfiguration", ["nginx.conf", "nginx.docker.conf"])
def test_keine_zeile_je_aufruf_der_ergebnisseite(konfiguration):
    """Ein direkter Aufruf von /result loest eine Suche aus; seine Zeile trueg
    deren genaue Uhrzeit."""
    with _nginx(konfiguration) as (basis, name):
        _anfrage(f"{basis}/result?searchQuery={SUCHTEXT}")
        _anfrage(f"{basis}/Result/")
        _anfrage(f"{basis}/hilfe")

        zugriffe = _zugriffe(name)

    assert any("/hilfe" in zeile for zeile in zugriffe), zugriffe
    assert not [zeile for zeile in zugriffe if "/result" in zeile.lower()]


@pytest.mark.usefixtures("docker_noetig")
def test_keine_zeile_je_suche():
    with _nginx("nginx.docker.conf") as (basis, name):
        _anfrage(f"{basis}{SUCHE}", methode="POST")
        _anfrage(f"{basis}{SUCHE.lower()}/", methode="POST")
        _anfrage(f"{basis}/api/v1/metrics/getMetrics")

        zugriffe = _zugriffe(name)

    assert any("/api/v1/metrics/getMetrics" in zeile for zeile in zugriffe), zugriffe
    # Fehlerprotokoll ausgenommen: Antwortet das BFF nicht, schreibt nginx dort die
    # Anfrage (nur Dev-Stack, nur im Fehlerfall; docs/LOESCHKONZEPT.md).
    zugriffe = [zeile for zeile in zugriffe if "[error]" not in zeile]
    assert not [zeile for zeile in zugriffe if "searchbytext" in zeile.lower()]


@pytest.mark.parametrize(
    ("fehler", "starts"),
    [
        ("bind: address already in use", 2),
        ("No such image", 1),
    ],
)
def test_neuer_start_nur_bei_belegtem_port(monkeypatch, fehler, starts):
    """Ohne Docker: Nur ein belegter Port fuehrt zu einem neuen Versuch,
    jeder gescheiterte Container wird entfernt."""
    gestartet, entfernt = [], []

    def docker(*argumente, timeout=60):
        gestartet.append(argumente[argumente.index("--name") + 1])
        if len(gestartet) == 1:
            raise RuntimeError(f"docker run: Exit 125: {fehler}")
        return "id"

    monkeypatch.setattr(f"{__name__}._docker", docker)
    monkeypatch.setattr(f"{__name__}._image", lambda: "nginx:alpine")
    monkeypatch.setattr(f"{__name__}._entfernen", entfernt.append)

    if starts == 1:
        with pytest.raises(RuntimeError, match=fehler):
            _starten("nginx.conf")
    else:
        assert _starten("nginx.conf") == gestartet[-1]

    assert len(gestartet) == starts
    assert entfernt == gestartet[:1]
    assert len(set(gestartet)) == starts


def test_browser_schickt_den_suchtext_nicht_als_verweisende_seite():
    """Fuer den vorgelagerten Webserver, dessen Format nicht hier im Repo steht.

    Ohne Vorgabe schicken Browser bei Anfragen an dieselbe Seite die volle Adresse
    der Ergebnisseite als Referer mit. ``strict-origin`` laesst nur den Ursprung
    uebrig; die Angabe muss vor der ersten Anfrage der Seite stehen.
    """
    index = (FRONTEND / "src" / "index.html").read_text(encoding="utf-8")
    kopf = index[: index.index("<link")]

    assert re.search(r'<meta name="referrer" content="strict-origin">', kopf)
