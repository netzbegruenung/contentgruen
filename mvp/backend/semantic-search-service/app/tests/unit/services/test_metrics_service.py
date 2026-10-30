"""MetricsService: Stimmen von Startkonten zaehlen nicht in "War hilfreich" (#352)."""

from unittest.mock import patch

from services.metrics_service import MetricsService


def _service(startkonten: frozenset):
    with patch("services.metrics_service.get_search_tracking_repository"), patch(
        "services.metrics_service.get_usage_repository"
    ), patch("services.metrics_service.get_app_database") as db:
        service = MetricsService(startkonten)
    session = db.return_value.get_session.return_value.__enter__.return_value
    session.execute.return_value.fetchone.return_value = (3, 1, 4)
    return service, session


def test_get_helpful_rate_ohne_stimmen_der_startkonten():
    service, session = _service(frozenset({"start-9", "start-8"}))

    rate = service.get_helpful_rate()

    assert session.execute.call_args.args[1]["ausgenommen"] == ["start-8", "start-9"]
    assert rate["helpful_rate"] == 75.0


def test_get_helpful_rate_ohne_startkonten_nimmt_niemanden_aus():
    service, session = _service(frozenset())

    service.get_helpful_rate()

    assert session.execute.call_args.args[1]["ausgenommen"] == [""]
