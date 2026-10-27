"""
Der Autor loescht seinen Beitrag (BeitragLoeschenService, #250).

Loeschen setzt nur den Zustand "geloescht": Der Beitrag bleibt gespeichert, die
Repositories blenden ihn aus. Andere als der Autor duerfen nicht loeschen.
"""

import json
import uuid
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel, ValidationError

from domain.models.content_status import ContentStatus
from repositories.aggregated.content_repository import ContentRepository
from repositories.implementations.qdrant.moderation_repository import (
    QdrantModerationRepository,
)
from services.content.beitrag_loeschen_service import (
    BeitragLoeschenService,
    LoeschErgebnis,
)
from tests.conftest import create_base_content_fields

BEITRAG_ID = str(uuid.uuid4())
AUTOR = "autor-1"


def _beitrag(content_type="commentary", **felder):
    return {
        **create_base_content_fields(original_author=AUTOR, last_modified_by=AUTOR),
        "id": BEITRAG_ID,
        "text": "Wärmepumpe lohnt sich auch im Altbau",
        "status": ContentStatus.VISIBLE.value,
        **felder,
        "content_type": content_type,
    }


@pytest.fixture
def speicher(test_embeddings_manager):
    return test_embeddings_manager


@pytest.fixture
def repository(test_settings, speicher):
    return ContentRepository(test_settings, speicher)


@pytest.fixture
def moderation_repo(speicher):
    return QdrantModerationRepository(embeddings_manager=speicher)


@pytest.fixture
def service(repository, moderation_repo):
    return BeitragLoeschenService(repository, moderation_repo)


def _status(speicher) -> str:
    return speicher.get_data()[BEITRAG_ID]["status"]


def _aussage_mit_verweis(speicher) -> str:
    """Eine Aussage, deren einziger Antwortvorschlag der Beitrag ist."""
    aussage_id = str(uuid.uuid4())
    speicher.add_test_data(
        "statement",
        [
            {
                **create_base_content_fields(),
                "id": aussage_id,
                "replysuggestions": json.dumps([{"id": BEITRAG_ID}]),
                "replysuggestions_count": 1,
            }
        ],
    )
    return aussage_id


@pytest.mark.unit
@pytest.mark.asyncio
class TestBeitragLoeschen:
    async def test_loeschen_autor_setzt_zustand_geloescht(
        self, service, speicher, repository
    ):
        speicher.add_test_data("commentary", [_beitrag()])

        ergebnis = await service.loeschen(uuid.UUID(BEITRAG_ID), AUTOR)

        assert ergebnis is LoeschErgebnis.GELOESCHT
        # Gespeichert bleibt er, nur fuer Leser ist er nicht mehr da.
        assert _status(speicher) == ContentStatus.DELETED.value
        with pytest.raises(ValueError):
            await repository.get(uuid.UUID(BEITRAG_ID))

    async def test_loeschen_andere_person_aendert_nichts(self, service, speicher):
        speicher.add_test_data("commentary", [_beitrag()])

        ergebnis = await service.loeschen(uuid.UUID(BEITRAG_ID), "andere-person")

        assert ergebnis is LoeschErgebnis.NICHT_AUTOR
        assert _status(speicher) == ContentStatus.VISIBLE.value

    async def test_loeschen_aussage_ist_kein_beitrag(self, service, speicher):
        speicher.add_test_data("statement", [_beitrag("statement")])

        ergebnis = await service.loeschen(uuid.UUID(BEITRAG_ID), AUTOR)

        assert ergebnis is LoeschErgebnis.NICHT_DA
        assert _status(speicher) == ContentStatus.VISIBLE.value

    async def test_loeschen_gesperrt_bleibt_gesperrt(self, service, speicher):
        speicher.add_test_data(
            "post", [_beitrag("post", status=ContentStatus.BLOCKED.value)]
        )

        ergebnis = await service.loeschen(uuid.UUID(BEITRAG_ID), AUTOR)

        assert ergebnis is LoeschErgebnis.NICHT_DA
        assert _status(speicher) == ContentStatus.BLOCKED.value

    async def test_loeschen_unbekannte_id_ist_nicht_da(self, service):
        ergebnis = await service.loeschen(uuid.uuid4(), AUTOR)

        assert ergebnis is LoeschErgebnis.NICHT_DA

    async def test_loeschen_bild_ohne_unterschrift_ist_nicht_da(
        self, service, speicher
    ):
        """Altbilder ohne Unterschrift (vor #281) sind ausgeblendet, auch fuer den Autor."""
        speicher.add_test_data(
            "image",
            [_beitrag("image", status=ContentStatus.PENDING_DESCRIPTION.value)],
        )

        ergebnis = await service.loeschen(uuid.UUID(BEITRAG_ID), AUTOR)

        assert ergebnis is LoeschErgebnis.NICHT_DA
        assert _status(speicher) == ContentStatus.PENDING_DESCRIPTION.value

    async def test_loeschen_sperre_zwischen_lesen_und_schreiben_bleibt(
        self, service, speicher, repository
    ):
        """Sperrt ein Admin, nachdem der Dienst gelesen hat, gewinnt die Sperre."""
        speicher.add_test_data("commentary", [_beitrag()])
        lesen = repository.get

        async def lesen_dann_sperren(item_id):
            beitrag = await lesen(item_id)
            speicher.get_data()[BEITRAG_ID]["status"] = ContentStatus.BLOCKED.value
            return beitrag

        repository.get = lesen_dann_sperren

        await service.loeschen(uuid.UUID(BEITRAG_ID), AUTOR)

        assert _status(speicher) == ContentStatus.BLOCKED.value

    async def test_loeschen_unlesbarer_datensatz_ist_fehler(self, service, repository):
        """ValidationError ist ein ValueError, heisst hier aber nicht "nicht da"."""

        class Modell(BaseModel):
            text: str

        with pytest.raises(ValidationError) as unlesbar:
            Modell.model_validate({})
        repository.get = AsyncMock(side_effect=unlesbar.value)

        with pytest.raises(ValidationError):
            await service.loeschen(uuid.UUID(BEITRAG_ID), AUTOR)


