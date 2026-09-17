"""
Antwort auf eine Aussage, gegen echtes Qdrant: die kuratierte Aussagensuche
(Vorschlaege im Beitragsformular) und das Verknuepfen ohne Dubletten.

Der Unit-Test prueft nur, welchen Filter das Repository baut; ob Qdrant den
verschachtelten must_not-Filter so auswertet, zeigt erst dieser Test.
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


async def _anlegen(service, text, author, origin):
    _, statement_id, _ = await service.add_statement(
        Statement(text=text, replysuggestions=[]),
        author,
        ContentStatus.RELEASED_INTERNAL,
        origin,
    )
    return statement_id


async def test_kuratierte_suche_laesst_unbeantwortete_suchanfragen_weg(
    statement_service,
):
    suchanfrage = await _anlegen(
        statement_service,
        "Wärmepumpen sind im Altbau zu teuer",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )
    kuratiert = await _anlegen(
        statement_service,
        "Die Grünen wollen uns das Autofahren verbieten",
        "person-1",
        ContentOrigin.MANUALLY_CREATED,
    )

    alle = await statement_service.search_filtered("Wärmepumpe Altbau teuer", 10)
    nur_kuratiert = await statement_service.search_filtered(
        "Wärmepumpe Altbau teuer", 10, nur_kuratiert=True
    )

    assert suchanfrage in {r.id for r in alle}
    assert {r.id for r in nur_kuratiert} == {kuratiert}


async def test_beantwortete_suchanfrage_gilt_als_kuratiert(statement_service):
    suchanfrage = await _anlegen(
        statement_service,
        "Windräder machen Vögel kaputt",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )

    await statement_service.beitrag_als_antwort_verknuepfen(
        uuid.uuid4(), ContentType.COMMENTARY, 1.0, "person-1", suchanfrage
    )

    treffer = await statement_service.search_filtered(
        "Windräder Vögel", 10, nur_kuratiert=True
    )
    assert suchanfrage in {r.id for r in treffer}


async def test_verknuepfen_per_text_und_ohne_dublette(statement_service):
    beitrag_id = uuid.uuid4()

    erste = await statement_service.beitrag_als_antwort_verknuepfen(
        beitrag_id,
        ContentType.COMMENTARY,
        1.0,
        "person-1",
        statement_text="Klimaschutz zerstört Arbeitsplätze",
    )
    zweite = await statement_service.beitrag_als_antwort_verknuepfen(
        beitrag_id,
        ContentType.COMMENTARY,
        1.0,
        "person-1",
        statement_text="Klimaschutz zerstört Arbeitsplätze",
    )

    assert erste == zweite
    aussage = await statement_service.get(erste)
    assert [r.id for r in aussage.replysuggestions] == [beitrag_id]
    assert aussage.replysuggestions_count == 1
    assert aussage.origin is ContentOrigin.MANUALLY_CREATED
    assert aussage.original_author == "person-1"


async def test_unbekannte_aussage_wirft(statement_service):
    with pytest.raises(ValueError):
        await statement_service.beitrag_als_antwort_verknuepfen(
            uuid.uuid4(), ContentType.COMMENTARY, 1.0, "person-1", uuid.uuid4()
        )
