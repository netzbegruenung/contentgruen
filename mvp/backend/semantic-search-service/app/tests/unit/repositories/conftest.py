"""
Gemeinsame Fixtures der Repository-Tests mit gemockter App-Datenbank.

``session`` ist eine gemockte SQLAlchemy-Session als Context-Manager, ``app_datenbank``
die App-Datenbank, die sie ausgibt. Das Repository selbst baut jede Testdatei, weil
``get_app_database`` je Repository-Modul gepatcht wird:

    @pytest.fixture
    def repository(app_datenbank):
        with patch("repositories.<modul>.get_app_database", return_value=app_datenbank):
            yield <Repository>()
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def session():
    """Eine gemockte SQLAlchemy-Session als Context-Manager."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session


@pytest.fixture
def app_datenbank(session):
    """Die App-Datenbank, deren ``get_session()`` die gemockte Session liefert."""
    datenbank = MagicMock()
    datenbank.get_session.return_value = session
    return datenbank
