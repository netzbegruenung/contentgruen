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
from services.content.statement_service import (
    AussageNichtGefunden,
    StatementService,
    SuchanfrageNichtFreigegeben,
)

from tests.integration.beitrag_helfer import sichtbarer_beitrag
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
    statement_service, sichtbare_suchanfragen
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
    # Antworten gibt es nur an freigegebenen (Vormoderation).
    _entscheidung_setzen(sichtbare_suchanfragen, angenommen, True)
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


async def test_vorab_uebernimmt_gleiche_unbeantwortete_suchanfrage(
    statement_service, sichtbare_suchanfragen
):
    suchanfrage = await _anlegen(
        statement_service,
        "Die Grundsteuer steigt wegen der Grünen",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )
    # Uebernommen wird nur eine sichtbare (Vormoderation).
    sichtbare_suchanfragen.add(suchanfrage)

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


# Vormoderation (Entscheidung des Maintainers vom 13.11.2026): Eine unbeantwortete
# Suchanfrage, die kein Admin freigegeben hat, wird ueber Schreibwege nicht sichtbar.
NICHT_FREIGEGEBEN = pytest.mark.parametrize(
    "entscheidung", [None, False], ids=["ungeprueft", "abgelehnt"]
)


def _entscheidung_setzen(freigaben, suchanfrage, entscheidung):
    # Sichtbar ist nur eine freigegebene (die Schwelle gilt im Test als erreicht).
    if entscheidung is True:
        freigaben.add(suchanfrage)


async def _bleibt_in_der_vormoderation(statement_service, suchanfrage, text):
    aussage = await statement_service.get(suchanfrage)
    assert aussage.origin is ContentOrigin.SEARCH_QUERY
    assert aussage.original_author == SEARCH_QUERY_AUTHOR
    assert aussage.replysuggestions_count == 0
    assert aussage.text == text


@NICHT_FREIGEGEBEN
async def test_vorab_legt_bei_nicht_freigegebener_suchanfrage_eine_neue_an(
    statement_service, sichtbare_suchanfragen, entscheidung
):
    gesucht = "Die Pendlerpauschale fällt wegen der Grünen weg"
    suchanfrage = await _anlegen(
        statement_service, gesucht, SEARCH_QUERY_AUTHOR, ContentOrigin.SEARCH_QUERY
    )
    _entscheidung_setzen(sichtbare_suchanfragen, suchanfrage, entscheidung)

    eigener = "die Pendlerpauschale fällt wegen der Grünen weg!"
    neu, statement_id, text = await statement_service.vorab_anlegen(eigener, "person-1")

    assert neu
    assert statement_id != suchanfrage
    assert text == eigener
    assert (await statement_service.get(statement_id)).original_author == "person-1"
    await _bleibt_in_der_vormoderation(statement_service, suchanfrage, gesucht)
    assert suchanfrage not in await _ohne_kommentar(statement_service)


@NICHT_FREIGEGEBEN
async def test_antwort_haengt_bei_nicht_freigegebener_suchanfrage_an_eine_neue(
    statement_service,
    commentary_service,
    sichtbare_suchanfragen,
    entscheidung,
):
    gesucht = "Das Heizungsgesetz verbietet Kamine"
    suchanfrage = await _anlegen(
        statement_service, gesucht, SEARCH_QUERY_AUTHOR, ContentOrigin.SEARCH_QUERY
    )
    _entscheidung_setzen(sichtbare_suchanfragen, suchanfrage, entscheidung)

    # Wie /addStatement aus dem Beitragsformular: die Aussage zum eigenen Text.
    eigener = "das Heizungsgesetz verbietet Kamine."
    neu, statement_id, text = await statement_service.add_statement(
        Statement(text=eigener, replysuggestions=[]),
        "person-1",
        ContentStatus.VISIBLE,
        ContentOrigin.MANUALLY_CREATED,
    )
    kommentar = await _kommentar(commentary_service, "Kamine bleiben erlaubt.")
    await _verknuepfen(
        statement_service, statement_id, kommentar, ContentType.COMMENTARY
    )

    assert neu
    assert statement_id != suchanfrage
    assert text == eigener
    await _bleibt_in_der_vormoderation(statement_service, suchanfrage, gesucht)


async def test_antwort_landet_bei_freigegebener_suchanfrage_wie_bisher(
    statement_service, sichtbare_suchanfragen
):
    gesucht = "Windräder machen krank"
    suchanfrage = await _anlegen(
        statement_service, gesucht, SEARCH_QUERY_AUTHOR, ContentOrigin.SEARCH_QUERY
    )
    _entscheidung_setzen(sichtbare_suchanfragen, suchanfrage, True)

    neu, statement_id, text = await statement_service.add_statement(
        Statement(text="windräder machen krank", replysuggestions=[]),
        "person-1",
        ContentStatus.VISIBLE,
        ContentOrigin.MANUALLY_CREATED,
    )

    assert not neu
    assert statement_id == suchanfrage
    assert text == gesucht


async def test_eine_suche_landet_weiter_auf_der_nicht_freigegebenen_suchanfrage(
    statement_service, suchen_ohne_treffer_ohne_datenbank
):
    # Sonst zaehlten die Suchen ohne Treffer nicht mehr an derselben Aussage.
    gesucht = "Tempolimit bringt nichts"
    suchanfrage = await _anlegen(
        statement_service, gesucht, SEARCH_QUERY_AUTHOR, ContentOrigin.SEARCH_QUERY
    )

    zweite = await _anlegen(
        statement_service,
        "tempolimit bringt nichts",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )

    assert zweite == suchanfrage
    suchen_ohne_treffer_ohne_datenbank.ueber_der_schwelle.assert_not_called()


