"""
Der Autor aendert seinen Beitrag, gegen echtes Qdrant (#299).

Die Unit-Tests pruefen den Service gegen den Speicher-Modus; hier zeigt sich, dass
die Suche nach dem Aendern den neuen Text findet (der Vektor ist neu berechnet), dass
der Rest des Punkts bleibt und dass eine Sperre zwischen Lesen und Schreiben steht.
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from domain.models.commentary import Commentary
from domain.models.content_origin import ContentOrigin
from domain.models.content_status import AUSGEBLENDET, ContentStatus
from domain.models.content_type import ContentType
from services.content.commentary_service import CommentaryService
from services.content.beitrag_aendern_service import (
    AenderErgebnis,
    Aenderung,
    BeitragAendernService,
)
from tests.integration.conftest import requires_qdrant

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]

AUTOR = "autor-1"
ALT = "Ein Tempolimit auf Autobahnen spart sofort CO2 und kostet nichts."
NEU = "Mehr Radwege in der Stadt machen den Schulweg für Kinder sicherer."


@pytest.fixture
def kommentare(integration_settings, real_repository_factory):
    return CommentaryService(integration_settings, real_repository_factory)


@pytest.fixture
def inhalte(integration_settings, real_repository_factory):
    return real_repository_factory.create_content_repository(integration_settings)


@pytest.fixture
def aendern(inhalte):
    return BeitragAendernService(inhalte, AsyncMock(return_value=uuid.uuid4()))


async def _kommentar(kommentare) -> uuid.UUID:
    _, kommentar_id, _ = await kommentare.add_commentary(
        Commentary(title="Tempolimit spart CO2", text=ALT, references=[]),
        AUTOR,
        ContentStatus.VISIBLE,
        ContentOrigin.MANUALLY_CREATED,
    )
    return kommentar_id


async def test_aendern_suche_findet_den_neuen_text(
    kommentare, aendern, real_embeddings_manager
):
    kommentar_id = await _kommentar(kommentare)
    await real_embeddings_manager.async_client.set_payload(
        collection_name=real_embeddings_manager.collection_name,
        payload={"report_count": 2},
        points=[str(kommentar_id)],
    )

    ergebnis = await aendern.aendern(
        kommentar_id, AUTOR, Aenderung("Radwege machen den Schulweg sicher", NEU, [])
    )

    assert ergebnis is AenderErgebnis.GEAENDERT
    treffer = await kommentare.search("sicherer Schulweg mit dem Rad", limit=1)
    assert [t.id for t in treffer] == [kommentar_id]
    assert treffer[0].text == NEU
    # Ohne den alten Text gilt der Kommentar auch nicht mehr als dessen Dublette.
    assert (await kommentare.pruefe_dublette(ALT)).vorhanden is None
    assert (await kommentare.pruefe_dublette(NEU)).vorhanden.id == kommentar_id
    # Was nicht geaendert wurde, bleibt.
    gespeichert = await kommentare.get(kommentar_id)
    assert gespeichert.report_count == 2
    assert gespeichert.original_author == AUTOR
    assert [e.editor for e in gespeichert.edit_history] == [AUTOR]


async def test_aendern_laesst_eine_sperre_stehen(
    kommentare, inhalte, real_embeddings_manager
):
    """Der Ausschluss wirkt im selben Schreibvorgang wie die Felder."""
    kommentar_id = await _kommentar(kommentare)
    await inhalte.update_status(kommentar_id, ContentStatus.BLOCKED)

    await inhalte.inhalt_aendern(
        kommentar_id,
        ContentType.COMMENTARY.value,
        {"title": "Geändert", "text": NEU},
        nicht_aus=AUSGEBLENDET,
    )

    punkt = await real_embeddings_manager.get_by_id(str(kommentar_id))
    assert punkt["status"] == ContentStatus.BLOCKED.value
    assert punkt["title"] == "Tempolimit spart CO2"
    assert punkt["text"] == ALT
