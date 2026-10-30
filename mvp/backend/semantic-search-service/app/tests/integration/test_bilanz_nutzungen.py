"""
Nutzungen je Tag fuer die Bilanz (#467) gegen ein echtes PostgreSQL.

K2 der Bilanz zaehlt Nutzungsereignisse je Woche, nicht die Gesamtzaehler der
Beitraege. Gezaehlt wird je UTC-Tag; die Wochen bildet services/bilanz_service.py.
Wegwerf-Schema aus der Fixture ``datenbank`` von ``test_loeschkommando.py``.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import update

from infrastructure.database.models import UsageEvent
from repositories.usage_tracking_repository import UsageTrackingRepository
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

pytestmark = pytest.mark.integration


def _am(datenbank, beitrag: uuid.UUID, zeitpunkt: datetime) -> None:  # noqa: F811
    with datenbank.get_session() as s:
        s.execute(
            update(UsageEvent)
            .where(UsageEvent.content_id == beitrag, UsageEvent.timestamp > zeitpunkt)
            .values(timestamp=zeitpunkt)
        )


class TestNutzungenJeTag:
    def test_get_nutzungen_je_tag_zaehlt_ereignisse_je_utc_tag(
        self, datenbank
    ):  # noqa: F811
        repo = UsageTrackingRepository(datenbank)
        frueh, spaet = uuid.uuid4(), uuid.uuid4()
        for _ in range(3):
            repo.track_usage(frueh)
        repo.track_usage(spaet)
        # 23:30 UTC ist in Berlin schon der naechste Tag; zaehlen soll der UTC-Tag.
        _am(datenbank, frueh, datetime(2026, 10, 20, 23, 30, tzinfo=timezone.utc))
        _am(datenbank, spaet, datetime(2026, 10, 21, 0, 10, tzinfo=timezone.utc))

        je_tag = repo.get_nutzungen_je_tag(date(2026, 10, 19), date(2026, 10, 25))

        assert je_tag == {date(2026, 10, 20): 3, date(2026, 10, 21): 1}

    def test_get_nutzungen_je_tag_grenzen_eingeschlossen(self, datenbank):  # noqa: F811
        repo = UsageTrackingRepository(datenbank)
        tage = [
            date(2026, 10, 18),
            date(2026, 10, 19),
            date(2026, 10, 25),
            date(2026, 10, 26),
        ]
        for tag in tage:
            beitrag = uuid.uuid4()
            repo.track_usage(beitrag)
            _am(
                datenbank,
                beitrag,
                datetime(tag.year, tag.month, tag.day, 12, tzinfo=timezone.utc),
            )

        je_tag = repo.get_nutzungen_je_tag(date(2026, 10, 19), date(2026, 10, 25))

        assert je_tag == {date(2026, 10, 19): 1, date(2026, 10, 25): 1}

    @pytest.mark.parametrize("zeitzone", ["Pacific/Kiritimati", "Pacific/Pago_Pago"])
    def test_get_nutzungen_je_tag_unabhaengig_von_der_zeitzone(
        self, datenbank, zeitzone
    ):  # noqa: F811
        beitrag = uuid.uuid4()
        UsageTrackingRepository(datenbank).track_usage(beitrag)
        # 10:30 UTC ist in Kiritimati (UTC+14) schon der 21., in Pago Pago (UTC-11)
        # noch der 19.; zaehlen soll in beiden der UTC-Tag.
        _am(datenbank, beitrag, datetime(2026, 10, 20, 10, 30, tzinfo=timezone.utc))

        with datenbank.mit_zeitzone(zeitzone) as in_zone:
            je_tag = UsageTrackingRepository(in_zone).get_nutzungen_je_tag(
                date(2026, 10, 20), date(2026, 10, 20)
            )

        assert je_tag == {date(2026, 10, 20): 1}


def _metrics_service(datenbank):  # noqa: F811
    from services.metrics_service import MetricsService

    with patch(
        "services.metrics_service.get_app_database", return_value=datenbank
    ), patch("services.metrics_service.get_search_tracking_repository"), patch(
        "services.metrics_service.get_usage_repository"
    ):
        return MetricsService()


class TestUsageTrend:
    """usage-trend zaehlte die Gesamtzaehler der zuletzt genutzten Beitraege (#467)."""

    def test_get_usage_counter_trend_zaehlt_nutzungen_im_zeitraum(
        self, datenbank
    ):  # noqa: F811
        repo = UsageTrackingRepository(datenbank)
        alt = uuid.uuid4()
        for _ in range(10):
            repo.track_usage(alt)
        # Zehnmal vor drei Wochen genutzt, dann noch einmal diese Woche.
        _am(datenbank, alt, datetime.now(timezone.utc) - timedelta(days=21))
        repo.track_usage(alt)
        neu = uuid.uuid4()
        repo.track_usage(neu)
        repo.track_usage(neu)
        _am(datenbank, neu, datetime.now(timezone.utc) - timedelta(days=9))

        diese, vorige = _metrics_service(datenbank).get_usage_counter_trend(weeks=2)

        assert diese["usage_count"] == 1
        assert vorige["usage_count"] == 2
