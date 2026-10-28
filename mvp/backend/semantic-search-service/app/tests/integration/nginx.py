"""
Gemeinsame Hilfen fuer Tests gegen nginx aus dem Image des Frontend-Dockerfiles
(``test_webserver_protokoll.py``).

Der Container bekommt eine der Konfigurationen samt ``nginx.protokoll.conf`` und
lauscht an 127.0.0.1 auf einem Port, den Docker waehlt. Die Ausgabe (Zugriffs- und
Fehlerprotokoll) steht in ``docker logs``.
"""

import re
import subprocess
import uuid

from tests.integration import postgres

FRONTEND = postgres.REPO_WURZEL / "mvp" / "frontend" / "gutgesagt-frontend"

# Unter paralleler Last scheiterte ``docker run`` gelegentlich: RootlessKit konnte
# den Port, den Docker fuer ``--publish`` gewaehlt hatte, nicht binden ("address
# already in use"). Docker waehlt ihn aus dem Bereich, aus dem auch der Kernel die
# Absenderports ausgehender Verbindungen nimmt; vermutlich haelt ihn gerade eine
# solche. Ein neuer Versuch bekommt einen anderen Port (#383).
PORT_BELEGT = "address already in use"
VERSUCHE = 5


def image() -> str:
    """Das Image aus dem letzten ``FROM`` im Frontend-Dockerfile."""
    dockerfile = (FRONTEND / "Dockerfile").read_text(encoding="utf-8")
    return re.findall(r"^FROM\s+(\S+)", dockerfile, re.MULTILINE)[-1]


def _lauf(*argumente: str, timeout: int) -> subprocess.CompletedProcess:
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
    return lauf


def docker(*argumente: str, timeout: int = 60) -> str:
    """``docker`` aufrufen; liefert stdout, bei Exit != 0 ein Fehler mit stderr."""
    return _lauf(*argumente, timeout=timeout).stdout.strip()


def ausgabe(name: str) -> list[str]:
    """Die ganze Ausgabe des Containers: Zugriffsprotokoll (stdout),
    Fehlerprotokoll (stderr) und Startmeldungen. Beide Stroeme landen im
    ``json-file``-Protokoll von Docker."""
    lauf = _lauf("logs", name, timeout=30)
    return (lauf.stdout + lauf.stderr).splitlines()


def starten(konfiguration: str) -> str:
    """Container starten, bei belegtem Port neu; liefert den Containernamen."""
    for versuch in range(1, VERSUCHE + 1):
        name = f"gutgesagt-itest-nginx-{uuid.uuid4().hex[:8]}"
        try:
            docker(
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
                image(),
                timeout=300,
            )
        except (RuntimeError, subprocess.TimeoutExpired) as fehler:
            # Der gescheiterte Container bleibt sonst angelegt liegen.
            entfernen(name)
            if PORT_BELEGT in str(fehler) and versuch < VERSUCHE:
                continue
            raise
        return name
    raise AssertionError("VERSUCHE muss mindestens 1 sein")


def entfernen(name: str) -> None:
    """Container entfernen; ein haengender Daemon beendet den Lauf mit Fehler."""
    subprocess.run(["docker", "rm", "--force", name], capture_output=True, timeout=60)
