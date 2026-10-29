"""
Betriebskennzahlen unter GET /metrics (#420).

Gezaehlt wird je Methode, Routen-Vorlage und Statusklasse; dazu die Dauer der Suche als
Histogramm. Geprueft an einer kleinen App, in die ``einbinden`` aus api/metrics_betrieb.py
Middleware und Endpunkt haengt, ueber HTTP wie der Prometheus-Scraper.
"""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.metrics_betrieb import einbinden


def _client() -> TestClient:
    app = FastAPI()
    einbinden(app)

    @app.get("/api/v1/beitrag/{beitrag_id}")
    async def beitrag(beitrag_id: str):
        if beitrag_id == "fehlt":
            raise HTTPException(status_code=404)
        if beitrag_id == "kaputt":
            raise RuntimeError("Fehler im Endpunkt")
        return {"id": beitrag_id}

    # Dieselbe Vorlage wie der echte Suchendpunkt; dessen Dienste braucht hier keiner.
    @app.post("/api/v1/search/searchByText")
    async def suche():
        return {}

    return TestClient(app, raise_server_exceptions=False)


def _zeilen(client: TestClient) -> list[str]:
    antwort = client.get("/metrics")
    assert antwort.status_code == 200
    return antwort.text.splitlines()


def test_metrics_zaehlt_routen_vorlage_statt_pfad():
    client = _client()
    client.get("/api/v1/beitrag/0c6f2a1e-1111-4222-8333-944455556666")
    client.get("/api/v1/beitrag/zweiter")

    zeilen = _zeilen(client)

    assert (
        'gutgesagt_http_requests_total{method="GET",'
        'route="/api/v1/beitrag/{beitrag_id}",status="2xx"} 2.0'
    ) in zeilen
    assert not any("0c6f2a1e" in z or "zweiter" in z for z in zeilen)


def test_metrics_unbekannter_pfad_ohne_pfad_im_label():
    """Ein 404 ohne Route traegt den Pfad nicht weiter: er koennte eine Kennung sein."""
    client = _client()
    client.get("/api/v1/nutzer/kennung-4711/profil")

    zeilen = _zeilen(client)

    assert (
        'gutgesagt_http_requests_total{method="GET",route="unmatched",status="4xx"} 1.0'
    ) in zeilen
    assert not any("kennung-4711" in z for z in zeilen)


def test_metrics_statusklasse_fuer_fehler():
    client = _client()
    client.get("/api/v1/beitrag/fehlt")
    client.get("/api/v1/beitrag/kaputt")

    zeilen = _zeilen(client)

    vorlage = 'method="GET",route="/api/v1/beitrag/{beitrag_id}"'
    assert f'gutgesagt_http_requests_total{{{vorlage},status="4xx"}} 1.0' in zeilen
    assert f'gutgesagt_http_requests_total{{{vorlage},status="5xx"}} 1.0' in zeilen


def test_metrics_unbekannte_methode_als_other():
    client = _client()
    client.request("BREW", "/api/v1/beitrag/kanne")

    zeilen = _zeilen(client)

    assert any('method="OTHER"' in z for z in zeilen)
    assert not any("BREW" in z for z in zeilen)


def _wert(zeilen: list[str], name: str) -> float:
    return float(next(z for z in zeilen if z.startswith(name + " ")).split()[-1])


def test_metrics_histogramm_nur_fuer_die_suche():
    client = _client()
    client.post("/api/v1/search/searchByText", json={"query_text": "egal"})
    client.post("/api/v1/search/searchByText", json={"query_text": "egal"})
    client.get("/api/v1/beitrag/anderes")

    zeilen = _zeilen(client)

    assert "# TYPE gutgesagt_search_duration_seconds histogram" in zeilen
    assert _wert(zeilen, "gutgesagt_search_duration_seconds_count") == 2.0
    assert 'gutgesagt_search_duration_seconds_bucket{le="+Inf"} 2.0' in zeilen
    assert _wert(zeilen, "gutgesagt_search_duration_seconds_sum") >= 0.0


def test_metrics_histogramm_buckets_kumulativ():
    """Jeder Bucket zaehlt alle Suchen bis zu seiner Grenze, also nie weniger als der vorige."""
    client = _client()
    client.post("/api/v1/search/searchByText", json={"query_text": "egal"})

    zeilen = _zeilen(client)
    buckets = [
        float(z.split()[-1])
        for z in zeilen
        if z.startswith("gutgesagt_search_duration_seconds_bucket")
    ]

    assert buckets == sorted(buckets)
    assert buckets[-1] == 1.0


def test_main_app_liefert_metrics_ausserhalb_von_api():
    """Der Suchdienst selbst haengt die Middleware ein; der Pfad liegt nicht unter /api."""
    from api.metrics_betrieb import SUCHE
    from main import app

    # Die Vorlage, an der das Histogramm haengt, muss es in der App geben; sonst bliebe
    # es nach einer Umbenennung von Prefix oder Route still leer.
    assert SUCHE in {route.path for route in app.routes}
    client = TestClient(app)
    client.get("/api/v1/content/")

    antwort = client.get("/metrics")

    assert antwort.status_code == 200
    assert antwort.headers["content-type"].startswith("text/plain; version=0.0.4")
    assert (
        'gutgesagt_http_requests_total{method="GET",route="/api/v1/content/",'
        'status="2xx"}'
    ) in antwort.text
