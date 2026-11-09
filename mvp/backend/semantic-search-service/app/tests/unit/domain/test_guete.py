"""Die Rechnung der Güte (#427, domain/guete.py)."""

import pytest

from domain.guete import Guetegewichte, guete_berechnen

pytestmark = pytest.mark.unit

GEWICHTE = Guetegewichte(stimmen_ab=3, stimmen_gewicht_max=0.6, stimmen_halbwert=5)


def test_ohne_kriterien_und_ohne_stimmen_neu():
    guete = guete_berechnen(None, 0, 0, GEWICHTE)
    assert guete.wert is None
    assert guete.stimmen_zaehlen is False


def test_ohne_stimmen_gilt_der_kriterienanteil():
    assert guete_berechnen(7, 0, 0, GEWICHTE).wert == 7


def test_unter_der_mindestzahl_aendert_eine_stimme_nichts():
    # M5: Aus der Güte darf sich keine einzelne Stimme ablesen lassen.
    for hilfreich, nicht in [(1, 0), (0, 1), (2, 0), (1, 1), (0, 2)]:
        guete = guete_berechnen(6, hilfreich, nicht, GEWICHTE)
        assert guete.wert == 6
        assert guete.stimmen_zaehlen is False


def test_ab_der_mindestzahl_zaehlen_stimmen():
    guete = guete_berechnen(6, 10, 0, GEWICHTE)
    assert guete.stimmen_zaehlen is True
    assert guete.wert > 6


def test_ablehnung_senkt_aber_nie_unter_eins():
    assert guete_berechnen(6, 0, 20, GEWICHTE).wert < 6
    assert guete_berechnen(1, 0, 1000, GEWICHTE).wert == 1


def test_stimmen_tragen_hoechstens_ihre_obergrenze():
    # Viele Zustimmungen heben einen schwachen Text nicht ganz nach oben.
    assert guete_berechnen(1, 10_000, 0, GEWICHTE).wert <= 7


def test_ohne_kriterienanteil_zaehlen_die_stimmen_allein():
    assert guete_berechnen(None, 3, 0, GEWICHTE).wert == 10
    assert guete_berechnen(None, 2, 0, GEWICHTE).wert is None


def test_kleine_verbesserung_hebt_die_guete_auch_mit_stimmen():
    # Verneinung am Anfang entfernt: Kriterienanteil 7 -> 10 (Gewicht 3).
    vorher = guete_berechnen(7, 4, 1, GEWICHTE).wert
    nachher = guete_berechnen(10, 4, 1, GEWICHTE).wert
    assert nachher - vorher >= 2


@pytest.mark.parametrize("kriterien", range(1, 11))
def test_bleibt_zwischen_eins_und_zehn(kriterien):
    for hilfreich, nicht in [(0, 0), (3, 0), (0, 3), (50, 50), (500, 0)]:
        assert 1 <= guete_berechnen(kriterien, hilfreich, nicht, GEWICHTE).wert <= 10
