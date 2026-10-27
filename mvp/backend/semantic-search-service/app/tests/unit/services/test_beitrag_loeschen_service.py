"""
Der Autor loescht seinen Beitrag (BeitragLoeschenService, #250).

Loeschen setzt nur den Zustand "geloescht": Der Beitrag bleibt gespeichert, die
Repositories blenden ihn aus. Andere als der Autor duerfen nicht loeschen.
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel, ValidationError

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
