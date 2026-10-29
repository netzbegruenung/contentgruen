"""
"Hier fehlt eine Antwort" gegen echtes Qdrant: welche Aussagen als ohne Kommentar
gelten und was das Anlegen einer Aussage vorab mit einer vorhandenen macht. Den
Filter auf die Herkunft und den Zustand der verknuepften Kommentare wertet erst
Qdrant selbst aus.
"""

import uuid

import pytest

from domain.models.commentary import Commentary
from domain.models.content_origin import ContentOrigin, SEARCH_QUERY_AUTHOR
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from domain.models.statement import Statement
from services.content.commentary_service import CommentaryService
from services.content.statement_service import StatementService

from tests.integration.conftest import requires_qdrant

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]


@pytest.fixture
def statement_service(integration_settings, real_repository_factory):
    return StatementService(
        integration_settings, repository_factory=real_repository_factory
    )


@pytest.fixture
def commentary_service(integration_settings, real_repository_factory):
    return CommentaryService(
        integration_settings, repository_factory=real_repository_factory
    )


@pytest.fixture
def status_setzen(integration_settings, real_repository_factory):
    """Den Zustand eines Beitrags oder einer Aussage aendern, wie Admin oder Autor."""
    repository = real_repository_factory.create_content_repository(integration_settings)

    async def setzen(item_id, status):
        await repository.update_status(item_id, status)

    return setzen


async def _anlegen(service, text, author="person-1", origin=None):
    _, statement_id, _ = await service.add_statement(
        Statement(text=text, replysuggestions=[]),
        author,
        ContentStatus.VISIBLE,
        origin or ContentOrigin.MANUALLY_CREATED,
    )
    return statement_id


async def _verknuepfen(service, statement_id, beitrag_id, content_type):
    await service.add_statementreplysuggestion_to_statement(
        statement_id=statement_id,
        replysuggestion_id=beitrag_id,
        content_type=content_type,
        relevance=1.0,
    )


async def _kommentar(commentary_service, text):
    _, kommentar_id, _ = await commentary_service.add_commentary(
        Commentary(
            text=text,
            title=text[:60],
            content_type=ContentType.COMMENTARY,
            references=[],
        ),
        "person-2",
        ContentStatus.VISIBLE,
        ContentOrigin.MANUALLY_CREATED,
    )
    return kommentar_id


async def _ohne_kommentar(statement_service):
    return {a.id for a in await statement_service.ohne_kommentar()}


async def test_ohne_kommentar_zeigt_nur_aussagen_ohne_kommentar(
    statement_service, commentary_service
):
    leer = await _anlegen(
        statement_service, "Solaranlagen auf Äckern zerstören die Landwirtschaft"
    )
    nur_hintergrund = await _anlegen(
        statement_service, "Fahrradwege nehmen den Autos den Platz weg"
    )
    await _verknuepfen(
        statement_service, nur_hintergrund, uuid.uuid4(), ContentType.GENERIC_TEXT
    )
    beantwortet = await _anlegen(
        statement_service, "Bürgergeld lohnt sich mehr als Arbeit"
    )
    kommentar = await _kommentar(
        commentary_service,
        "Wer arbeitet, hat mit Wohngeld und Kinderzuschlag immer mehr als im "
        "Bürgergeld. Das rechnen Sozialverbände jedes Jahr nach.",
    )
    await _verknuepfen(
        statement_service, beantwortet, kommentar, ContentType.COMMENTARY
    )

    ids = await _ohne_kommentar(statement_service)

    assert leer in ids
    assert nur_hintergrund in ids
    assert beantwortet not in ids


async def test_gesperrter_oder_geloeschter_kommentar_ist_keine_antwort(
    statement_service, commentary_service, status_setzen
):
    gesperrt = await _anlegen(statement_service, "Der Kohleausstieg kommt viel zu früh")
    kommentar = await _kommentar(
        commentary_service,
        "Der Kohleausstieg ist seit Jahren geplant, die Regionen bekommen dafür "
        "Milliarden für den Strukturwandel.",
    )
    await _verknuepfen(statement_service, gesperrt, kommentar, ContentType.COMMENTARY)
    await status_setzen(kommentar, ContentStatus.BLOCKED)

    geloescht = await _anlegen(
        statement_service, "Windkraft im Wald zerstört die Natur"
    )
    zweiter = await _kommentar(
        commentary_service,
        "Windräder im Wald stehen fast immer in Fichten-Monokulturen, die der "
        "Borkenkäfer ohnehin schon geschädigt hat.",
    )
    await _verknuepfen(statement_service, geloescht, zweiter, ContentType.COMMENTARY)
    await status_setzen(zweiter, ContentStatus.DELETED)

    ids = await _ohne_kommentar(statement_service)

    assert gesperrt in ids
    assert geloescht in ids


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
    await _verknuepfen(
        statement_service, angenommen, uuid.uuid4(), ContentType.GENERIC_TEXT
    )

    ids = await _ohne_kommentar(statement_service)

    assert suchanfrage not in ids
    assert angenommen in ids


async def test_ohne_kommentar_laesst_gesperrte_aussagen_weg(
    statement_service, status_setzen
):
    gesperrt = await _anlegen(
        statement_service, "Veganes Essen in Kantinen ist Bevormundung"
    )
    await status_setzen(gesperrt, ContentStatus.BLOCKED)

    assert gesperrt not in await _ohne_kommentar(statement_service)


async def test_vorab_uebernimmt_gleiche_unbeantwortete_suchanfrage(
    statement_service,
):
    suchanfrage = await _anlegen(
        statement_service,
        "Die Grundsteuer steigt wegen der Grünen",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )

    neu, statement_id, _ = await statement_service.vorab_anlegen(
        "Die Grundsteuer steigt wegen der Grünen", "person-1"
    )

    assert not neu
    assert statement_id == suchanfrage
    aussage = await statement_service.get(suchanfrage)
    assert aussage.origin is ContentOrigin.MANUALLY_CREATED
    assert aussage.original_author == "person-1"
    assert suchanfrage in await _ohne_kommentar(statement_service)


async def test_vorab_laesst_vorhandene_aussage_einer_person_unveraendert(
    statement_service,
):
    vorhanden = await _anlegen(
        statement_service, "Das Verbrenner-Aus kostet Arbeitsplätze", "person-2"
    )

    neu, statement_id, _ = await statement_service.vorab_anlegen(
        "Das Verbrenner-Aus kostet Arbeitsplätze", "person-1"
    )

    assert not neu
    assert statement_id == vorhanden
    assert (await statement_service.get(vorhanden)).original_author == "person-2"
