"""
Unit tests for the usage cleanup service configuration.

Die Werte kommen ueber die echte Umgebungsvariable in ein frisches Settings-Objekt,
damit der ganze Weg Env -> Settings-Feld -> Service geprueft ist. Frueher las der
Service Grossbuchstaben-Attribute, die es nicht gibt, und fiel still auf die
Defaults zurueck.
"""

from unittest.mock import Mock, patch
import pytest

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
    with patch.object(usage_cleanup_service, "get_usage_service", return_value=Mock()):
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


class TestSuchenOhneTrefferAufraeumen:
    """Der taegliche Lauf loescht auch alte Wochen der Suchen ohne Treffer."""

    def test_taeglicher_lauf_loescht_wochen_vor_der_aufbewahrungsgrenze(
        self, suchen_ohne_treffer_ohne_datenbank
    ):
        with patch.object(
            usage_cleanup_service, "get_usage_service", return_value=Mock()
        ), patch.object(
            usage_cleanup_service,
            "aufbewahrungsgrenze",
            return_value="grenze",
        ):
            usage_cleanup_service.UsageCleanupService().cleanup_old_data()

        suchen_ohne_treffer_ohne_datenbank.loeschen_vor.assert_called_once_with(
            "grenze"
        )
