"""
Zustaende eines Beitrags gegen echtes Qdrant (#214).

Die Unit-Tests pruefen die Filter als Objekte und die Umstellung im Speicher-Modus;
hier zeigt sich, dass Qdrant den Suchfilter so auswertet wie gedacht, auch fuer
Altbestand zwischen dem Ausrollen und der Umstellung: Was die Suche vorher fand,
findet sie weiter, Gesperrtes nie, und die Dublettenpruefung legt keine zweite
Aussage an.
"""

import pytest
import pytest_asyncio

from domain.models.content_origin import ContentOrigin
from domain.models.content_status import ContentStatus
from domain.models.statement import Statement
from services.content.statement_service import StatementService
from services.wartung.zustaende_umstellen import zustaende_umstellen
from tests.integration.conftest import requires_qdrant

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]

# Gespeicherter Status je Aussage; None heisst: Feld fehlt (Altbestand).
BESTAND = {
    "Tempolimit spart sofort CO2 auf Autobahnen": "released_internal",
    "Windräder töten weniger Vögel als Glasfassaden": None,
    "Wärmepumpen lohnen sich auch im Altbau": "pending_review",
    "Atomkraft ist die billigste Energie überhaupt": "blocked",
}


@pytest.fixture
def statement_service(integration_settings, real_repository_factory):
    return StatementService(
        integration_settings, repository_factory=real_repository_factory
    )


@pytest_asyncio.fixture
async def altbestand(statement_service, real_embeddings_manager):
    """Aussagen anlegen, dann ihren Status auf den gespeicherten Altwert setzen."""
    client = real_embeddings_manager.client
    ids = {}
    for text, status in BESTAND.items():
        _, aussage_id, _ = await statement_service.add_statement(
            Statement(text=text, replysuggestions=[]),
            "person-1",
            ContentStatus.VISIBLE,
            ContentOrigin.MANUALLY_CREATED,
        )
        punkt = str(aussage_id)
        if status is None:
            client.delete_payload(
                real_embeddings_manager.collection_name, keys=["status"], points=[punkt]
            )
        else:
            client.set_payload(
                real_embeddings_manager.collection_name,
                payload={"status": status, "visibility": "internal"},
                points=[punkt],
            )
        ids[text] = aussage_id
    return ids


async def _gefunden(statement_service, text) -> bool:
    treffer = await statement_service.search(text, 10)
    return any(t.text == text for t in treffer)


async def test_suche_vor_der_umstellung_findet_was_sie_vorher_fand(
    statement_service, altbestand
):
    gefunden = {t: await _gefunden(statement_service, t) for t in BESTAND}

    assert gefunden == {
        "Tempolimit spart sofort CO2 auf Autobahnen": True,
        "Windräder töten weniger Vögel als Glasfassaden": True,
        "Wärmepumpen lohnen sich auch im Altbau": False,
        "Atomkraft ist die billigste Energie überhaupt": False,
    }


async def test_einzelansicht_vor_der_umstellung_liest_altwert_als_sichtbar(
    statement_service, altbestand
):
    aussage = await statement_service.get(
        altbestand["Tempolimit spart sofort CO2 auf Autobahnen"]
    )

    assert aussage.status is ContentStatus.VISIBLE


async def test_dublettenpruefung_vor_der_umstellung_nimmt_vorhandene(
    statement_service, altbestand
):
    text = "Tempolimit spart sofort CO2 auf Autobahnen"

    neu, aussage_id, _ = await statement_service.add_statement(
        Statement(text=text, replysuggestions=[]),
        "person-2",
        ContentStatus.VISIBLE,
        ContentOrigin.MANUALLY_CREATED,
    )

    assert neu is False
    assert aussage_id == altbestand[text]


async def test_nach_der_umstellung_findet_die_suche_nur_sichtbare(
    statement_service, altbestand, real_embeddings_manager
):
    bericht = zustaende_umstellen(
        real_embeddings_manager.client,
        real_embeddings_manager.collection_name,
        ausfuehren=True,
    )

    assert bericht.zu_aendern == 4
    gefunden = {t: await _gefunden(statement_service, t) for t in BESTAND}
    assert gefunden == {
        "Tempolimit spart sofort CO2 auf Autobahnen": True,
        "Windräder töten weniger Vögel als Glasfassaden": True,
        "Wärmepumpen lohnen sich auch im Altbau": True,
        "Atomkraft ist die billigste Energie überhaupt": False,
    }
    gesperrt = real_embeddings_manager.client.retrieve(
        real_embeddings_manager.collection_name,
        [str(altbestand["Atomkraft ist die billigste Energie überhaupt"])],
        with_payload=True,
    )[0].payload
    assert gesperrt["status_vor_sperre"] == "visible"
    assert "visibility" not in gesperrt
    assert await statement_service.count_curated() == 3


async def test_zweite_umstellung_findet_nichts(altbestand, real_embeddings_manager):
    client = real_embeddings_manager.client
    collection = real_embeddings_manager.collection_name
    zustaende_umstellen(client, collection, ausfuehren=True)

    assert zustaende_umstellen(client, collection).zu_aendern == 0
