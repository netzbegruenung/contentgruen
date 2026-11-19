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


def test_die_eigene_einwilligung_ist_gebaut_und_passt_zum_schalter():
    """#668: Konstante an, und es gibt Wortlaut, Tabelle und Endpunkt dazu."""
    from api.v1.usage import router
    from domain.punkte_einwilligung import AKTUELLER_WORTLAUT, GELTENDE_WORTLAUTE
    from infrastructure.database.models import PunkteEinwilligungZeile

    assert config.PUNKTE_EINWILLIGUNG_GEBAUT is True
    assert AKTUELLER_WORTLAUT in GELTENDE_WORTLAUTE
    assert PunkteEinwilligungZeile.__tablename__ == "punkte_einwilligung"
    pfade = {(m, r.path) for r in router.routes for m in getattr(r, "methods", ())}
    assert ("GET", "/users/me/punkte-einwilligung") in pfade
    assert ("PUT", "/users/me/punkte-einwilligung") in pfade
    punkte_schalter_pruefen(Settings(punkte_aktiv=True))
