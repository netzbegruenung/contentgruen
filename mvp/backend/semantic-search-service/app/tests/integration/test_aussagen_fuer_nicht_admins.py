"""
Aussagen fuer Nicht-Admins gegen echtes Qdrant (#436): kuratierte Aussagen und
Suchanfragen ueber der Schwelle, nie die unbeantwortete Suchanfrage einer
einzelnen Person. Den verschachtelten Filter (Herkunft, Zahl der
Antwortvorschlaege, ausgenommene IDs) wertet erst Qdrant selbst aus.
"""

import uuid

import pytest
import pytest_asyncio

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


async def _anlegen(service, text, origin=ContentOrigin.MANUALLY_CREATED):
    author = SEARCH_QUERY_AUTHOR if origin is ContentOrigin.SEARCH_QUERY else "p-1"
    _, statement_id, _ = await service.add_statement(
        Statement(text=text, replysuggestions=[]),
        author,
        ContentStatus.VISIBLE,
        origin,
    )
    return statement_id


@pytest_asyncio.fixture
async def bestand(statement_service):
    """
    Je eine Aussage einer Person, eine beantwortete Aussage aus einer
    Suchanfrage, eine aus der Suchanfrage einer einzelnen Person und eine aus
    einer Suchanfrage ueber der Schwelle (gefragt).
    """
    von_person = await _anlegen(
        statement_service, "Windräder vertreiben die Touristen von der Küste"
    )
    beantwortet = await _anlegen(
        statement_service,
        "Tempolimit bringt für das Klima gar nichts",
        ContentOrigin.SEARCH_QUERY,
    )
    await statement_service.add_statementreplysuggestion_to_statement(
        statement_id=beantwortet,
        replysuggestion_id=uuid.uuid4(),
        content_type=ContentType.COMMENTARY,
        relevance=1.0,
    )
    einzeln = await _anlegen(
        statement_service,
        "Was kostet eine Wärmepumpe für ein Reihenhaus",
        ContentOrigin.SEARCH_QUERY,
    )
    gefragt = await _anlegen(
        statement_service,
        "Machen Elektroautos das Stromnetz kaputt",
        ContentOrigin.SEARCH_QUERY,
    )
    return von_person, beantwortet, einzeln, gefragt


async def test_liste_ohne_einzelne_suchanfrage_mit_gefragter(
    statement_service, bestand
):
    von_person, beantwortet, einzeln, gefragt = bestand

    aussagen = await statement_service.get_all_curated(
        limit=10, offset=0, ueber_der_schwelle=frozenset({gefragt})
    )

    assert {a.id for a in aussagen} == {von_person, beantwortet, gefragt}
    assert (
        await statement_service.count_curated(ueber_der_schwelle=frozenset({gefragt}))
        == 3
    )


async def test_liste_blaettert_ueber_die_gefilterten(statement_service, bestand):
    von_person, beantwortet, einzeln, gefragt = bestand
    ueber_der_schwelle = frozenset({gefragt})

    seiten = [
        await statement_service.get_all_curated(
            limit=2, offset=offset, ueber_der_schwelle=ueber_der_schwelle
        )
        for offset in (0, 2)
    ]

    assert [len(s) for s in seiten] == [2, 1]
    assert {a.id for s in seiten for a in s} == {von_person, beantwortet, gefragt}


async def test_ohne_ueber_der_schwelle_nur_kuratierte(statement_service, bestand):
    von_person, beantwortet, einzeln, gefragt = bestand

    aussagen = await statement_service.get_all_curated(limit=10, offset=0)

    assert {a.id for a in aussagen} == {von_person, beantwortet}
    assert await statement_service.count_curated() == 2


async def test_suche_ohne_einzelne_suchanfrage_mit_gefragter(
    statement_service, bestand
):
    von_person, beantwortet, einzeln, gefragt = bestand

    treffer = await statement_service.search_filtered(
        "Wärmepumpe Elektroauto Windrad Tempolimit",
        10,
        nur_kuratiert=True,
        ueber_der_schwelle=frozenset({gefragt}),
    )

    assert {t.id for t in treffer} == {von_person, beantwortet, gefragt}
