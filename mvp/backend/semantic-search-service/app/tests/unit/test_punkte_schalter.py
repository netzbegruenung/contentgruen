"""
punkte_aktiv erst nach #668 (Review zu #670): Punkte und Meilensteine haengen seit dem
Wortlaut 2026-11-13 an einer eigenen, freiwilligen Einwilligung. Bis die gebaut ist,
startet der Dienst mit eingeschalteten Punkten nicht.
"""

import pytest

from core import config
from core.config import Settings, punkte_schalter_pruefen


def test_punkte_standard_aus():
    assert Settings().punkte_aktiv is False


def test_ohne_eigene_einwilligung_startet_der_dienst_mit_punkten_nicht(monkeypatch):
    monkeypatch.setattr(config, "PUNKTE_EINWILLIGUNG_GEBAUT", False)

    with pytest.raises(RuntimeError, match="#668"):
        punkte_schalter_pruefen(Settings(punkte_aktiv=True))
    punkte_schalter_pruefen(Settings(punkte_aktiv=False))


def test_mit_eigener_einwilligung_darf_er_an(monkeypatch):
    monkeypatch.setattr(config, "PUNKTE_EINWILLIGUNG_GEBAUT", True)

    punkte_schalter_pruefen(Settings(punkte_aktiv=True))