@pytest.mark.unit
@pytest.mark.asyncio
class TestVerweiseAnAussagen:
    """
    Eine Aussage verweist nach dem Loeschen nicht mehr auf den Beitrag; war er ihr
    einziger, zaehlt sie nicht mehr als beantwortet (#294).
    """

    async def test_loeschen_entfernt_verweis_aus_aussage(self, service, speicher):
        speicher.add_test_data("generic_text", [_beitrag("generic_text")])
        aussage_id = _aussage_mit_verweis(speicher)

        await service.loeschen(uuid.UUID(BEITRAG_ID), AUTOR)

        aussage = speicher.get_data()[aussage_id]
        assert json.loads(aussage["replysuggestions"]) == []
        assert aussage["replysuggestions_count"] == 0

    async def test_loeschen_andere_person_laesst_verweis_stehen(
        self, service, speicher
    ):
        speicher.add_test_data("commentary", [_beitrag()])
        aussage_id = _aussage_mit_verweis(speicher)

        await service.loeschen(uuid.UUID(BEITRAG_ID), "andere-person")

        assert speicher.get_data()[aussage_id]["replysuggestions_count"] == 1

    async def test_loeschen_gesperrt_laesst_verweis_stehen(self, service, speicher):
        """Entsperren soll den Beitrag samt Verweisen zurueckbringen."""
        speicher.add_test_data(
            "commentary", [_beitrag(status=ContentStatus.BLOCKED.value)]
        )
        aussage_id = _aussage_mit_verweis(speicher)

        await service.loeschen(uuid.UUID(BEITRAG_ID), AUTOR)

        assert speicher.get_data()[aussage_id]["replysuggestions_count"] == 1

    async def test_loeschen_verweise_scheitern_beitrag_bleibt_sichtbar(
        self, service, speicher, moderation_repo
    ):
        """Erst die Verweise, dann der Zustand: Der Autor kann es erneut versuchen."""
        speicher.add_test_data("commentary", [_beitrag()])
        moderation_repo.aus_aussagen_entfernen = AsyncMock(
            side_effect=RuntimeError("Qdrant nicht erreichbar")
        )

        with pytest.raises(RuntimeError):
            await service.loeschen(uuid.UUID(BEITRAG_ID), AUTOR)

        assert _status(speicher) == ContentStatus.VISIBLE.value
