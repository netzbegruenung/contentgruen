"""
MVP-Dashboard ohne feste Zielwerte (#467, Entscheidung in #417).

Die Kennzahlen selbst kommen aus Repositories und SQL; die sind hier ersetzt.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from services.metrics_service import MetricsService

pytestmark = pytest.mark.unit


@pytest.fixture
def service():
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 42
    db = MagicMock()

    @contextmanager
    def get_session():
        yield session

    db.get_session = get_session
    with patch("services.metrics_service.get_app_database", return_value=db), patch(
        "services.metrics_service.get_search_tracking_repository"
    ), patch("services.metrics_service.get_usage_repository"):
        service = MetricsService()
    service.get_daily_active_users = lambda: 3
    service.get_searches_per_user = lambda days: {"average": 1.5}
    service.get_content_created_per_week = lambda weeks: [{"content_created": 4}]
    service.get_usage_counter_trend = lambda weeks: [
        {"usage_count": 9},
        {"usage_count": 2},
    ]
    service.get_helpful_rate = lambda days: {
        "helpful_rate": 50.0,
        "like_count": 1,
        "dislike_count": 1,
        "total_votes": 2,
    }
    return service


def test_get_mvp_dashboard_metrics_ohne_zielwerte(service):
    metrics = service.get_mvp_dashboard_metrics()

    assert [k for k in metrics if k.endswith(("_goal", "_met"))] == []
    assert metrics["daily_active_users"] == 3
    assert metrics["usage_counter_current_week"] == 9
    assert metrics["usage_counter_previous_week"] == 2
    assert metrics["usage_counter_total"] == 42
