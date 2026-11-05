"""
Pruefwerte fuer die entdoppelte Nutzung (#352): eine Nutzung je Person (Besucher:
Tagespseudonym), Beitrag und Tag, ohne festzuhalten, wer was genutzt hat. Die
Schluessel liegen nur im Speicher (BanSe/todo#266, DSFA Risiko 2).
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import services.entdoppelung as entdoppelung
from core.config import settings
from services.entdoppelung import (
    MUSTER_FENSTER_TAGE,
    Fensterschluessel,
    paar_pruefwert,
    paar_pruefwerte_im_fenster,
    pruefwert,
)
from utils.besucher_pseudonym import Tagesschluessel

BEITRAG = uuid.UUID("11111111-1111-4111-8111-111111111111")
ANDERER = uuid.UUID("22222222-2222-4222-8222-222222222222")
MORGENS = datetime(2026, 10, 30, 8, tzinfo=timezone.utc)
ABENDS = datetime(2026, 10, 30, 22, tzinfo=timezone.utc)
FOLGETAG = datetime(2026, 10, 31, 8, tzinfo=timezone.utc)


def test_pruefwert_gleich_am_selben_tag():
    assert pruefwert("kim-1", None, BEITRAG, MORGENS) == pruefwert(
        "kim-1", None, BEITRAG, ABENDS
    )


def test_pruefwert_anders_am_naechsten_tag():
    assert pruefwert("kim-1", None, BEITRAG, MORGENS) != pruefwert(
        "kim-1", None, BEITRAG, FOLGETAG
    )


def test_pruefwert_anders_je_beitrag_und_person():
    basis = pruefwert("kim-1", None, BEITRAG, MORGENS)

    assert basis != pruefwert("kim-1", None, ANDERER, MORGENS)
    assert basis != pruefwert("bo-2", None, BEITRAG, MORGENS)


def test_pruefwert_besucher_ueber_besuchermerkmal():
    assert pruefwert(None, "anschluss-1|Browser", BEITRAG, MORGENS) == pruefwert(
        None, "anschluss-1|Browser", BEITRAG, ABENDS
    )
    assert pruefwert(None, "anschluss-1|Browser", BEITRAG, MORGENS) != pruefwert(
        None, "anschluss-2|Browser", BEITRAG, MORGENS
    )


def test_pruefwert_ohne_person_und_merkmal_keiner():
    assert pruefwert(None, None, BEITRAG, MORGENS) is None
    assert pruefwert("anonymous", None, BEITRAG, MORGENS) is None


def test_pruefwert_enthaelt_weder_kennung_noch_beitrag():
    wert = pruefwert("kim-1", None, BEITRAG, MORGENS)

    assert "kim-1" not in wert
    assert str(BEITRAG) not in wert


def test_pruefwert_nach_neustart_anders():
    """Der Schluessel liegt nur im Speicher: ein Neustart beginnt neu."""
    vorher = pruefwert("kim-1", None, BEITRAG, MORGENS)

    _neustart()

    assert pruefwert("kim-1", None, BEITRAG, ABENDS) != vorher


def test_pruefwert_ohne_bezug_zum_actor_hash_secret(monkeypatch):
    monkeypatch.setattr(settings, "actor_hash_secret", "eins")
    eins = pruefwert("kim-1", None, BEITRAG, MORGENS)
    paar_eins = paar_pruefwert("kim-1", "bo-2", MORGENS.date())

    monkeypatch.setattr(settings, "actor_hash_secret", "zwei")

    assert pruefwert("kim-1", None, BEITRAG, MORGENS) == eins
    assert paar_pruefwert("kim-1", "bo-2", MORGENS.date()) == paar_eins


def test_paar_pruefwert_hat_richtung():
    tag = MORGENS.date()
    assert paar_pruefwert("kim-1", "bo-2", tag) != paar_pruefwert("bo-2", "kim-1", tag)
    assert paar_pruefwert("kim-1", "bo-2", tag) != paar_pruefwert("kim-1", "lea-3", tag)


def test_paar_pruefwert_bleibt_im_fenster_vergleichbar():
    """
    Jeder Paar-Pruefwert der letzten sieben Tage (den heutigen eingeschlossen) ist
    unter den heutigen Vergleichswerten, ueber jeden Schluesselwechsel hinweg.
    """
    start = date(2026, 10, 1)
    gemerkt = {}
    for versatz in range(3 * MUSTER_FENSTER_TAGE):
        tag = start + timedelta(days=versatz)
        gemerkt[tag] = paar_pruefwert("kim-1", "bo-2", tag)
        vergleich = paar_pruefwerte_im_fenster("kim-1", "bo-2", tag)
        for zurueck in range(min(versatz + 1, MUSTER_FENSTER_TAGE)):
            assert gemerkt[tag - timedelta(days=zurueck)] in vergleich


def test_paar_pruefwert_nach_zwei_fenstern_nicht_mehr_herzustellen():
    """Spaetestens nach zwei Fenstern ist der Schluessel eines Werts verworfen."""
    tag = date(2026, 10, 1)
    alt = paar_pruefwert("kim-1", "bo-2", tag)

    spaeter = tag + timedelta(days=2 * MUSTER_FENSTER_TAGE)

    assert alt not in paar_pruefwerte_im_fenster("kim-1", "bo-2", spaeter)


def test_paar_pruefwert_nach_neustart_anders():
    tag = MORGENS.date()
    vorher = paar_pruefwert("kim-1", "bo-2", tag)

    _neustart()

    assert vorher not in paar_pruefwerte_im_fenster("kim-1", "bo-2", tag)


class TestFensterschluessel:
    def test_gleicher_schluessel_im_fenster_vorheriger_danach(self):
        schluessel = Fensterschluessel(tage=7)
        tag = date(2026, 10, 1)
        aktuell, _ = schluessel.fuer(tag)

        naechster, vorheriger = schluessel.fuer(tag + timedelta(days=7))

        assert vorheriger == aktuell
        assert naechster != aktuell

    def test_vergangenes_fenster_bekommt_einmalschluessel(self):
        schluessel = Fensterschluessel(tage=7)
        tag = date(2026, 10, 1)
        aktuell, _ = schluessel.fuer(tag + timedelta(days=7))

        alt, vorheriger = schluessel.fuer(tag - timedelta(days=7))

        assert alt != aktuell
        assert vorheriger is None


def _neustart():
    """Wie ein Neustart des Prozesses: die Schluessel im Speicher sind weg."""
    entdoppelung._NUTZUNG_SCHLUESSEL = Tagesschluessel()
    entdoppelung._PAAR_SCHLUESSEL = Fensterschluessel(tage=MUSTER_FENSTER_TAGE)
