"""
"Hier fehlt eine Antwort" gegen echtes Qdrant: welche Aussagen als ohne Kommentar
gelten und was das Anlegen einer Aussage vorab mit einer vorhandenen macht. Den
Filter auf die Herkunft und den Zustand der verknuepften Kommentare wertet erst
Qdrant selbst aus.
"""

import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from domain.models.commentary import Commentary
from domain.models.content_origin import ContentOrigin, SEARCH_QUERY_AUTHOR
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from domain.models.statement import Statement
from services.content.commentary_service import CommentaryService
from services.content.statement_service import StatementService

from tests.integration.beitrag_helfer import sichtbarer_beitrag
from tests.integration.conftest import requires_qdrant

# Fuer den Weg "Hier fehlt eine Antwort" -> gespeichert (UnbeantworteteAussagenService).
from services.aussage_themen_service import AussageThemenService
from services.suchen_ohne_treffer_service import (
    SucheOhneTreffer,
    SuchenOhneTrefferService,
)
from services.unbeantwortete_aussagen_service import (
    UnbeantworteteAussagenService,
)

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
    hintergrund = await sichtbarer_beitrag(statement_service, ContentType.GENERIC_TEXT)
    await _verknuepfen(
        statement_service, angenommen, hintergrund, ContentType.GENERIC_TEXT
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


async def test_mit_kommentar_nur_mit_sichtbarem_kommentar(
    statement_service, commentary_service, status_setzen
):
    beantwortet = await _anlegen(
        statement_service, "Das Bürgergeld ist höher als der Mindestlohn"
    )
    kommentar = await _kommentar(
        commentary_service,
        "Wer Vollzeit zum Mindestlohn arbeitet, hat mit Wohngeld und "
        "Kinderzuschlag mehr im Monat als mit Bürgergeld.",
    )
    await _verknuepfen(
        statement_service, beantwortet, kommentar, ContentType.COMMENTARY
    )
    nur_hintergrund = await _anlegen(
        statement_service, "Lastenräder blockieren die Gehwege"
    )
    hintergrund = await sichtbarer_beitrag(statement_service, ContentType.GENERIC_TEXT)
    await _verknuepfen(
        statement_service, nur_hintergrund, hintergrund, ContentType.GENERIC_TEXT
    )
    gesperrt = await _anlegen(statement_service, "Biogas verdirbt die Böden")
    gesperrter = await _kommentar(
        commentary_service,
        "Gärreste aus Biogasanlagen ersetzen Mineraldünger, wenn man sie nach "
        "Bedarf ausbringt.",
    )
    await _verknuepfen(statement_service, gesperrt, gesperrter, ContentType.COMMENTARY)
    await status_setzen(gesperrter, ContentStatus.BLOCKED)
    leer = await _anlegen(statement_service, "Hitzeschutzpläne sind Panikmache")

    ids = await statement_service.mit_kommentar(
        [beantwortet, nur_hintergrund, gesperrt, leer, uuid.uuid4()]
    )

    assert ids == {beantwortet}


async def test_gesuchte_aussage_verschwindet_nach_dem_kommentar(
    statement_service, commentary_service
):
    """
    Der Weg "Hier fehlt eine Antwort" -> Antworten -> gespeichert: Die Suchanfrage,
    nach der zwei Personen ohne Treffer gesucht haben, steht auf der Liste, bis ein
    Kommentar an ihr haengt; die Suchen ohne Treffer bleiben gezaehlt.
    """
    gesucht = await _anlegen(
        statement_service,
        "Windräder im Wald vergiften das Grundwasser",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )
    suchen = Mock(spec=SuchenOhneTrefferService)
    suchen.haeufigste = AsyncMock(
        return_value=[
            SucheOhneTreffer(
                gesucht, "Windräder im Wald vergiften das Grundwasser", 3, 2
            )
        ]
    )
    themen = Mock(spec=AussageThemenService)
    themen.themen_von = Mock(return_value={})
    service = UnbeantworteteAussagenService(statement_service, suchen, themen)

    vorher = await service.liste(limit=500)
    kommentar = await _kommentar(
        commentary_service,
        "Fundamente von Windrädern reichen nicht ins Grundwasser, und jede "
        "Anlage im Wald braucht ein Gutachten zum Wasserschutz.",
    )
    await _verknuepfen(statement_service, gesucht, kommentar, ContentType.COMMENTARY)
    nachher = await service.liste(limit=500)

    assert gesucht in [a.statement_id for a in vorher]
    assert gesucht not in [a.statement_id for a in nachher]


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
