"""
Dieselben Faelle wie tests/unit/services/test_vektor_benennen.py, aber gegen einen
echten Qdrant: Aliase und Payload-Indizes wertet hier der Server aus. Dazu der
Dienst selbst vor und nach der Umstellung: Er sucht auf der alten Collection mit
unbenanntem Vektor (Uebergang) und nach einem Neustart ueber den Alias mit
benanntem Vektor, mit denselben Treffern.
"""

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from domain.interfaces.embeddings_manager import Suchparameter
from services.embeddings.qdrant_embeddings_manager import QdrantEmbeddingsManager
from services.wartung.vektor_benennen import benennen, ziel_collection
from tests.integration.conftest import QDRANT_URL, requires_qdrant
from tests.unit.services import test_vektor_benennen as faelle

pytestmark = [pytest.mark.integration, requires_qdrant]


@pytest.fixture
def client():
    client = QdrantClient(url=QDRANT_URL, timeout=10, check_compatibility=False)
    faelle.punkte_anlegen(client)
    yield client
    faelle.abraeumen(client)


class TestVektorBenennenGegenQdrant(faelle.TestVektorBenennen):
    def test_payload_indizes_uebernommen(self, client):
        benennen(client, faelle.COLLECTION, ausfuehren=True)

        schema = client.get_collection(faelle.COLLECTION).payload_schema
        assert schema["content_type"].data_type.value == "keyword"


BESTAND = [
    ("commentary", "Ein Tempolimit rettet Leben"),
    ("statement", "Tempolimit auf Autobahnen"),
    ("commentary", "Waermepumpen lohnen sich im Altbau"),
]


@pytest.fixture
def leerer_name(integration_settings):
    """Der Collection-Name des Laufs, ohne die Collection von real_embeddings_manager."""
    client = QdrantClient(url=QDRANT_URL, timeout=10, check_compatibility=False)
    name = integration_settings.qdrant_collection
    for alt in (name, ziel_collection(name)):
        if client.collection_exists(alt):
            client.delete_collection(alt)
    yield client, name
    for alt in (name, ziel_collection(name)):
        if client.collection_exists(alt):
            client.delete_collection(alt)


async def _gestartet(integration_settings, einbettungsmodell):
    QdrantEmbeddingsManager._instance = None
    manager = QdrantEmbeddingsManager(
        integration_settings, einbettungsmodell=einbettungsmodell
    )
    await manager.start()
    return manager


async def _suchen(manager):
    treffer = await manager.search_batch(
        "Bringt ein Tempolimit etwas?",
        [Suchparameter("commentary", None, 5), Suchparameter("statement", None, 5)],
    )
    einzeln = await manager.search("Bringt ein Tempolimit etwas?", limit=10)
    return [[(t["id"], t["score"]) for t in liste] for liste in [*treffer, einzeln]]


@pytest.mark.asyncio
async def test_dienst_sucht_vor_und_nach_der_umstellung_gleich(
    leerer_name, integration_settings, einbettungsmodell
):
    client, name = leerer_name

    # Collection wie vor #395 anlegen, den Bestand schreibt der Dienst selbst.
    client.create_collection(
        name, vectors_config=VectorParams(size=768, distance=Distance.COSINE)
    )
    manager = await _gestartet(integration_settings, einbettungsmodell)
    try:
        for nummer, (typ, text) in enumerate(BESTAND, start=1):
            await manager.upsert_batch(
                [
                    (
                        f"00000000-0000-4000-8000-00000000000{nummer}",
                        {"text": text},
                        text,
                    )
                ],
                typ,
            )
        vorher = await _suchen(manager)

        bericht = benennen(client, name, ausfuehren=True)
        assert bericht.kopiert == 3
        # Ohne Neustart sucht der Dienst ohne Vektornamen; das meldet die Gesundheit.
        ohne_neustart = await manager.health_check()
        await manager.shutdown()

        manager = await _gestartet(integration_settings, einbettungsmodell)
        nachher = await _suchen(manager)
        gesundheit = await manager.health_check()
    finally:
        await manager.shutdown()
        QdrantEmbeddingsManager._instance = None

    assert ohne_neustart == {"status": "unhealthy", "error": "restart_required"}
    assert nachher == vorher
    assert vorher[0][0][0].endswith("1")  # Kommentar zum Tempolimit vorn
    assert gesundheit["status"] == "healthy"
    assert gesundheit["config"]["vector_size"] == 768


@pytest.mark.asyncio
async def test_neu_angelegte_collection_nach_alter_im_selben_prozess(
    leerer_name, integration_settings, einbettungsmodell
):
    """Erst eine alte Collection, dann eine neu angelegte: der Vektor ist benannt."""
    client, name = leerer_name
    client.create_collection(
        name, vectors_config=VectorParams(size=768, distance=Distance.COSINE)
    )
    manager = await _gestartet(integration_settings, einbettungsmodell)
    try:
        await manager.shutdown()
        client.delete_collection(name)
        await manager.start()  # dieselbe Instanz legt die Collection neu an

        await manager.upsert_batch(
            [("00000000-0000-4000-8000-000000000001", {"text": "x"}, "x")],
            "commentary",
        )
        treffer = await manager.search("x", limit=1)
    finally:
        await manager.shutdown()
        QdrantEmbeddingsManager._instance = None

    assert [t["id"] for t in treffer] == ["00000000-0000-4000-8000-000000000001"]


@pytest.mark.asyncio
async def test_neue_collection_mit_benanntem_vektor(real_embeddings_manager):
    info = await real_embeddings_manager.async_client.get_collection(
        real_embeddings_manager.collection_name
    )

    assert set(info.config.params.vectors) == {"e5_base"}
    gesundheit = await real_embeddings_manager.health_check()
    assert gesundheit["config"] == {"vector_size": 768, "distance": "Cosine"}
