"""
GET /metrics nach einer echten Suche: keine Personendaten in den Betriebskennzahlen (#420).

Eine angemeldete Testperson sucht mit einem Merkmal im Suchtext, das sonst nirgends
vorkommt; Kennung, Anzeigename und Sitzungskennung gehen in den Kopfzeilen mit, so wie
das BFF sie setzt. Danach ruft sie einen Pfad mit ihrer Kennung darin auf, den es nicht
gibt. In /metrics darf keiner dieser Werte stehen, und jeder Label-Wert der Route muss
eine registrierte Routen-Vorlage sein, kein Pfad mit ID.

Die Suche laeuft durch den echten Router mit echten Diensten, hinter dem Rate-Limit wie
in main.py. Ersetzt sind der Suchindex (``TestEmbeddingsManager``) und was PostgreSQL
braucht (Nutzung, Suchereignis): Was in /metrics landet, haengt an Router und
Middleware, nicht an Qdrant. Bis #459 lief der Test gegen echtes Qdrant.
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

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

MERKMAL = "Merkmal420xq"
KENNUNG = "testperson-kennung-420"
ANZEIGENAME = "Testperson Vierhundertzwanzig"
SITZUNG = "sitzung-420-a1b2c3"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


@pytest_asyncio.fixture
async def dienst(test_settings, repository_factory):
    """Suchdienst-App mit Betriebskennzahlen und Suche auf echten Diensten."""
    factory = repository_factory
    statements = StatementService(test_settings, factory)
    commentaries = CommentaryService(test_settings, factory)
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
                test_settings, factory
            ),
            get_post_service: lambda: create_content_service(
                REGISTRY[ContentType.POST], test_settings, factory
            ),
            get_image_service: lambda: create_content_service(
                REGISTRY[ContentType.IMAGE], test_settings, factory
            ),
            get_reference_service: lambda: ReferenceService(test_settings, factory),
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


async def test_metrics_nach_suche_ohne_merkmal_kennung_und_sitzung(dienst):
    app, client = dienst
    kopf = {
        "X-User": KENNUNG,
        "X-User-Display-Name": ANZEIGENAME,
        "X-Session-Id": SITZUNG,
    }

    suche = await client.post(
        SUCHE_VORLAGE,
        json={"query_text": f"Lohnt sich die Wärmepumpe im Altbau {MERKMAL}?"},
        headers=kopf,
    )
    assert suche.status_code == 200, suche.text
    fehlt = await client.get(f"/api/v1/nutzer/{KENNUNG}/{uuid.uuid4()}", headers=kopf)
    assert fehlt.status_code == 404

    text = (await client.get("/metrics")).text

    for wert in (MERKMAL, KENNUNG, ANZEIGENAME, SITZUNG, "Wärmepumpe"):
        assert wert not in text
    assert not UUID.search(text)

    vorlagen = {route.path for route in app.routes} | {"unmatched"}
    routen = re.findall(r'route="([^"]*)"', text)
    assert SUCHE_VORLAGE in routen
    assert "unmatched" in routen
    assert set(routen) <= vorlagen
    # Ausser method, route und status (Zaehler) und le (Histogramm) gibt es kein Label.
    assert set(re.findall(r'[{,](\w+)="', text)) == {"method", "route", "status", "le"}
    assert "gutgesagt_search_duration_seconds_count 1.0" in text
