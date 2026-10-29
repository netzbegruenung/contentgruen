"""
Betriebskennzahlen fuer das Monitoring: GET /metrics im Prometheus-Textformat (#420).

Nicht zu verwechseln mit /api/v1/metrics: das sind fachliche Kennzahlen fuer Admins und
die Startseite. Hier steht nur, was der Betrieb fuer Alarme braucht: Anfragen je Methode,
Routen-Vorlage und Statusklasse, dazu die Dauer der Suche.

Label-Werte kommen nie aus der Anfrage selbst. Die Route ist die Vorlage, unter der
FastAPI die Anfrage zugeordnet hat (``/api/v1/usage/content/{content_id}/usage``), nicht
der Pfad mit der ID darin; ohne Treffer steht dort ``unmatched``. Kennung, Suchtext und
Sitzung kommen in keinem Header und keinem Body vor, den diese Middleware liest.

Gesperrt ist /metrics am BFF (EndpointPolicy.Blocked): YARP leitet sonst jeden Pfad
weiter. Der Scraper fragt den Suchdienst direkt im internen Netz.
"""

import bisect
import threading
import time
from collections import defaultdict

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import PlainTextResponse

router = APIRouter()

# Kein Zaehler fuer frei waehlbare Methoden: sonst waechst die Zahl der Zeitreihen mit
# jedem Wort, das jemand in die erste Zeile der Anfrage schreibt.
_METHODEN = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
_OHNE_ROUTE = "unmatched"
SUCHE = "/api/v1/search/searchByText"
# Obergrenzen in Sekunden. Eine Suche bettet ein und fragt Qdrant mehrfach ab; ueblich
# ist weniger als eine Sekunde, die oberen Stufen fangen Lastspitzen und Kaltstarts.
_SUCHDAUER_GRENZEN = (0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)


class Betriebskennzahlen:
    """Zaehlerstaende im Speicher des Prozesses; ein Neustart setzt sie auf null."""

    def __init__(self) -> None:
        self._sperre = threading.Lock()
        self._anfragen: dict[tuple[str, str, str], int] = defaultdict(int)
        # Je Grenze die Suchen, die genau in diese Stufe fallen; der letzte Platz
        # zaehlt die ueber der hoechsten Grenze. Kumuliert wird erst bei der Ausgabe.
        self._suchdauer_stufen = [0] * (len(_SUCHDAUER_GRENZEN) + 1)
        self._suchdauer_summe = 0.0

    def anfrage(self, methode: str, route: str, status: int) -> None:
        methode = methode if methode in _METHODEN else "OTHER"
        schluessel = (methode, route, f"{status // 100}xx")
        with self._sperre:
            self._anfragen[schluessel] += 1

    def suchdauer(self, sekunden: float) -> None:
        stufe = bisect.bisect_left(_SUCHDAUER_GRENZEN, sekunden)
        with self._sperre:
            self._suchdauer_stufen[stufe] += 1
            self._suchdauer_summe += sekunden

    def als_text(self) -> str:
        with self._sperre:
            anfragen = sorted(self._anfragen.items())
            stufen = list(self._suchdauer_stufen)
            summe = self._suchdauer_summe
        zeilen = [
            "# HELP gutgesagt_http_requests_total Anfragen je Methode, Routen-Vorlage "
            "und Statusklasse.",
            "# TYPE gutgesagt_http_requests_total counter",
        ]
        for (methode, route, status), anzahl in anfragen:
            zeilen.append(
                f'gutgesagt_http_requests_total{{method="{methode}",'
                f'route="{_label(route)}",status="{status}"}} {float(anzahl)}'
            )

        zeilen += [
            "# HELP gutgesagt_search_duration_seconds Dauer von searchByText.",
            "# TYPE gutgesagt_search_duration_seconds histogram",
        ]
        bisher = 0
        for grenze, anzahl in zip((*_SUCHDAUER_GRENZEN, "+Inf"), stufen):
            bisher += anzahl
            zeilen.append(
                f'gutgesagt_search_duration_seconds_bucket{{le="{grenze}"}} '
                f"{float(bisher)}"
            )
        zeilen.append(f"gutgesagt_search_duration_seconds_sum {summe}")
        zeilen.append(f"gutgesagt_search_duration_seconds_count {float(bisher)}")
        return "\n".join(zeilen) + "\n"


def _label(wert: str) -> str:
    """Label-Wert nach dem Textformat maskieren (Backslash, Anfuehrungszeichen, Umbruch)."""
    return wert.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class BetriebskennzahlenMiddleware:
    """Reine ASGI-Middleware: liest nach dem Routing ``scope["route"]`` und den Status."""

    def __init__(self, app, kennzahlen: Betriebskennzahlen) -> None:
        self.app = app
        self.kennzahlen = kennzahlen

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status = 500
        beginn = time.perf_counter()

        async def senden(nachricht):
            nonlocal status
            if nachricht["type"] == "http.response.start":
                status = nachricht["status"]
            await send(nachricht)

        try:
            await self.app(scope, receive, senden)
        finally:
            # FastAPI legt die zugeordnete Route in denselben Scope (APIRoute.matches).
            route = getattr(scope.get("route"), "path", None) or _OHNE_ROUTE
            self.kennzahlen.anfrage(scope["method"], route, status)
            if route == SUCHE and scope["method"] == "POST":
                self.kennzahlen.suchdauer(time.perf_counter() - beginn)


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request) -> PlainTextResponse:
    return PlainTextResponse(
        request.app.state.betriebskennzahlen.als_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


def einbinden(app: FastAPI) -> None:
    """Middleware und GET /metrics an die App haengen."""
    kennzahlen = Betriebskennzahlen()
    app.state.betriebskennzahlen = kennzahlen
    app.add_middleware(BetriebskennzahlenMiddleware, kennzahlen=kennzahlen)
    app.include_router(router)
