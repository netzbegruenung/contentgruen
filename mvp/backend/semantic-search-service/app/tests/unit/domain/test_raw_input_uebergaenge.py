"""
Die Statuswechsel des Fangkorbs festnageln.

Kein Lock, Duplikate erlaubt: deshalb darf processed auch aus processed kommen
(ein zweiter Beitrag aus demselben Einwurf) und ein wiederholter Aufruf nie
scheitern. Verworfenes darf von anderen trotzdem destilliert werden.

open und in_progress sind kein Ziel eines Statuswechsels, sie ergeben sich aus
den gespeicherten Saetzen (``status_nach_satz``, ``status_ohne_saetze``).
"""

import pytest

from domain.models.raw_input import (
    RawInputStatus,
    status_nach_satz,
    status_ohne_saetze,
    uebergang_erlaubt,
)

OPEN = RawInputStatus.OPEN
IN_PROGRESS = RawInputStatus.IN_PROGRESS
PROCESSED = RawInputStatus.PROCESSED
DISCARDED = RawInputStatus.DISCARDED


@pytest.mark.unit
class TestUebergaenge:
    @pytest.mark.parametrize(
        "von, nach",
        [
            (OPEN, DISCARDED),
            (OPEN, PROCESSED),
            (IN_PROGRESS, PROCESSED),
            (IN_PROGRESS, DISCARDED),
            (DISCARDED, PROCESSED),
            (DISCARDED, DISCARDED),
            (PROCESSED, PROCESSED),
        ],
    )
    def test_uebergang_erlaubt(self, von, nach):
        assert uebergang_erlaubt(von, nach) is True

    @pytest.mark.parametrize(
        "von, nach",
        [
            (PROCESSED, DISCARDED),
            (PROCESSED, OPEN),
            (DISCARDED, OPEN),
            (OPEN, OPEN),
            (OPEN, IN_PROGRESS),
            (IN_PROGRESS, OPEN),
            (DISCARDED, IN_PROGRESS),
        ],
    )
    def test_uebergang_nicht_erlaubt(self, von, nach):
        assert uebergang_erlaubt(von, nach) is False


@pytest.mark.unit
class TestStandAusSaetzen:
    @pytest.mark.parametrize(
        "vorher, nachher",
        [
            (OPEN, IN_PROGRESS),
            (IN_PROGRESS, IN_PROGRESS),
            (DISCARDED, DISCARDED),
            (PROCESSED, PROCESSED),
        ],
    )
    def test_status_nach_satz(self, vorher, nachher):
        """Nur ein offener Einwurf wird durch einen Satz destilliert."""
        assert status_nach_satz(vorher) == nachher

    @pytest.mark.parametrize(
        "vorher, nachher",
        [
            (IN_PROGRESS, OPEN),
            (OPEN, OPEN),
            (DISCARDED, DISCARDED),
            (PROCESSED, PROCESSED),
        ],
    )
    def test_status_ohne_saetze(self, vorher, nachher):
        """Nur ein destillierter Einwurf faellt ohne Saetze zurueck auf offen."""
        assert status_ohne_saetze(vorher) == nachher