async def test_zaehlt_nur_sichtbare_unbeantwortete_suchanfragen(
    statement_service, status_setzen
):
    # Zaehler am Umschalter der Vormoderation: ein Zaehlaufruf statt einer Abfrage je ID.
    offen = await _anlegen(
        statement_service,
        "Solarpflicht ruiniert Hausbesitzer",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )
    gesperrt = await _anlegen(
        statement_service,
        "Bürgergeld lockt Zuwanderer an",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )
    await status_setzen(gesperrt, ContentStatus.BLOCKED)
    gepflegt = await _anlegen(statement_service, "Bahnfahren ist zu teuer")

    anzahl = await statement_service.zaehle_unbeantwortete_suchanfragen(
        frozenset({offen, gesperrt, gepflegt, uuid.uuid4()})
    )

    assert anzahl == 1


@NICHT_FREIGEGEBEN
async def test_antwort_per_id_an_nicht_freigegebene_suchanfrage_geht_nicht(
    statement_service,
    commentary_service,
    sichtbare_suchanfragen,
    entscheidung,
):
    # addReplysuggestionToStatement mit bekannter ID: abgelehnt, nichts angehaengt.
    gesucht = "Die Grünen wollen Grillen verbieten"
    suchanfrage = await _anlegen(
        statement_service, gesucht, SEARCH_QUERY_AUTHOR, ContentOrigin.SEARCH_QUERY
    )
    _entscheidung_setzen(sichtbare_suchanfragen, suchanfrage, entscheidung)
    kommentar = await _kommentar(commentary_service, "Grillen bleibt erlaubt.")

    with pytest.raises(SuchanfrageNichtFreigegeben):
        await _verknuepfen(
            statement_service, suchanfrage, kommentar, ContentType.COMMENTARY
        )

    await _bleibt_in_der_vormoderation(statement_service, suchanfrage, gesucht)


@NICHT_FREIGEGEBEN
async def test_beitrag_per_id_einer_nicht_freigegebenen_suchanfrage(
    statement_service,
    commentary_service,
    sichtbare_suchanfragen,
    entscheidung,
):
    # Beitragsformular mit ?aussage=<ID>: mit Text eine eigene Aussage, ohne Text
    # "nicht gefunden"; der Wortlaut der Suchanfrage geht nie zurueck.
    gesucht = "Das Deutschlandticket wird abgeschafft"
    suchanfrage = await _anlegen(
        statement_service, gesucht, SEARCH_QUERY_AUTHOR, ContentOrigin.SEARCH_QUERY
    )
    _entscheidung_setzen(sichtbare_suchanfragen, suchanfrage, entscheidung)
    kommentar = await _kommentar(commentary_service, "Das Ticket bleibt.")

    with pytest.raises(AussageNichtGefunden):
        await statement_service.beitrag_als_antwort_verknuepfen(
            beitrag_id=kommentar,
            content_type=ContentType.COMMENTARY,
            relevance=1.0,
            author="person-1",
            statement_id=suchanfrage,
        )

    eigener = "das Deutschlandticket wird abgeschafft!"
    statement_id, text, neu = await statement_service.beitrag_als_antwort_verknuepfen(
        beitrag_id=kommentar,
        content_type=ContentType.COMMENTARY,
        relevance=1.0,
        author="person-1",
        statement_id=suchanfrage,
        statement_text=eigener,
    )

    assert neu
    assert statement_id != suchanfrage
    assert text == eigener
    assert (await statement_service.get(statement_id)).replysuggestions_count == 1
    await _bleibt_in_der_vormoderation(statement_service, suchanfrage, gesucht)


async def test_antwort_per_id_an_freigegebene_suchanfrage_wie_bisher(
    statement_service, commentary_service, sichtbare_suchanfragen
):
    suchanfrage = await _anlegen(
        statement_service,
        "Wärmepumpen funktionieren im Altbau nicht",
        SEARCH_QUERY_AUTHOR,
        ContentOrigin.SEARCH_QUERY,
    )
    _entscheidung_setzen(sichtbare_suchanfragen, suchanfrage, True)
    kommentar = await _kommentar(commentary_service, "Doch, mit Planung.")

    await _verknuepfen(
        statement_service, suchanfrage, kommentar, ContentType.COMMENTARY
    )

    assert (await statement_service.get(suchanfrage)).replysuggestions_count == 1


async def test_zweimal_derselbe_text_ergibt_genau_eine_neue_aussage(
    statement_service, sichtbare_suchanfragen
):
    # Die verborgene Suchanfrage ist kein Kandidat; der zweite Aufruf landet auf der
    # eigenen Aussage des ersten. Sonst entstuende je Aufruf eine weitere, und zweimal
    # "neu" verriete, dass es eine verborgene Suchanfrage mit diesem Text gibt.
    gesucht = "Die Grünen wollen das Eigenheim abschaffen"
    suchanfrage = await _anlegen(
        statement_service, gesucht, SEARCH_QUERY_AUTHOR, ContentOrigin.SEARCH_QUERY
    )

    erst_neu, erste, _ = await statement_service.vorab_anlegen(gesucht, "person-1")
    dann_neu, zweite, text = await statement_service.vorab_anlegen(gesucht, "person-2")

    assert erst_neu
    assert erste != suchanfrage
    assert not dann_neu
    assert zweite == erste
    assert text == gesucht
    await _bleibt_in_der_vormoderation(statement_service, suchanfrage, gesucht)
