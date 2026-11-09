"""
Wortlaute der Zustimmung zur Sichtbarkeit (#351): jede Kennung bleibt bekannt, die
aktuelle Frage ist kurz und hat ein "Mehr dazu" mit den Hinweisen.
"""

from domain.abzeichen_sichtbarkeit import AKTUELLER_WORTLAUT, MEHR_DAZU, WORTLAUTE


def test_jede_kennung_hat_text_und_mehr_dazu():
    assert set(WORTLAUTE) == set(MEHR_DAZU)
    assert AKTUELLER_WORTLAUT in WORTLAUTE


def test_fruehere_kennung_bleibt_bekannt():
    assert "2026-11-09" in WORTLAUTE


def test_aktuelle_frage_kurz_mit_hinweisen_unter_mehr_dazu():
    frage = WORTLAUTE[AKTUELLER_WORTLAUT]
    mehr = MEHR_DAZU[AKTUELLER_WORTLAUT]

    assert "Besucher sehen es nie" in frage
    assert "„Meine Beiträge“" in frage
    assert "Screenshot" not in frage
    assert "nicht nur Mitglieder" in mehr
    assert "Screenshot" in mehr
    assert "Datenschutzerklärung" in mehr
