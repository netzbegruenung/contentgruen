"""
Datenbankfehler im Log nennen keine gebundenen Parameter.

Eine SQLAlchemy-Fehlermeldung enthaelt sonst die Werte der Anweisung, beim
Bearbeiten einer Meldung etwa reviewed_by, also die Kennung des Admins.
"""

import pytest
from sqlalchemy import text

from infrastructure.database.connection import AppDatabase

ADMIN_KENNUNG = "admin.person@example.org"


@pytest.mark.unit
def test_fehlermeldung_nennt_keine_parameter(monkeypatch):
    monkeypatch.delenv("APP_DATABASE_ECHO", raising=False)
    datenbank = AppDatabase("sqlite://")

    with pytest.raises(Exception) as fehler:
        with datenbank.engine.connect() as verbindung:
            verbindung.execute(
                text("UPDATE fehlt SET reviewed_by = :wer"), {"wer": ADMIN_KENNUNG}
            )

    assert ADMIN_KENNUNG not in str(fehler.value)
