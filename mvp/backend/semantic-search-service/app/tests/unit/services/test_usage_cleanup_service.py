"""
Unit tests for the usage cleanup service configuration.

Die Werte kommen ueber die echte Umgebungsvariable in ein frisches Settings-Objekt,
damit der ganze Weg Env -> Settings-Feld -> Service geprueft ist. Frueher las der
Service Grossbuchstaben-Attribute, die es nicht gibt, und fiel still auf die
Defaults zurueck.
"""

from unittest.mock import Mock, patch
import pytest
from pydantic import ValidationError

from api.v1.usage import CleanupStatusResponse
from core.config import Settings
from services.cleanup import usage_cleanup_service


@pytest.fixture
def settings_from_env(monkeypatch):
    """Baut Settings aus der Umgebung und setzt den globalen Service zurueck."""

    def build(**env):
        for name, value in env.items():
            monkeypatch.setenv(f"SEMANTIC_SEARCH_{name}", value)
        monkeypatch.setattr(usage_cleanup_service, "settings", Settings())

    monkeypatch.setattr(usage_cleanup_service, "_cleanup_service", None)
    with patch.object(
        usage_cleanup_service, "get_usage_service", return_value=Mock()
    ), patch.object(
        usage_cleanup_service, "get_search_tracking_repository", return_value=Mock()
    ):
        yield build


class TestUsageCleanupServiceSettings:
    """Die Cleanup-Einstellungen aus core/config.py kommen im Service an."""

    def test_get_cleanup_service_retention_from_env(self, settings_from_env):
        settings_from_env(USAGE_RETENTION_DAYS="30")

        service = usage_cleanup_service.get_cleanup_service()

        assert service.retention_days == 30

    def test_get_cleanup_service_explicit_retention_wins(self, settings_from_env):
        settings_from_env(USAGE_RETENTION_DAYS="30")

        service = usage_cleanup_service.get_cleanup_service(retention_days=7)

        assert service.retention_days == 7

    def test_get_cleanup_service_search_retention_from_env(self, settings_from_env):
        settings_from_env(SEARCH_EVENT_RETENTION_DAYS="120")

        service = usage_cleanup_service.get_cleanup_service()

        assert service.search_event_retention_days == 120

    def test_search_retention_default_is_90_days(self, settings_from_env):
        settings_from_env()

        service = usage_cleanup_service.get_cleanup_service()

        assert service.search_event_retention_days == 90

    @pytest.mark.parametrize("tage", ["89", "0", "-1"])
    def test_search_retention_unter_90_tagen_abgelehnt(self, settings_from_env, tage):
        with pytest.raises(ValidationError):
            settings_from_env(SEARCH_EVENT_RETENTION_DAYS=tage)

    def test_get_status_nennt_frist_der_suchereignisse(self, settings_from_env):
        settings_from_env(SEARCH_EVENT_RETENTION_DAYS="120")

        status = usage_cleanup_service.get_cleanup_service().get_status()

        # Ueber das Antwortmodell von GET /usage/cleanup/status, das unbekannte
        # Felder verwerfen wuerde.
        assert CleanupStatusResponse(**status).search_event_retention_days == 120

    def test_start_cleanup_scheduler_uses_configured_time(self, settings_from_env):
        settings_from_env(CLEANUP_HOUR="4", CLEANUP_MINUTE="15")

        with patch.object(
            usage_cleanup_service.UsageCleanupService, "start_scheduled_cleanup"
        ) as start:
            usage_cleanup_service.start_cleanup_scheduler()

        start.assert_called_once_with(hour=4, minute=15)

    def test_start_cleanup_scheduler_disabled(self, settings_from_env):
        settings_from_env(ENABLE_USAGE_CLEANUP="false")

        with patch.object(
            usage_cleanup_service.UsageCleanupService, "start_scheduled_cleanup"
        ) as start:
            usage_cleanup_service.start_cleanup_scheduler()

        start.assert_not_called()
        assert usage_cleanup_service._cleanup_service is None


class TestUsageCleanupServiceSuchereignisse:
    """Der Bereinigungsjob verdichtet alte Suchereignisse zu Tageszaehlern (#289)."""

    def test_cleanup_old_data_verdichtet_suchereignisse_mit_frist(
        self, settings_from_env
    ):
        settings_from_env(SEARCH_EVENT_RETENTION_DAYS="120")
        service = usage_cleanup_service.get_cleanup_service()

        service.cleanup_old_data()

        service.search_repository.verdichte_alte_suchereignisse.assert_called_once_with(
            120
        )

    def test_cleanup_old_data_mischt_abgeschlossene_tage_nach_dem_verdichten(
        self, settings_from_env
    ):
        """Erst verdichten, dann mischen: Was verdichtet wird, muss nicht mehr
        gemischt werden (#337)."""
        service = usage_cleanup_service.get_cleanup_service()
        repository = service.search_repository

        service.cleanup_old_data()

        assert [name for name, _, _ in repository.method_calls] == [
            "verdichte_alte_suchereignisse",
            "mische_abgeschlossene_tage",
        ]

    def test_cleanup_old_data_mischt_auch_bei_fehler_des_verdichtens(
        self, settings_from_env
    ):
        service = usage_cleanup_service.get_cleanup_service()
        service.search_repository.verdichte_alte_suchereignisse.side_effect = (
            RuntimeError("db weg")
        )

        service.cleanup_old_data()

        service.search_repository.mische_abgeschlossene_tage.assert_called_once_with()

    def test_cleanup_old_data_nutzung_bleibt_bei_fehler_des_mischens(
        self, settings_from_env
    ):
        service = usage_cleanup_service.get_cleanup_service()
        service.search_repository.mische_abgeschlossene_tage.side_effect = RuntimeError(
            "db weg"
        )
        service.usage_service.cleanup_old_events.return_value = 4

        assert service.cleanup_old_data() == 4

    def test_cleanup_old_data_nutzung_bleibt_bei_fehler_der_suchereignisse(
        self, settings_from_env
    ):
        settings_from_env(USAGE_RETENTION_DAYS="60")
        service = usage_cleanup_service.get_cleanup_service()
        service.search_repository.verdichte_alte_suchereignisse.side_effect = (
            RuntimeError("db weg")
        )
        service.usage_service.cleanup_old_events.return_value = 4

        assert service.cleanup_old_data() == 4
        service.usage_service.cleanup_old_events.assert_called_once_with(60)
