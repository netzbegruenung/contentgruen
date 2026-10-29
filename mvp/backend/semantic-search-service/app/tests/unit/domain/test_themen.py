"""
Unit-Tests fuer die Themenliste (domain/themen.json): die feste, kurze Liste, mit
der Aussagen geordnet werden, und die Pruefung einer Zuordnung (hoechstens zwei
Themen, nur aus der Liste).
"""

import pytest

from domain.themen import (
    HOECHSTENS_JE_AUSSAGE,
    THEMEN,
    ThemaUngueltig,
    themen_pruefen,
)

pytestmark = pytest.mark.unit


def test_liste_ist_kurz_und_eindeutig():
    schluessel = [t.schluessel for t in THEMEN]
    assert 8 <= len(THEMEN) <= 15
    assert len(set(schluessel)) == len(schluessel)
    assert len({t.name for t in THEMEN}) == len(THEMEN)


def test_schluessel_sind_kleingeschrieben_mit_bindestrichen():
    for thema in THEMEN:
        assert thema.schluessel.replace("-", "").isalpha()
        assert thema.schluessel == thema.schluessel.lower()
        assert thema.name.strip() == thema.name and thema.name


def test_pruefen_laesst_keine_bis_zwei_themen_durch():
    erstes, zweites = THEMEN[0].schluessel, THEMEN[1].schluessel

    assert themen_pruefen([]) == []
    assert themen_pruefen([erstes]) == [erstes]
    assert themen_pruefen([erstes, zweites]) == [erstes, zweites]
    assert HOECHSTENS_JE_AUSSAGE == 2


def test_pruefen_entfernt_doppelte():
    erstes = THEMEN[0].schluessel
    assert themen_pruefen([erstes, erstes]) == [erstes]


def test_pruefen_weist_drei_themen_ab():
    drei = [t.schluessel for t in THEMEN[:3]]
    with pytest.raises(ThemaUngueltig):
        themen_pruefen(drei)


def test_pruefen_weist_freie_schlagworte_ab():
    with pytest.raises(ThemaUngueltig):
        themen_pruefen(["heizungsgesetz"])
