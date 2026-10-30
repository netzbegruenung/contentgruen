"""
Pruefwerte fuer die entdoppelte Nutzung (#352): eine Nutzung je Person (Besucher:
Sitzung), Beitrag und Tag, ohne festzuhalten, wer was genutzt hat.
"""

import uuid
from datetime import datetime, timezone

from services.entdoppelung import paar_pruefwert, pruefwert

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


def test_pruefwert_besucher_ueber_sitzung():
    assert pruefwert(None, "sitzung-1", BEITRAG, MORGENS) == pruefwert(
        None, "sitzung-1", BEITRAG, ABENDS
    )
    assert pruefwert(None, "sitzung-1", BEITRAG, MORGENS) != pruefwert(
        None, "sitzung-2", BEITRAG, MORGENS
    )


def test_pruefwert_ohne_person_und_sitzung_keiner():
    assert pruefwert(None, None, BEITRAG, MORGENS) is None
    assert pruefwert("anonymous", None, BEITRAG, MORGENS) is None


def test_pruefwert_enthaelt_weder_kennung_noch_beitrag():
    wert = pruefwert("kim-1", None, BEITRAG, MORGENS)

    assert "kim-1" not in wert
    assert str(BEITRAG) not in wert


def test_paar_pruefwert_hat_richtung():
    assert paar_pruefwert("kim-1", "bo-2") != paar_pruefwert("bo-2", "kim-1")


def test_paar_pruefwert_bleibt_ueber_tage_gleich():
    """Muster ueber mehrere Tage: der Wert muss das Fenster ueberdauern."""
    assert paar_pruefwert("kim-1", "bo-2") == paar_pruefwert("kim-1", "bo-2")
    assert paar_pruefwert("kim-1", "bo-2") != paar_pruefwert("kim-1", "lea-3")
