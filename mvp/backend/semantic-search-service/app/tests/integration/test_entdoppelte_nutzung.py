"""
Entdoppelte Nutzung (#352) gegen ein echtes PostgreSQL.

Der Zaehler an der Karte zaehlt jede Nutzung; fuer Punkte und "Diese Woche oft
genutzt" zaehlt eine Nutzung hoechstens einmal je Person, Beitrag und Tag. Gemerkt
wird dafuer nur ein Pruefwert (services/entdoppelung.py). Wegwerf-Schema aus der
Fixture ``datenbank`` von ``test_loeschkommando.py``.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from infrastructure.database.models import NutzungHeute, UsageEvent
from repositories.usage_tracking_repository import UsageTrackingRepository
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

pytestmark = pytest.mark.integration


def _vor_tagen(datenbank, beitrag: uuid.UUID, tage: float) -> None:  # noqa: F811
    with datenbank.get_session() as s:
        s.execute(
            update(UsageEvent)
            .where(UsageEvent.content_id == beitrag)
            .values(timestamp=datetime.now(timezone.utc) - timedelta(days=tage))
        )


class TestEntdoppelteNutzung:
    def test_track_usage_zweite_nutzung_derselben_person_zaehlt_nur_an_der_karte(
        self, datenbank  # noqa: F811
    ):
        repo = UsageTrackingRepository(datenbank)
        beitrag = uuid.uuid4()

        repo.track_usage(beitrag, pruefwert="kim-heute-beitrag")
        repo.track_usage(beitrag, pruefwert="kim-heute-beitrag")
        repo.track_usage(beitrag, pruefwert="bo-heute-beitrag")

        assert repo.get_usage_count(beitrag) == 3
        assert repo.get_nutzung_entdoppelt_batch([beitrag]) == {str(beitrag): 2}

    def test_track_usage_ohne_pruefwert_nicht_entdoppelt(self, datenbank):  # noqa: F811
        repo = UsageTrackingRepository(datenbank)
        beitrag = uuid.uuid4()

        repo.track_usage(beitrag)

        assert repo.get_usage_count(beitrag) == 1
        assert repo.get_nutzung_entdoppelt_batch([beitrag]) == {str(beitrag): 0}

    def test_get_trending_content_nur_entdoppelt_zaehlt_verschiedene_personen(
        self, datenbank  # noqa: F811
    ):
        """ "Diese Woche oft genutzt" zaehlt nur Nutzung verschiedener Personen."""
        repo = UsageTrackingRepository(datenbank)
        oft_kopiert, breit_genutzt = uuid.uuid4(), uuid.uuid4()
        for _ in range(5):
            repo.track_usage(oft_kopiert, pruefwert=f"kim-{oft_kopiert}")
        for person in ["kim", "bo", "ali"]:
            repo.track_usage(breit_genutzt, pruefwert=f"{person}-{breit_genutzt}")

        alle = repo.get_trending_content(limit=10, hours=168)
        entdoppelt = repo.get_trending_content(limit=10, hours=168, nur_entdoppelt=True)

        assert alle[0] == {
            "content_id": str(oft_kopiert),
            "recent_uses": 5,
            "total_uses": 5,
        }
        assert [(t["content_id"], t["recent_uses"]) for t in entdoppelt] == [
            (str(breit_genutzt), 3),
            (str(oft_kopiert), 1),
        ]

    def test_nutzung_entdoppelt_ueberdauert_die_ereignisse(
        self, datenbank  # noqa: F811
    ):
        repo = UsageTrackingRepository(datenbank)
        beitrag = uuid.uuid4()
        repo.track_usage(beitrag, pruefwert="kim")
        _vor_tagen(datenbank, beitrag, 100)

        repo.cleanup_old_events(days_to_keep=90)

        assert repo.get_nutzung_entdoppelt_batch([beitrag]) == {str(beitrag): 1}

    def test_vergangene_tage_verwerfen_laesst_nur_heute(self, datenbank):  # noqa: F811
        repo = UsageTrackingRepository(datenbank)
        heute = date(2026, 10, 30)
        repo.track_usage(uuid.uuid4(), pruefwert="gestern", tag=heute - timedelta(1))
        repo.track_usage(uuid.uuid4(), pruefwert="heute", tag=heute)

        assert repo.vergangene_tage_verwerfen(heute) == 1

        with datenbank.get_session() as s:
            assert s.execute(select(NutzungHeute.pruefwert)).scalars().all() == [
                "heute"
            ]
