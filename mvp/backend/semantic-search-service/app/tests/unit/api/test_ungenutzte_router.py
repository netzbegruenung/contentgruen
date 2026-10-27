"""
Router ohne Aufrufer sind nicht eingebunden.

/api/v1/candidates (passende Kommentare zu einer Aussage, voller TODOs, mit
Testendpunkt "/") und /api/v1/scores (nie eingebunden, nur Platzhalter) hatten
in Frontend, BFF, Skripten und Tests keinen Aufrufer. Das BFF leitet jeden Pfad
weiter; ein eingebundener Router waere also von aussen erreichbar.
"""

import pytest

from main import app

ENTFERNTE_PRAEFIXE = ["/api/v1/candidates", "/api/v1/scores"]


@pytest.mark.parametrize("praefix", ENTFERNTE_PRAEFIXE)
def test_app_routes_router_ohne_aufrufer_nicht_eingebunden(praefix):
    pfade = [getattr(route, "path", "") for route in app.routes]

    assert not [p for p in pfade if p.startswith(praefix)]
