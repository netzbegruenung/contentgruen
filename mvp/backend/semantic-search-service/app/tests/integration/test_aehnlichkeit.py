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
from services.content.reference_service import ReferenceService
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
                "„Wärmepumpen funktionieren nur im Neubau!“",
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

    async def dublette(text):
        return (await commentary_service.pruefe_dublette(text)).vorhanden

    # A: wortgleich (q/p erreichte nur 0,96 - die alte Pruefung griff nie)
    assert (await dublette(KATZEN)).id == katzen
    # B: nur klein geschrieben
    assert (await dublette(KATZEN.lower())).id == katzen
    # C: Kopie mit Quellenzusatz (p/p 0,997)
    assert (await dublette(KATZEN + " Quelle: NABU-Studie 2023.")).id == katzen
    # C: eigene Umformulierung (p/p 0,968) und D: anderer Kommentar zur selben Aussage
    assert (
        await dublette(
            "Ich mag Vögel auch. Aber Hauskatzen töten jedes Jahr rund 100 Millionen "
            "Vögel, Windräder weniger als 100.000. Selbst der NABU unterstützt "
            "Windkraft, wenn sie gut geplant ist."
        )
        is None
    )
    assert await dublette(DORF) is None


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


async def test_normalisiert_gleich_ohne_gesperrte_freigegebene_zuerst_dann_aelteste(
    statement_service, real_embeddings_manager
):
    """Mehrere normalisiert gleiche Aussagen (Altbestand): deterministische Wahl."""
    import datetime
    from domain.models.author_entry import AuthorEntry
    from domain.models.statement import StatementDbEntry

    repository = statement_service._repository
    basis = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)

    async def punkt(text, tage, status):
        eintrag = StatementDbEntry(
            text=text,
            id=uuid.uuid4(),
            created=basis + datetime.timedelta(days=tage),
            last_modified=basis,
            original_author="alt",
            last_modified_by="alt",
            authors=[AuthorEntry(name="alt")],
            edit_history=[],
            status=status,
            origin=ContentOrigin.MANUALLY_CREATED,
            replysuggestions=[],
            replysuggestions_count=0,
        )
        await repository.upsert(eintrag.id, eintrag)
        return eintrag.id

    normalform = "windräder sind vogel-schredder"
    gesperrt = await punkt("Windräder sind Vogel-Schredder!", 0, ContentStatus.BLOCKED)
    archiviert = await punkt(
        "windräder sind Vogel-Schredder", 1, ContentStatus.ARCHIVED
    )
    entwurf = await punkt("Windräder sind Vogel-Schredder.", 2, ContentStatus.DRAFT)
    freigegeben_neu = await punkt(
        "WINDRÄDER SIND VOGEL-SCHREDDER", 4, ContentStatus.RELEASED_INTERNAL
    )
    freigegeben_alt = await punkt(
        "Windräder sind Vogel-Schredder!!", 3, ContentStatus.RELEASED_INTERNAL
    )

    treffer = await repository.finde_normalisiert_gleich(normalform)
    assert treffer.id == freigegeben_alt

    for status_aendern in (freigegeben_alt, freigegeben_neu):
        await repository.update_status(status_aendern, ContentStatus.BLOCKED)
    # Nur noch der Entwurf ist wiederverwendbar - gesperrt und archiviert nie.
    assert (await repository.finde_normalisiert_gleich(normalform)).id == entwurf
    await repository.update_status(entwurf, ContentStatus.DUPLICATE)
    assert await repository.finde_normalisiert_gleich(normalform) is None
    assert gesperrt and archiviert

    # Auch add_statement legt dann neu an statt eine gesperrte wiederzuverwenden.
    neu, _, _ = await _aussage(statement_service, "Windräder sind Vogel-Schredder!")
    assert neu is True


async def test_parallele_gleiche_kommentare_ueber_den_router(
    integration_settings, real_repository_factory, statement_service, commentary_service
):
    """Zwei gleichzeitige gleiche Kommentare: ein Kommentar, eine Referenz."""
    import httpx
    from fastapi import FastAPI
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    from api.v1.commentary import router
    from dependencies import (
        get_commentary_service,
        get_reference_service,
        get_statement_service,
    )

    reference_service = ReferenceService(
        integration_settings, repository_factory=real_repository_factory
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/commentary")
    app.dependency_overrides[get_commentary_service] = lambda: commentary_service
    app.dependency_overrides[get_reference_service] = lambda: reference_service
    app.dependency_overrides[get_statement_service] = lambda: statement_service

    anfrage = {
        "commentary": {
            "title": "Katzen gefaehrden Voegel mehr als Windraeder",
            "text": KATZEN,
            "content_type": "commentary",
            "references": [],
        },
        "references": [
            {
                "reference_string": "https://www.nabu.de/natur-und-landschaft/katzen",
                "description": "NABU zu Hauskatzen",
            }
        ],
        "statement_text": "Windräder sind Vogel-Schredder!",
    }
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        antworten = await asyncio.gather(
            *(
                client.post(
                    "/api/v1/commentary/addCommentary",
                    json=anfrage,
                    headers={"X-User": person},
                )
                for person in ("person-1", "person-2")
            )
        )

    daten = [a.json() for a in antworten]
    assert all(a.status_code == 200 for a in antworten), daten
    assert sorted(d["duplikat"] for d in daten) == [False, True]
    assert daten[0]["id"] == daten[1]["id"]
    angelegt = next(d for d in daten if not d["duplikat"])
    dublette = next(d for d in daten if d["duplikat"])
    # Die zweite Person bekommt den Kommentar der ersten - fremder Inhalt wird nicht
    # an ihre Aussage gehaengt.
    assert angelegt["statement_id"] is not None
    assert dublette["statement_id"] is None

    manager = commentary_service._repository._shared_manager

    def anzahl(typ):
        return manager.client.count(
            manager.collection_name,
            count_filter=Filter(
                must=[FieldCondition(key="content_type", match=MatchValue(value=typ))]
            ),
        ).count

    assert anzahl("commentary") == 1
    assert anzahl("reference") == 1
    aussage = await statement_service.get(uuid.UUID(angelegt["statement_id"]))
    assert [r.id for r in aussage.replysuggestions] == [uuid.UUID(angelegt["id"])]


async def test_dublette_mit_anderer_aussage_wird_dort_verknuepft(
    statement_service, commentary_service
):
    """Die Verknuepfung selbst: der vorhandene Kommentar haengt an beiden Aussagen."""
    _, kommentar, _ = await commentary_service.add_commentary(
        _kommentar(KATZEN),
        "person-1",
        ContentStatus.RELEASED_INTERNAL,
        ContentOrigin.MANUALLY_CREATED,
    )
    for text in ("Windräder sind Vogel-Schredder!", "Windkraft tötet unsere Vögel"):
        await statement_service.beitrag_als_antwort_verknuepfen(
            kommentar, ContentType.COMMENTARY, 1.0, "person-2", statement_text=text
        )
    # zweimal dieselbe Aussage: die Verknuepfung erkennt es
    statement_id, _ = await statement_service.beitrag_als_antwort_verknuepfen(
        kommentar,
        ContentType.COMMENTARY,
        1.0,
        "person-2",
        statement_text="Windkraft tötet unsere Vögel",
    )
    aussage = await statement_service.get(statement_id)
    assert [r.id for r in aussage.replysuggestions] == [kommentar]
