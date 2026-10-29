"""
Nutzung je Fassung (#355) gegen ein echtes PostgreSQL.

Ein Kommentar hat eine Mittelfassung und optional eine Kurz- und eine Langfassung;
kopiert und gezaehlt wird je Fassung. Die Summe je Fassung bleibt ueber die Frist der
``usage_events`` hinaus stehen, der Zuwachs der letzten 7 Tage kommt aus den
Ereignissen. Wegwerf-Schema aus der Fixture ``datenbank`` von ``test_loeschkommando.py``.
"""

import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from infrastructure.database.models import UsageEvent
from repositories.usage_tracking_repository import UsageTrackingRepository
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

pytestmark = pytest.mark.integration


def _vor_tagen(datenbank, beitrag: uuid.UUID, tage: float) -> None:  # noqa: F811
    """Schiebt alle Ereignisse des Beitrags um ``tage`` in die Vergangenheit."""
    with datenbank.get_session() as s:
        s.execute(
            update(UsageEvent)
            .where(UsageEvent.content_id == beitrag)
            .values(timestamp=datetime.now(timezone.utc) - timedelta(days=tage))
        )


class TestNutzungJeFassung:
    def test_track_usage_zaehlt_je_fassung_und_insgesamt(self, datenbank):  # noqa: F811
        repo = UsageTrackingRepository(datenbank)
        beitrag = uuid.uuid4()

        for fassung in ["kurz", "kurz", "lang", "mittel", "kurz"]:
            assert repo.track_usage(beitrag, fassung=fassung)

        assert repo.get_usage_count(beitrag) == 5
        assert repo.get_nutzung_je_fassung_batch([beitrag]) == {
            str(beitrag): {
                "kurz": {"nutzung": 3, "letzte_7_tage": 3},
                "mittel": {"nutzung": 1, "letzte_7_tage": 1},
                "lang": {"nutzung": 1, "letzte_7_tage": 1},
            }
        }

    def test_track_usage_gleichzeitig_summe_je_fassung_gleich_gesamt(
        self, datenbank
    ):  # noqa: F811
        """Gleichzeitige Kopien zaehlen insgesamt wie je Fassung, keine geht verloren."""
        repo = UsageTrackingRepository(datenbank)
        beitrag = uuid.uuid4()
        repo.track_usage(beitrag, fassung="kurz")
        start = threading.Barrier(8)

        def kopieren():
            start.wait()
            for _ in range(5):
                repo.track_usage(beitrag, fassung="kurz")

        faeden = [threading.Thread(target=kopieren) for _ in range(8)]
        for faden in faeden:
            faden.start()
        for faden in faeden:
            faden.join()

        je_fassung = repo.get_nutzung_je_fassung_batch([beitrag])[str(beitrag)]
        assert je_fassung["kurz"]["nutzung"] == 41
        assert repo.get_usage_count(beitrag) == 41

    def test_get_nutzung_je_fassung_batch_zuwachs_nur_letzte_7_tage(
        self, datenbank
    ):  # noqa: F811
        repo = UsageTrackingRepository(datenbank)
        beitrag = uuid.uuid4()
        repo.track_usage(beitrag, fassung="kurz")
        repo.track_usage(beitrag, fassung="kurz")
        _vor_tagen(datenbank, beitrag, 8)
        repo.track_usage(beitrag, fassung="kurz")

        je_fassung = repo.get_nutzung_je_fassung_batch([beitrag])

        assert je_fassung[str(beitrag)]["kurz"] == {"nutzung": 3, "letzte_7_tage": 1}

    def test_get_nutzung_je_fassung_batch_summe_ueberdauert_die_ereignisse(
        self, datenbank
    ):  # noqa: F811
        repo = UsageTrackingRepository(datenbank)
        beitrag = uuid.uuid4()
        repo.track_usage(beitrag, fassung="lang")
        _vor_tagen(datenbank, beitrag, 100)

        repo.cleanup_old_events(days_to_keep=90)

        assert repo.get_nutzung_je_fassung_batch([beitrag]) == {
            str(beitrag): {"lang": {"nutzung": 1, "letzte_7_tage": 0}}
        }

    def test_get_nutzung_je_fassung_batch_ohne_fassung_nicht_dabei(
        self, datenbank
    ):  # noqa: F811
        repo = UsageTrackingRepository(datenbank)
        bild, ungenutzt = uuid.uuid4(), uuid.uuid4()
        repo.track_usage(bild)

        je_fassung = repo.get_nutzung_je_fassung_batch([bild, ungenutzt])

        assert repo.get_usage_count(bild) == 1
        assert je_fassung == {str(bild): {}, str(ungenutzt): {}}

    def test_get_nutzung_je_fassung_batch_leere_liste(self, datenbank):  # noqa: F811
        assert UsageTrackingRepository(datenbank).get_nutzung_je_fassung_batch([]) == {}
