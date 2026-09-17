"""
Dublettenpruefung gegen echtes Qdrant und das echte Einbettungsmodell.

Die Unit-Tests pruefen die Entscheidungslogik mit festen Scores; ob Keyword-Index,
Normalform im Payload, Praefix der Einbettung und die Schwellen zusammen das
Richtige tun, zeigt erst dieser Test. Die Texte stammen aus dem Messset
(tests/regression/aehnlichkeit_paare.py).
"""

import asyncio
import uuid
from unittest.mock import MagicMock

import pytest

from domain.models.commentary import Commentary
from domain.models.content_origin import ContentOrigin, SEARCH_QUERY_AUTHOR
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from domain.models.statement import Statement
from services.content.commentary_service import CommentaryService
from services.content.statement_service import StatementService
from services.orchestration.content_orchestrator import DataProcessor
from services.wartung.text_normalisiert_nachtrag import nachtragen
from tests.integration.conftest import requires_qdrant
from tests.regression.aehnlichkeit_paare import DORF, KATZEN
from utils.text_normalisierung import FELD_TEXT_NORMALISIERT

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


async def _aussage(service, text, author="person-1", origin=None):
    return await service.add_statement(
        Statement(text=text, replysuggestions=[]),
        author,
        ContentStatus.RELEASED_INTERNAL,
        origin or ContentOrigin.MANUALLY_CREATED,
    )


def _kommentar(text):
    return Commentary(
        text=text,
        title="Katzen gefaehrden Voegel mehr als Windraeder",
        content_type=ContentType.COMMENTARY,
        references=[],
    )


def _payload(manager, punkt_id):
    punkte = manager.client.retrieve(
        manager.collection_name, [str(punkt_id)], with_payload=True
    )
    return punkte[0].payload


async def test_keyword_index_wird_angelegt(real_embeddings_manager):
    info = real_embeddings_manager.client.get_collection(
        real_embeddings_manager.collection_name
    )
    assert FELD_TEXT_NORMALISIERT in info.payload_schema


async def test_gleiche_aussage_wird_wiederverwendet_andere_behauptung_nicht(
    statement_service, real_embeddings_manager
):
    neu, verbot, _ = await _aussage(
        statement_service, "Die Grünen sind eine Verbotspartei!"
    )
    assert neu
    assert (
        _payload(real_embeddings_manager, verbot)[FELD_TEXT_NORMALISIERT]
        == "die grünen sind eine verbotspartei"
    )

    # B: trivial abweichend - normalisiert gleich
    assert await _aussage(
        statement_service, "  die grünen sind eine VERBOTSPARTEI"
    ) == (
        False,
        verbot,
        "Die Grünen sind eine Verbotspartei!",
    )
    # D: Verneinung (q/q 0,969) und verwandte Behauptung (0,906) - eigene Aussagen
    for text in ("Die Grünen sind keine Verbotspartei", "Grüne sind Kriegstreiber"):
        neu, andere, _ = await _aussage(statement_service, text)
        assert neu, text
        assert andere != verbot


async def test_suchanfrage_folgt_derselben_regel(statement_service):
    _, klima, _ = await _aussage(
        statement_service,
        "Klimaschutz",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )

    wieder = await _aussage(
        statement_service,
        "klimaschutz",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )
    verwandt = await _aussage(
        statement_service,
        "Klimaschutz Kosten",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )

    assert wieder[:2] == (False, klima)
    assert verwandt[0] is True


