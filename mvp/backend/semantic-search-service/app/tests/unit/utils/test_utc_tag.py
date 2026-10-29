"""Unit-Tests fuer den UTC-Tag (utils/utc_tag.py)."""

from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest

import utils.utc_tag as modul
from utils.utc_tag import heute_utc, sekunden_bis_mitternacht

pytestmark = pytest.mark.unit


def test_sekunden_bis_mitternacht_rechnet_in_utc():
    jetzt = datetime(2026, 10, 28, 23, 0, tzinfo=timezone.utc)

    assert sekunden_bis_mitternacht(jetzt) == 3600


def test_heute_utc_nimmt_das_utc_datum_nicht_die_ortszeit():
    # 23:30 UTC am Sonntag ist in Berlin schon Montag; gezaehlt wird in UTC.
    spaet = datetime(2026, 11, 1, 23, 30, tzinfo=timezone.utc)
    with patch.object(modul, "datetime", wraps=datetime) as uhr:
        uhr.now.return_value = spaet
        assert heute_utc() == date(2026, 11, 1)
    uhr.now.assert_called_once_with(timezone.utc)
