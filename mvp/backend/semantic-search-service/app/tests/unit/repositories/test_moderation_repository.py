"""
QdrantModerationRepository: der Zugriff der Moderation auf den Suchindex.

Anders als die Beitrags-Repositories filtert es gesperrte Beitraege nicht heraus,
denn nur ueber die Moderation finden Admins sie noch.
"""

import json
import uuid

import pytest

from repositories.implementations.qdrant.moderation_repository import (
    QdrantModerationRepository,
)
from tests.conftest import create_base_content_fields

BEITRAG_ID = str(uuid.uuid4())


@pytest.fixture
def speicher(test_embeddings_manager):
    test_embeddings_manager.add_test_data(
        "commentary",
        [
            {
                **create_base_content_fields(),
                "id": BEITRAG_ID,
                "text": "Gemeldeter Kommentar",
                "status": "approved",
            }
        ],
    )
    return test_embeddings_manager


@pytest.fixture
def repo(speicher):
    return QdrantModerationRepository(embeddings_manager=speicher)


def _payload(speicher, beitrag_id=BEITRAG_ID) -> dict:
    return speicher.get_data()[beitrag_id]


@pytest.mark.unit
@pytest.mark.asyncio
class TestLaden:
    async def test_laedt_auch_gesperrte(self, repo, speicher):
        await repo.sperren(BEITRAG_ID, status_vorher="approved")

        beitrag = await repo.laden(BEITRAG_ID)

        assert beitrag["text"] == "Gemeldeter Kommentar"
        assert beitrag["status"] == "blocked"

    async def test_unbekannter_beitrag_ist_none(self, repo):
        assert await repo.laden(str(uuid.uuid4())) is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestSperrenEntsperren:
    async def test_sperren_merkt_status_von_vorher(self, repo, speicher):
        await repo.sperren(BEITRAG_ID, status_vorher="approved")

        assert _payload(speicher)["status"] == "blocked"
        assert _payload(speicher)["status_vor_sperre"] == "approved"

    async def test_entsperren_stellt_status_wieder_her(self, repo, speicher):
        await repo.sperren(BEITRAG_ID, status_vorher="approved")

        await repo.entsperren(BEITRAG_ID, status_vorher="approved")

        assert _payload(speicher)["status"] == "approved"
        assert "status_vor_sperre" not in _payload(speicher)

    async def test_entsperren_ohne_status_von_vorher_entfernt_status(
        self, repo, speicher
    ):
        await repo.sperren(BEITRAG_ID, status_vorher=None)

        await repo.entsperren(BEITRAG_ID, status_vorher=None)

        assert "status" not in _payload(speicher)
        assert "status_vor_sperre" not in _payload(speicher)

    async def test_gesperrte_listet_nur_gesperrte(self, repo, speicher):
        anderer = str(uuid.uuid4())
        speicher.add_test_data(
            "reference",
            [{**create_base_content_fields(), "id": anderer, "status": "approved"}],
        )
        await repo.sperren(BEITRAG_ID, status_vorher="approved")

        gesperrte = await repo.gesperrte(limit=10)

        assert [beitrag["id"] for beitrag in gesperrte] == [BEITRAG_ID]


@pytest.mark.unit
@pytest.mark.asyncio
class TestEntfernen:
    async def test_entfernt_beitrag(self, repo, speicher):
        assert await repo.entfernen(BEITRAG_ID) is True

        assert BEITRAG_ID not in speicher.get_data()

    async def test_unbekannter_beitrag(self, repo):
        assert await repo.entfernen(str(uuid.uuid4())) is False

    async def test_entfernt_verweise_aus_aussagen(self, repo, speicher):
        aussage_id = str(uuid.uuid4())
        andere_antwort = str(uuid.uuid4())
        speicher.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(),
                    "id": aussage_id,
                    "text": "Eine Aussage",
                    "replysuggestions": json.dumps(
                        [{"id": BEITRAG_ID}, {"id": andere_antwort}]
                    ),
                    "replysuggestions_count": 2,
                }
            ],
        )

        assert await repo.aus_aussagen_entfernen(BEITRAG_ID) == 1

        aussage = _payload(speicher, aussage_id)
        assert json.loads(aussage["replysuggestions"]) == [{"id": andere_antwort}]
        assert aussage["replysuggestions_count"] == 1
        assert aussage["text"] == "Eine Aussage"

    async def test_aussage_ohne_verweis_bleibt_unveraendert(self, repo, speicher):
        aussage_id = str(uuid.uuid4())
        speicher.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(),
                    "id": aussage_id,
                    "replysuggestions": [{"id": str(uuid.uuid4())}],
                }
            ],
        )

        assert await repo.aus_aussagen_entfernen(BEITRAG_ID) == 0

        speicher.async_client.set_payload.assert_not_called()