async def test_altbestand_ohne_feld_ueber_vektortreffer_und_nachtrag(
    statement_service, real_embeddings_manager
):
    manager = real_embeddings_manager
    _, totgeburt, _ = await _aussage(statement_service, "E-Autos sind eine Totgeburt!")
    await _aussage(statement_service, "E-Autos sind auch nicht besser für die Umwelt")
    await statement_service.beitrag_als_antwort_verknuepfen(
        uuid.uuid4(), ContentType.COMMENTARY, 1.0, "person-1", totgeburt
    )
    # Altbestand nachstellen: Punkt ohne Normalform
    manager.client.delete_payload(
        manager.collection_name, [FELD_TEXT_NORMALISIERT], points=[str(totgeburt)]
    )

    # Grossschreibung: q/q nur 0,902 - gefunden unter den Vektortreffern
    neu, gefunden, _ = await _aussage(
        statement_service, "E-AUTOS SIND EINE TOTGEBURT!!!"
    )
    assert (neu, gefunden) == (False, totgeburt)

    trocken = nachtragen(manager.client, manager.collection_name)
    assert trocken.nachzutragen == {"statement": 1}
    assert FELD_TEXT_NORMALISIERT not in _payload(manager, totgeburt)

    erster = nachtragen(manager.client, manager.collection_name, ausfuehren=True)
    zweiter = nachtragen(manager.client, manager.collection_name, ausfuehren=True)

    assert erster.nachgetragen == {"statement": 1}
    assert zweiter.nachzutragen == {}
    payload = _payload(manager, totgeburt)
    assert payload[FELD_TEXT_NORMALISIERT] == "e-autos sind eine totgeburt"
    assert payload["replysuggestions_count"] == 1  # set_payload laesst den Rest stehen


async def test_parallel_derselbe_neue_text_ergibt_eine_aussage(statement_service):
    ergebnisse = await asyncio.gather(
        *(
            _aussage(statement_service, text)
            for text in (
                "Wärmepumpen funktionieren nur im Neubau!",
                "wärmepumpen funktionieren nur im neubau",
                "Wärmepumpen funktionieren nur im Neubau?",
            )
        )
    )

    assert sorted(neu for neu, _, _ in ergebnisse) == [False, False, True]
    assert len({statement_id for _, statement_id, _ in ergebnisse}) == 1


async def test_kommentar_dublette_mit_passage_einbettung(commentary_service):
    neu, katzen, _ = await commentary_service.add_commentary(
        _kommentar(KATZEN),
        "person-1",
        ContentStatus.RELEASED_INTERNAL,
        ContentOrigin.MANUALLY_CREATED,
    )
    assert neu

    # A: wortgleich (q/p erreichte nur 0,96 - die alte Pruefung griff nie)
    assert (await commentary_service.finde_dublette(KATZEN)).id == katzen
    # B: nur klein geschrieben
    assert (await commentary_service.finde_dublette(KATZEN.lower())).id == katzen
    # C: Kopie mit Quellenzusatz (p/p 0,997)
    assert (
        await commentary_service.finde_dublette(KATZEN + " Quelle: NABU-Studie 2023.")
    ).id == katzen
    # C: eigene Umformulierung (p/p 0,968) und D: anderer Kommentar zur selben Aussage
    assert (
        await commentary_service.finde_dublette(
            "Ich mag Vögel auch. Aber Hauskatzen töten jedes Jahr rund 100 Millionen "
            "Vögel, Windräder weniger als 100.000. Selbst der NABU unterstützt "
            "Windkraft, wenn sie gut geplant ist."
        )
        is None
    )
    assert await commentary_service.finde_dublette(DORF) is None


async def test_seeding_haengt_antworten_an_die_vorhandene_aussage(statement_service):
    orchestrator = MagicMock()
    orchestrator.statement_service = statement_service
    orchestrator.initial_data_author = "integration_test"
    verarbeitung = DataProcessor(orchestrator)
    erste, zweite = uuid.uuid4(), uuid.uuid4()

    await verarbeitung.create_statement_with_replies(
        "Die Grünen sind eine Verbotspartei", [erste], ContentType.COMMENTARY
    )
    await verarbeitung.create_statement_with_replies(
        "Die Grünen sind eine Verbotspartei!", [zweite], ContentType.COMMENTARY
    )

    treffer = await statement_service.search("Die Grünen sind eine Verbotspartei", 5)
    aussagen = [t for t in treffer if t.text.startswith("Die Grünen sind eine Verbot")]
    assert len(aussagen) == 1
    assert {r.id for r in aussagen[0].replysuggestions} == {erste, zweite}
