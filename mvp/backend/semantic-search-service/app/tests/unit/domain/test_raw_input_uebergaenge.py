"""
Die Statuswechsel des Destillier-Ablaufs festnageln.

Kein Lock, Duplikate erlaubt: deshalb darf processed auch aus processed kommen
(ein zweiter Beitrag aus demselben Einwurf) und ein wiederholter Aufruf nie
scheitern. Verworfenes darf von anderen trotzdem destilliert werden.
"""

import pytest

from domain.models.raw_input import RawInputStatus, uebergang_erlaubt

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
            (IN_PROGRESS, PROCESSED),
            (IN_PROGRESS, DISCARDED),
        ],
    )
    def test_uebergang_nicht_erlaubt(self, von, nach):
        assert uebergang_erlaubt(von, nach) is False
