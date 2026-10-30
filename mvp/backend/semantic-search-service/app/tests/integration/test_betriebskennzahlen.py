"""
GET /metrics nach einer echten Suche: keine Personendaten in den Betriebskennzahlen (#420).

Eine angemeldete Testperson sucht mit einem Merkmal im Suchtext, das sonst nirgends
vorkommt; Kennung, Anzeigename, Adresse (X-Real-IP) und User-Agent gehen in den
Kopfzeilen mit, so wie nginx und das BFF sie setzen. Dieselbe Suche laeuft danach noch
einmal als Besucher, dessen Tagespseudonym aus Adresse und User-Agent entsteht (#446).
Zuletzt ruft die Testperson einen Pfad mit ihrer Kennung darin auf, den es nicht gibt.
In /metrics darf keiner dieser Werte stehen, und jeder Label-Wert der Route muss
eine registrierte Routen-Vorlage sein, kein Pfad mit ID.

Die Suche laeuft durch den echten Router mit echten Diensten auf einer
Wegwerf-Collection, hinter dem Rate-Limit wie in main.py; ersetzt ist nur, was
PostgreSQL braucht (Nutzung, Suchereignis).
"""

import datetime
import re
import uuid
from unittest.mock import MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from api.betriebskennzahlen import SUCHE_VORLAGE, einbinden
from api.v1.search import router as search_router
from dependencies import (
    get_commentary_service,
    get_generic_text_service,
    get_image_service,
    get_post_service,
    get_reference_service,
    get_statement_service,
    get_voting_service,
)
from domain.content_registry import REGISTRY, create_content_service
from domain.models.commentary import CommentaryDbEntry
from domain.models.content_origin import ContentOrigin
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from middleware.rate_limit import RateLimitMiddleware
from services.content.commentary_service import CommentaryService
from services.content.generic_text_service import GenericTextService
from services.content.reference_service import ReferenceService
from services.content.statement_service import StatementService

from tests.integration.conftest import requires_qdrant

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]

MERKMAL = "Merkmal420xq"
KENNUNG = "testperson-kennung-420"
ANZEIGENAME = "Testperson Vierhundertzwanzig"
ADRESSE = "198.51.100.42"
BROWSER = "Testbrowser-420/1.0"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


@pytest_asyncio.fixture
async def dienst(integration_settings, real_repository_factory):
    """Suchdienst-App mit Betriebskennzahlen und Suche auf echten Diensten."""
    factory = real_repository_factory
    statements = StatementService(integration_settings, factory)
    commentaries = CommentaryService(integration_settings, factory)
    now = datetime.datetime.now()
    await commentaries.add(
        CommentaryDbEntry(
            text="Mit Förderung rechnet sich die Wärmepumpe auch in alten Häusern.",
            title="Wärmepumpe lohnt sich auch im Altbau",
            references=[],
            references_count=0,
            id=uuid.uuid4(),
            created=now,
            last_modified=now,
            original_author=KENNUNG,
            last_modified_by=KENNUNG,
            status=ContentStatus.VISIBLE,
            origin=ContentOrigin.MANUALLY_CREATED,
        )
    )

    # Dieselbe Schichtung wie in main.py: das Rate-Limit ist eine BaseHTTPMiddleware
    # innen, die Betriebskennzahlen liegen aussen und lesen die Route danach aus dem Scope.
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)
    einbinden(app)
    app.include_router(search_router, prefix="/api/v1/search")
    app.dependency_overrides.update(
        {
            get_statement_service: lambda: statements,
            get_commentary_service: lambda: commentaries,
            get_generic_text_service: lambda: GenericTextService(
                integration_settings, factory
            ),
            get_post_service: lambda: create_content_service(
                REGISTRY[ContentType.POST], integration_settings, factory
            ),
            get_image_service: lambda: create_content_service(
                REGISTRY[ContentType.IMAGE], integration_settings, factory
            ),
            get_reference_service: lambda: ReferenceService(
                integration_settings, factory
            ),
            get_voting_service: lambda: MagicMock(),
        }
    )

    usage = MagicMock()
    usage.enrich_content_with_usage.side_effect = lambda dicts: dicts
    with (
        patch("api.v1.search.get_usage_service", return_value=usage),
        patch("api.v1.search.get_search_tracking_service", return_value=MagicMock()),
    ):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            yield app, client


async def test_metrics_nach_suche_ohne_merkmal_kennung_adresse_und_browser(dienst):
    app, client = dienst
    besucher = {"X-Real-IP": ADRESSE, "User-Agent": BROWSER}
    kopf = {"X-User": KENNUNG, "X-User-Display-Name": ANZEIGENAME, **besucher}

    for headers in (kopf, besucher):
        suche = await client.post(
            SUCHE_VORLAGE,
            json={"query_text": f"Lohnt sich die Wärmepumpe im Altbau {MERKMAL}?"},
            headers=headers,
        )
        assert suche.status_code == 200, suche.text
    fehlt = await client.get(f"/api/v1/nutzer/{KENNUNG}/{uuid.uuid4()}", headers=kopf)
    assert fehlt.status_code == 404

    text = (await client.get("/metrics")).text

    for wert in (MERKMAL, KENNUNG, ANZEIGENAME, ADRESSE, BROWSER, "Wärmepumpe"):
        assert wert not in text
    assert not UUID.search(text)

    vorlagen = {route.path for route in app.routes} | {"unmatched"}
    routen = re.findall(r'route="([^"]*)"', text)
    assert SUCHE_VORLAGE in routen
    assert "unmatched" in routen
    assert set(routen) <= vorlagen
    # Ausser method, route und status (Zaehler) und le (Histogramm) gibt es kein Label.
    assert set(re.findall(r'[{,](\w+)="', text)) == {"method", "route", "status", "le"}
    assert "gutgesagt_search_duration_seconds_count 2.0" in text
