"""
Zeitstempel der Inhalte: naive Altwerte (frueher ``datetime.now()`` im UTC-Container)
und neue Werte mit Zeitzone muessen gleich ausgeliefert werden - mit Offset, sonst
liest der Browser sie als Ortszeit ("vor 2 Stunden" fuer einen eben gespeicherten
Beitrag).
"""

import datetime
import json
import uuid

import pytest

from domain.models.commentary import CommentaryDbEntry
from domain.models.statement import StatementReplysuggestion
from domain.models.zeit import als_utc, utc_jetzt
from tests.conftest import create_base_content_fields, create_commentary_data


def _kommentar(created, last_modified) -> CommentaryDbEntry:
    daten = {
        **create_base_content_fields(),
        **create_commentary_data(),
        "id": str(uuid.uuid4()),
        "content_type": "commentary",
        "created": created,
        "last_modified": last_modified,
    }
    return CommentaryDbEntry.model_validate(daten)


@pytest.mark.unit
class TestZeitstempelUtc:
    def test_utc_jetzt_traegt_die_zeitzone(self):
        assert utc_jetzt().tzinfo == datetime.timezone.utc

    def test_naiver_wert_gilt_als_utc(self):
        naiv = datetime.datetime(2026, 9, 17, 8, 6, 22)
        assert als_utc(naiv) == datetime.datetime(
            2026, 9, 17, 8, 6, 22, tzinfo=datetime.timezone.utc
        )

    def test_anderer_offset_wird_nach_utc_umgerechnet(self):
        berlin = datetime.timezone(datetime.timedelta(hours=2))
        wert = datetime.datetime(2026, 9, 17, 10, 6, 22, tzinfo=berlin)
        assert als_utc(wert).isoformat() == "2026-09-17T08:06:22+00:00"

    def test_altwert_und_neuer_wert_werden_gleich_ausgeliefert(self):
        alt = _kommentar("2026-09-17T08:06:22.123456", "2026-09-17T08:06:22.123456")
        neu = _kommentar(
            "2026-09-17T08:06:22.123456Z", "2026-09-17T08:06:22.123456+00:00"
        )

        alt_json = json.loads(alt.model_dump_json())
        neu_json = json.loads(neu.model_dump_json())

        assert alt_json["created"] == neu_json["created"]
        assert alt_json["last_modified"] == neu_json["last_modified"]
        assert alt_json["created"].endswith("Z")

    def test_altwerte_lassen_sich_mit_neuen_sortieren(self):
        """/recent sortiert model_dump-Werte; naiv und aware gemischt waere ein TypeError."""
        alt = _kommentar("2026-09-17T08:00:00", "2026-09-17T08:00:00").model_dump()
        neu = _kommentar(utc_jetzt().isoformat(), utc_jetzt().isoformat()).model_dump()

        reihenfolge = sorted([alt, neu], key=lambda x: x["created"], reverse=True)

        assert reihenfolge[0] is neu

    def test_antwortvorschlag_zeiten_mit_offset(self):
        vorschlag = StatementReplysuggestion.model_validate(
            {
                "id": str(uuid.uuid4()),
                "content_type": "commentary",
                "relevance": 1.0,
                "created": "2026-09-17T08:06:22",
                "updated": "2026-09-17T08:06:22",
                "number_of_usages": 0,
            }
        )
        assert (
            json.loads(vorschlag.model_dump_json())["created"] == "2026-09-17T08:06:22Z"
        )


@pytest.mark.unit
class TestCountLastWeek:
    """count_last_week vergleicht Zeitpunkte, nicht Zeichenketten: naive Altwerte (UTC)
    und neue Werte mit Offset zaehlen gleich."""

    @pytest.mark.asyncio
    async def test_zaehlt_naive_und_aware_werte_der_letzten_woche(
        self, test_settings, test_embeddings_manager
    ):
        from unittest.mock import AsyncMock, MagicMock
        from repositories.implementations.qdrant.statement_repository import (
            StatementRepository,
        )

        jetzt = utc_jetzt()
        vor = lambda tage: (jetzt - datetime.timedelta(days=tage))  # noqa: E731
        punkte = [
            # naiv, gestern -> zaehlt
            MagicMock(payload={"created": vor(1).replace(tzinfo=None).isoformat()}),
            # mit Z, vor drei Tagen -> zaehlt
            MagicMock(payload={"created": vor(3).isoformat().replace("+00:00", "Z")}),
            # naiv, vor zehn Tagen, aber heute geaendert (mit Offset) -> zaehlt
            MagicMock(
                payload={
                    "created": vor(10).replace(tzinfo=None).isoformat(),
                    "last_modified": jetzt.isoformat(),
                }
            ),
            # vor zehn Tagen -> zaehlt nicht
            MagicMock(payload={"created": vor(10).isoformat()}),
            # kaputter Wert -> zaehlt nicht, bricht nichts
            MagicMock(payload={"created": "kein Datum"}),
        ]
        manager = MagicMock()
        manager.collection_name = "content_collection"
        manager.async_client.scroll = AsyncMock(side_effect=[(punkte, None)])

        repository = StatementRepository(
            test_settings, embeddings_manager=test_embeddings_manager
        )
        repository._shared_manager = manager

        assert await repository.count_last_week() == 3
