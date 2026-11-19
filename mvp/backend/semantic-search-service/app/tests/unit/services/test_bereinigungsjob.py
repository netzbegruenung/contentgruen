"""
Unit tests for the configuration of the Bereinigungsjob.

Die Werte kommen ueber die echte Umgebungsvariable in ein frisches Settings-Objekt,
damit der ganze Weg Env -> Settings-Feld -> Service geprueft ist. Frueher las der
Service Grossbuchstaben-Attribute, die es nicht gibt, und fiel still auf die
Defaults zurueck.
"""

from unittest.mock import Mock, patch
import pytest

from api.v1.usage import CleanupStatusResponse
from core.config import Settings
from services.cleanup import bereinigungsjob


@pytest.fixture
def settings_from_env(monkeypatch):
    """Baut Settings aus der Umgebung und setzt den globalen Service zurueck."""

    def build(**env):
        for name, value in env.items():
            monkeypatch.setenv(f"SEMANTIC_SEARCH_{name}", value)
        monkeypatch.setattr(bereinigungsjob, "settings", Settings())

    monkeypatch.setattr(bereinigungsjob, "_bereinigungsjob", None)
    with patch.object(bereinigungsjob, "get_usage_service", return_value=Mock()):
        yield build


class TestBereinigungsjobSettings:
    """Die Cleanup-Einstellungen aus core/config.py kommen im Service an."""

    def test_get_bereinigungsjob_retention_from_env(self, settings_from_env):
        settings_from_env(USAGE_RETENTION_DAYS="30")

        service = bereinigungsjob.get_bereinigungsjob()

        assert service.retention_days == 30

    def test_get_bereinigungsjob_explicit_retention_wins(self, settings_from_env):
        settings_from_env(USAGE_RETENTION_DAYS="30")

        service = bereinigungsjob.get_bereinigungsjob(retention_days=7)

        assert service.retention_days == 7

    def test_get_status_ohne_frist_der_suchereignisse(self, settings_from_env):
        """Suchereignisse verdichtet seit #495 der Task der Loeschfristen am Tagesende."""
        settings_from_env(SEARCH_EVENT_RETENTION_DAYS="120")

        status = bereinigungsjob.get_bereinigungsjob().get_status()

        assert "search_event_retention_days" not in status
        # Ueber das Antwortmodell von GET /usage/cleanup/status.
        assert CleanupStatusResponse(**status).retention_days == 90

    def test_bereinigungsjob_starten_zur_eingestellten_zeit(self, settings_from_env):
        settings_from_env(CLEANUP_HOUR="4", CLEANUP_MINUTE="15")

        with patch.object(
            bereinigungsjob.Bereinigungsjob, "start_scheduled_cleanup"
        ) as start:
            bereinigungsjob.bereinigungsjob_starten()

        start.assert_called_once_with(hour=4, minute=15)

    def test_start_ohne_job_mit_dem_neuen_schalter(self, settings_from_env):
        settings_from_env(ENABLE_BEREINIGUNGSJOB="false")

        with patch.object(
            bereinigungsjob.Bereinigungsjob, "start_scheduled_cleanup"
        ) as start:
            bereinigungsjob.bereinigungsjob_starten()

        start.assert_not_called()
        assert bereinigungsjob._bereinigungsjob is None

    def test_der_neue_schalter_geht_dem_frueheren_vor(self, settings_from_env):
        settings_from_env(ENABLE_BEREINIGUNGSJOB="true", ENABLE_USAGE_CLEANUP="false")

        assert bereinigungsjob.settings.enable_bereinigungsjob is True

    def test_ohne_praefix_schaltet_nichts_ab(self, settings_from_env, monkeypatch):
        """Nur die Namen mit SEMANTIC_SEARCH_ gelten, keine fremde Variable."""
        monkeypatch.setenv("ENABLE_BEREINIGUNGSJOB", "false")
        settings_from_env()

        assert bereinigungsjob.settings.enable_bereinigungsjob is True

    def test_per_feldname_setzbar(self):
        assert Settings(enable_bereinigungsjob=False).enable_bereinigungsjob is False

    def test_start_ohne_job_mit_dem_frueheren_schalter(self, settings_from_env):
        """Ein im Betrieb gesetztes ENABLE_USAGE_CLEANUP=false gilt weiter."""
        settings_from_env(ENABLE_USAGE_CLEANUP="false")

        with patch.object(
            bereinigungsjob.Bereinigungsjob, "start_scheduled_cleanup"
        ) as start:
            bereinigungsjob.bereinigungsjob_starten()

        start.assert_not_called()
        assert bereinigungsjob._bereinigungsjob is None


class TestBereinigungsjobOhneSuchereignisse:
    """Suchereignisse fasst der Bereinigungsjob seit #495 nicht mehr an."""

    def test_cleanup_old_data_loescht_nur_nutzungsereignisse(self, settings_from_env):
        settings_from_env(USAGE_RETENTION_DAYS="60")
        service = bereinigungsjob.get_bereinigungsjob()
        service.usage_service.cleanup_old_events.return_value = 4

        assert service.cleanup_old_data() == 4
        service.usage_service.cleanup_old_events.assert_called_once_with(60)
        assert not hasattr(service, "search_repository")
