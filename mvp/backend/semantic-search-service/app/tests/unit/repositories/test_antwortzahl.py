"""
Die Zahl "N Antworten" (repositories/implementations/qdrant/antwortzahl.py, #631):
nur Beitraege, die die Suche findet, und ungueltige Verweise brechen nichts ab.
"""

import uuid

import pytest

from repositories.implementations.qdrant.antwortzahl import (
    findet_die_suche,
    sichtbare_antworten_zaehlen,
)
from tests.conftest import create_base_content_fields


def _beitrag(speicher, **felder) -> str:
    beitrag_id = str(uuid.uuid4())
    speicher.add_test_data(
        "commentary",
        [{**create_base_content_fields(), "id": beitrag_id, **felder}],
    )
    return beitrag_id


@pytest.mark.unit
class TestFindetDieSuche:
    @pytest.mark.parametrize("status", ["visible", None, "approved", "draft"])
    def test_sichtbar_altwert_und_ohne_status(self, status):
        assert findet_die_suche(status)

    @pytest.mark.parametrize(
        "status", ["blocked", "deleted", "pending_review", "pending_description"]
    )
    def test_ausgeblendet_und_pending_review(self, status):
        """pending_review findet die Suche nicht (ALT_AUFFINDBAR), also zaehlt es nicht."""
        assert not findet_die_suche(status)


@pytest.mark.unit
@pytest.mark.asyncio
class TestSichtbareAntwortenZaehlen:
    async def test_zaehlt_nur_was_die_suche_findet(self, test_embeddings_manager):
        speicher = test_embeddings_manager
        ids = [
            _beitrag(speicher, status="visible"),
            _beitrag(speicher, status="blocked"),
            _beitrag(speicher, status="deleted"),
            str(uuid.uuid4()),  # endgueltig entfernt
        ]

        zahl = await sichtbare_antworten_zaehlen(
            speicher.async_client, "c", ids + [ids[0]]
        )

        assert zahl == 1

    async def test_ungueltige_ids_werden_uebersprungen(self, test_embeddings_manager):
        speicher = test_embeddings_manager
        sichtbar = _beitrag(speicher, status="visible")

        zahl = await sichtbare_antworten_zaehlen(
            speicher.async_client, "c", [None, "kaputt", sichtbar]
        )

        assert zahl == 1
        abgefragt = speicher.async_client.retrieve.call_args.kwargs["ids"]
        assert abgefragt == [sichtbar]

    async def test_ohne_ids_keine_abfrage(self, test_embeddings_manager):
        speicher = test_embeddings_manager
        assert await sichtbare_antworten_zaehlen(speicher.async_client, "c", []) == 0
        speicher.async_client.retrieve.assert_not_called()
