"""
Ob der Stack fuer die Integrationssuite da ist: Qdrant und PostgreSQL.

Ohne Stack ueberspringen sich die Tests, damit ein Lauf ohne Docker gruen bleibt.
Im Pflichtmodus (``INTEGRATION_STACK_PFLICHT=1``, gesetzt von
``scripts/check.sh --integration``) waere das ein falsches Gruen: Dann bricht der
Lauf vor dem ersten Test ab und nennt, was fehlt (``pytest_sessionstart`` in
``conftest.py``).
"""

import os
from typing import Mapping, Optional

import requests

from tests.integration import postgres

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
PFLICHT_VARIABLE = "INTEGRATION_STACK_PFLICHT"


def pflicht(env: Optional[Mapping[str, str]] = None) -> bool:
    env = os.environ if env is None else env
    return env.get(PFLICHT_VARIABLE, "") not in ("", "0")


def pflicht_ausser_in_ci(env: Optional[Mapping[str, str]] = None) -> bool:
    """Ob ein Dienst, den nur der Dev-Stack oder der Entwicklungsrechner hat, fehlen darf.

    Gilt fuer das BFF (Tests unter ``api/``) und fuer Docker (nginx-Container in
    ``test_webserver_protokoll.py``). Im Pflichtmodus ist ein Fehlen ein Fehler,
    ausser in der CI (``CI`` gesetzt): Woodpecker startet Qdrant und PostgreSQL,
    aber kein BFF, und der Runner hat keinen Docker-Socket (docs/CI.md). Dort
    ueberspringen sich die Tests sichtbar in den SKIPPED-Zeilen (#460).
    """
    env = os.environ if env is None else env
    return pflicht(env) and not env.get("CI")


def qdrant_erreichbar(url: str = QDRANT_URL) -> bool:
    """True, wenn unter ``url`` ein Qdrant auf /healthz antwortet."""
    try:
        return requests.get(f"{url}/healthz", timeout=2).status_code == 200
    except requests.RequestException:
        return False


def postgres_fehlt(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """Warum es kein PostgreSQL gibt, oder None.

    Die eine Regel fuer Vorabpruefung und Fixture ``postgres_url``: Ist
    ``POSTGRES_TEST_DATABASE_URL`` gesetzt, muss die Datenbank erreichbar sein,
    sonst braucht es Docker fuer einen Wegwerf-Container.
    """
    env = os.environ if env is None else env
    url = env.get(postgres.URL_VARIABLE)
    if url:
        if not postgres.erreichbar(url):
            return f"PostgreSQL aus {postgres.URL_VARIABLE} nicht erreichbar"
    elif not postgres.docker_verfuegbar():
        return (
            f"PostgreSQL: weder {postgres.URL_VARIABLE} gesetzt noch Docker "
            "fuer einen Wegwerf-Container verfuegbar"
        )
    return None


def fehlende_dienste(
    qdrant_url: str = QDRANT_URL, env: Optional[Mapping[str, str]] = None
) -> list[str]:
    """Je fehlendem Dienst eine Meldung; leer, wenn der Stack da ist."""
    fehlend = []
    if not qdrant_erreichbar(qdrant_url):
        fehlend.append(
            f"Qdrant nicht erreichbar unter {qdrant_url} "
            "(mvp/run-local.sh up, oder QDRANT_URL setzen)"
        )
    grund = postgres_fehlt(env)
    if grund:
        fehlend.append(grund)
    return fehlend
