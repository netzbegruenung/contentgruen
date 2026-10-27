"""
Meine Einwuerfe gegen ein echtes PostgreSQL: der Filter auf den Einwerfer.

Die Unit-Tests pruefen nur, dass ``submitted_by`` als Bedingung ankommt; hier zeigt
sich, dass fremde und herrenlose Einwuerfe wirklich fehlen und Zaehlung und
Reihenfolge zur Seite passen. Wegwerf-Schema aus der Fixture ``datenbank`` von
``test_loeschkommando.py``; woher PostgreSQL kommt, steht in ``postgres.py``.
"""

from datetime import datetime, timedelta, timezone

import pytest

from infrastructure.database.models import RawInput
from repositories.raw_input_repository import RawInputRepository
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

EINWERFER = "einwerfer"
ANDERE = "andere-person"

pytestmark = pytest.mark.integration


@pytest.fixture
def einwuerfe(datenbank):  # noqa: F811
    """Drei eigene (aelteste zuerst angelegt), ein fremder, ein herrenloser."""
    beginn = datetime(2026, 10, 1, tzinfo=timezone.utc)
    with datenbank.get_session() as s:
        for tag, (von, status) in enumerate(
            [
                (EINWERFER, "open"),
                (ANDERE, "open"),
                (EINWERFER, "discarded"),
                (None, "open"),
                (EINWERFER, "processed"),
            ]
        ):
            s.add(
                RawInput(
                    content=f"Fundstueck {tag}",
                    submitted_by=von,
                    status=status,
                    created_at=beginn + timedelta(days=tag),
                )
            )


@pytest.mark.usefixtures("einwuerfe")
class TestMeineEinwuerfe:
    def test_nur_die_eigenen_neueste_zuerst(self, datenbank):  # noqa: F811
        zeilen = RawInputRepository(datenbank).get_all(
            current_user=EINWERFER, submitted_by=EINWERFER
        )

        assert [z["content"] for z in zeilen] == [
            "Fundstueck 4",
            "Fundstueck 2",
            "Fundstueck 0",
        ]
        assert {z["submitted_by"] for z in zeilen} == {EINWERFER}

    def test_zaehlung_passt_zur_liste(self, datenbank):  # noqa: F811
        repository = RawInputRepository(datenbank)

        assert repository.count(submitted_by=EINWERFER) == 3
        assert repository.count(submitted_by=ANDERE) == 1
        assert repository.count() == 5

    def test_seite_zwei_setzt_fort(self, datenbank):  # noqa: F811
        zweite = RawInputRepository(datenbank).get_all(
            limit=2, offset=2, current_user=EINWERFER, submitted_by=EINWERFER
        )

        assert [z["content"] for z in zweite] == ["Fundstueck 0"]
