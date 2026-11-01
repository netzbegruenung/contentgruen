"""
Gemeinsame Helfer der Integrationstests zu Suchereignissen (``search_events``): das
Repository auf eine Wegwerf-Datenbank statt auf die App-Datenbank. Die Tabelle legt
die Fixture ``suchereignisse_db`` in ``conftest.py`` an.
"""

from unittest.mock import patch

from repositories.search_tracking_repository import SearchTrackingRepository
from tests.integration.postgres import Datenbank


def suchtracking_repository(db: Datenbank) -> SearchTrackingRepository:
    """Das SearchTrackingRepository auf diese Datenbank."""
    with patch(
        "repositories.search_tracking_repository.get_app_database",
        return_value=db,
    ):
        return SearchTrackingRepository()
