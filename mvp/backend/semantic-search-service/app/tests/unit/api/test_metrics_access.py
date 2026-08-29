"""
Zugriffsschutz und Caching der Metrics-Endpunkte.

Die sechs MVP-Endpunkte liefern Betriebskennzahlen (taegliche aktive Nutzer,
Suchvolumen, Vote-Verhaeltnisse) und waren ohne jede Auth-Dependency erreichbar.
/getMetrics bleibt bewusst oeffentlich -- es liefert nur Bestandszaehler und wird
von der anonym erreichbaren Startseite aufgerufen -- bekommt dafuer aber einen
TTL-Cache, weil es sonst unbegrenzt oft vier Qdrant-Counts ausloesen kann.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import metrics as metrics_module
from api.v1.metrics import router as metrics_router
from dependencies import (
    get_commentary_service,
    get_reference_service,
    get_settings,
    get_statement_service,
)

ADMIN_ONLY_PATHS = [
    "/api/v1/metrics/mvp-dashboard",
    "/api/v1/metrics/daily-active-users",
    "/api/v1/metrics/searches-per-user",
    "/api/v1/metrics/content-created",
    "/api/v1/metrics/usage-trend",
    "/api/v1/metrics/helpful-rate",
]


@pytest.fixture
def client():
    """App nur mit dem Metrics-Router; die Content-Services sind gemockt."""
    app = FastAPI()
    app.include_router(metrics_router, prefix="/api/v1/metrics")

    statement_service = Mock()
    statement_service.count_curated = AsyncMock(return_value=11)
    commentary_service = Mock()
    commentary_service.count = AsyncMock(return_value=22)
    reference_service = Mock()
    reference_service.count = AsyncMock(return_value=33)

    app.dependency_overrides[get_statement_service] = lambda: statement_service
    app.dependency_overrides[get_commentary_service] = lambda: commentary_service
    app.dependency_overrides[get_reference_service] = lambda: reference_service
    app.dependency_overrides[get_settings] = lambda: Mock()

    metrics_module._metrics_cache = None
    yield TestClient(app)
    metrics_module._metrics_cache = None


class TestAdminOnlyEndpoints:
    """Die sechs MVP-Endpunkte verlangen X-User plus X-Is-Admin."""

    @pytest.mark.parametrize("path", ADMIN_ONLY_PATHS)
    def test_anonymous_is_unauthorized(self, client, path):
        assert client.get(path).status_code == 401

    @pytest.mark.parametrize("path", ADMIN_ONLY_PATHS)
    def test_anonymous_user_header_is_unauthorized(self, client, path):
        response = client.get(path, headers={"X-User": "anonymous"})
        assert response.status_code == 401

    @pytest.mark.parametrize("path", ADMIN_ONLY_PATHS)
    def test_authenticated_non_admin_is_forbidden(self, client, path):
        response = client.get(path, headers={"X-User": "normalo"})
        assert response.status_code == 403

    @pytest.mark.parametrize("path", ADMIN_ONLY_PATHS)
    def test_forged_admin_header_alone_is_unauthorized(self, client, path):
        """
        X-Is-Admin ohne X-User reicht nicht. Beide Header werden am BFF gestrippt
        und aus den Claims neu gesetzt (IdentityHeaderTransform); hier ist nur
        festgehalten, dass die Dependency sich nicht allein auf das Flag verlaesst.
        """
        response = client.get(path, headers={"X-Is-Admin": "true"})
        assert response.status_code == 401


class TestGetMetricsStaysPublic:
    """
    /getMetrics muss ohne Anmeldung erreichbar bleiben: die Startseite ruft es
    ueber den PublicGuard auch fuer anonyme Besucher auf.
    """

    def test_anonymous_access_succeeds(self, client):
        with patch.object(metrics_module, "QdrantRepositoryFactory") as factory:
            repository = Mock()
            repository.count = AsyncMock(return_value=44)
            factory.return_value.create_content_repository.return_value = repository

            response = client.get("/api/v1/metrics/getMetrics")

        assert response.status_code == 200
        body = response.json()
        assert body["content_count"] == 44
        assert body["statement_count"] == 11
        assert body["commentary_count"] == 22
        assert body["reference_count"] == 33


class TestGetMetricsCache:
    """Der TTL-Cache haelt die Qdrant-Last unabhaengig von der Aufrufzahl."""

    def test_repeated_calls_query_qdrant_once(self, client):
        with patch.object(metrics_module, "QdrantRepositoryFactory") as factory:
            repository = Mock()
            repository.count = AsyncMock(return_value=99)
            factory.return_value.create_content_repository.return_value = repository

            for _ in range(20):
                assert client.get("/api/v1/metrics/getMetrics").status_code == 200

            # Ohne Cache waeren es 20 Zaehlungen gewesen.
            assert repository.count.await_count == 1

    def test_expired_cache_is_refreshed(self, client):
        with patch.object(metrics_module, "QdrantRepositoryFactory") as factory:
            repository = Mock()
            repository.count = AsyncMock(return_value=99)
            factory.return_value.create_content_repository.return_value = repository

            assert client.get("/api/v1/metrics/getMetrics").status_code == 200

            # Zeitstempel kuenstlich altern lassen, statt 60 Sekunden zu warten.
            timestamp, payload = metrics_module._metrics_cache
            metrics_module._metrics_cache = (
                timestamp - metrics_module._METRICS_CACHE_TTL_SECONDS - 1,
                payload,
            )

            assert client.get("/api/v1/metrics/getMetrics").status_code == 200
            assert repository.count.await_count == 2

    def test_cached_response_matches_fresh_response(self, client):
        first = client.get("/api/v1/metrics/getMetrics").json()
        second = client.get("/api/v1/metrics/getMetrics").json()

        assert first == second


class TestGetMetricsCacheConcurrency:
    """
    Laeuft der Cache ab, waehrend viele Requests gleichzeitig anliegen, darf nur
    einer zaehlen -- sonst erzeugt genau der Moment die Spitze, die der Cache
    verhindern soll.
    """

    @pytest.mark.asyncio
    async def test_concurrent_requests_count_once(self):
        metrics_module._metrics_cache = None

        statement_service = Mock()
        statement_service.count_curated = AsyncMock(return_value=1)
        commentary_service = Mock()
        commentary_service.count = AsyncMock(return_value=2)
        reference_service = Mock()
        reference_service.count = AsyncMock(return_value=3)

        repository = Mock()

        async def slow_count():
            await asyncio.sleep(0.05)
            return 7

        repository.count = AsyncMock(side_effect=slow_count)

        with patch.object(metrics_module, "QdrantRepositoryFactory") as factory:
            factory.return_value.create_content_repository.return_value = repository

            results = await asyncio.gather(
                *[
                    metrics_module.get_metrics(
                        statement_service=statement_service,
                        commentary_service=commentary_service,
                        reference_service=reference_service,
                        settings=Mock(),
                    )
                    for _ in range(10)
                ]
            )

        assert repository.count.await_count == 1
        assert all(r.content_count == 7 for r in results)

        metrics_module._metrics_cache = None
