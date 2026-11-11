"""
Ausgebaute Endpunkte ohne Aufrufer in Frontend und BFF (#272): die Wurzel-Stubs
der Router ("This is a test endpoint"), die Suche je Typ fuer Kommentar und
Hintergrundinfo, ``generic_text/getAll`` und ``content/searchContent``. Gesucht
wird ueber ``/api/v1/search/searchByText``, gelistet ueber ``content/recent``;
``content/getAll`` bleibt fuer Admins (test_content_get_all_nur_admins.py).

Festgehalten, damit niemand einen davon als Regression zurueckholt: Jeder weitere
Weg zu Beitraegen muss die Antwort-Allowlist (dtos/beitrag.py) eigens bekommen.
"""

import pytest
from fastapi.routing import APIRoute

from main import app

AUSGEBAUT = [
    ("GET", "/api/v1/commentary/"),
    ("GET", "/api/v1/content/"),
    ("GET", "/api/v1/contribution/"),
    ("GET", "/api/v1/generic_text/"),
    ("GET", "/api/v1/post/"),
    ("GET", "/api/v1/reference/"),
    ("GET", "/api/v1/search/"),
    ("GET", "/api/v1/statement/"),
    ("POST", "/api/v1/commentary/searchCommentaries"),
    ("POST", "/api/v1/generic_text/searchGenericText"),
    ("GET", "/api/v1/generic_text/getAll"),
    ("POST", "/api/v1/content/searchContent"),
]


def _routen() -> set:
    return {
        (methode, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for methode in route.methods
    }


@pytest.mark.unit
@pytest.mark.parametrize("methode, pfad", AUSGEBAUT)
def test_endpunkt_ist_nicht_eingebunden(methode, pfad):
    assert (methode, pfad) not in _routen()


@pytest.mark.unit
def test_gegenprobe_die_genutzten_wege_sind_eingebunden():
    routen = _routen()

    assert ("POST", "/api/v1/search/searchByText") in routen
    assert ("GET", "/api/v1/content/getAll") in routen
    assert ("GET", "/api/v1/content/recent") in routen
