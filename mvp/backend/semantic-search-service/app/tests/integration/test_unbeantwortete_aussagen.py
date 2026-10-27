"""
"Hier fehlt eine Antwort" gegen echtes Qdrant: welche Aussagen als ohne Kommentar
gelten. Der Filter auf verschachtelte Antwortvorschlaege (replysuggestions[]) und das
must_not der unbeantworteten Suchanfragen wertet erst Qdrant selbst aus.
"""

import uuid

import pytest

from domain.models.content_origin import ContentOrigin, SEARCH_QUERY_AUTHOR
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from domain.models.statement import Statement
from services.content.statement_service import StatementService

from tests.integration.conftest import requires_qdrant

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]


@pytest.fixture
def statement_service(integration_settings, real_repository_factory):
    return StatementService(
        integration_settings, repository_factory=real_repository_factory
    )


async def _anlegen(service, text, author="person-1", origin=None):
    _, statement_id, _ = await service.add_statement(
        Statement(text=text, replysuggestions=[]),
        author,
        ContentStatus.VISIBLE,
        origin or ContentOrigin.MANUALLY_CREATED,
    )
    return statement_id


async def _antwort(service, statement_id, content_type):
    await service.add_statementreplysuggestion_to_statement(
        statement_id=statement_id,
        replysuggestion_id=uuid.uuid4(),
        content_type=content_type,
        relevance=1.0,
    )


async def test_ohne_kommentar_zeigt_nur_aussagen_ohne_kommentar(statement_service):
    leer = await _anlegen(
        statement_service, "Solaranlagen auf Äckern zerstören die Landwirtschaft"
    )
    nur_hintergrund = await _anlegen(
        statement_service, "Fahrradwege nehmen den Autos den Platz weg"
    )
    await _antwort(statement_service, nur_hintergrund, ContentType.GENERIC_TEXT)
    beantwortet = await _anlegen(
        statement_service, "Bürgergeld lohnt sich mehr als Arbeit"
    )
    await _antwort(statement_service, beantwortet, ContentType.GENERIC_TEXT)
    await _antwort(statement_service, beantwortet, ContentType.COMMENTARY)

    ids = {a.id for a in await statement_service.ohne_kommentar()}

    assert leer in ids
    assert nur_hintergrund in ids
    assert beantwortet not in ids


async def test_ohne_kommentar_laesst_unbeantwortete_suchanfragen_weg(
    statement_service,
):
    suchanfrage = await _anlegen(
        statement_service,
        "Elektroautos brennen ständig ab",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )
    angenommen = await _anlegen(
        statement_service,
        "Der Wolf gefährdet die Weidetierhaltung",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )
    await _antwort(statement_service, angenommen, ContentType.GENERIC_TEXT)

    ids = {a.id for a in await statement_service.ohne_kommentar()}

    assert suchanfrage not in ids
    assert angenommen in ids


async def test_ohne_kommentar_laesst_gesperrte_aussagen_weg(statement_service):
    gesperrt = await _anlegen(
        statement_service, "Veganes Essen in Kantinen ist Bevormundung"
    )
    await statement_service._repository.update_status(gesperrt, ContentStatus.BLOCKED)

    ids = {a.id for a in await statement_service.ohne_kommentar()}

    assert gesperrt not in ids
