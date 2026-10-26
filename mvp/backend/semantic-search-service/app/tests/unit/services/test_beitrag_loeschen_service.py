"""
Der Autor loescht seinen Beitrag (BeitragLoeschenService, #250).

Loeschen setzt nur den Zustand "geloescht": Der Beitrag bleibt gespeichert, die
Repositories blenden ihn aus. Andere als der Autor duerfen nicht loeschen.
"""

import uuid

import pytest

from domain.models.content_status import ContentStatus
from repositories.aggregated.content_repository import ContentRepository
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
def service(repository):
    return BeitragLoeschenService(repository)


def _status(speicher) -> str:
    return speicher.get_data()[BEITRAG_ID]["status"]


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

    async def test_loeschen_bild_ohne_unterschrift(self, service, speicher):
        """Der Autor sieht es in "Meine Beitraege", also kann er es auch loeschen."""
        speicher.add_test_data(
            "image",
            [_beitrag("image", status=ContentStatus.PENDING_DESCRIPTION.value)],
        )

        ergebnis = await service.loeschen(uuid.UUID(BEITRAG_ID), AUTOR)

        assert ergebnis is LoeschErgebnis.GELOESCHT
        assert _status(speicher) == ContentStatus.DELETED.value
