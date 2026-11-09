"""
Meilensteine (#351): Schwellen bei der Wirkung der eigenen Beitraege und bei der
Unterstuetzungsarbeit; erreicht ab der Schwelle.
"""

from domain.meilensteine import (
    UNTERSTUETZUNG,
    WIRKUNG,
    Meilensteindaten,
    meilensteine_berechnen,
)


def _erreicht(daten: Meilensteindaten) -> list:
    return [m.kennung for m in meilensteine_berechnen(daten) if m.erreicht]


def test_ohne_wirkung_kein_meilenstein_erreicht():
    meilensteine = meilensteine_berechnen(Meilensteindaten())

    assert [m.kennung for m in meilensteine] == [
        "nutzung-1",
        "nutzung-10",
        "nutzung-50",
        "nutzung-100",
        "zustimmung-1",
        "ausformuliert-10",
        "eingeworfen-10",
    ]
    assert not any(m.erreicht for m in meilensteine)
    assert all(m.stand == 0 for m in meilensteine)


def test_nutzung_genau_an_der_schwelle_erreicht():
    assert _erreicht(Meilensteindaten(nutzungen=1)) == ["nutzung-1"]
    assert _erreicht(Meilensteindaten(nutzungen=9)) == ["nutzung-1"]
    assert _erreicht(Meilensteindaten(nutzungen=50)) == [
        "nutzung-1",
        "nutzung-10",
        "nutzung-50",
    ]


def test_erste_zustimmung():
    assert _erreicht(Meilensteindaten(zustimmungen=1)) == ["zustimmung-1"]


def test_unterstuetzungsarbeit_ab_zehn():
    daten = Meilensteindaten(
        einwuerfe_ausformuliert=10, eigene_einwuerfe_von_anderen_ausformuliert=9
    )

    assert _erreicht(daten) == ["ausformuliert-10"]


def test_stand_und_art_je_meilenstein():
    meilensteine = {
        m.kennung: m
        for m in meilensteine_berechnen(
            Meilensteindaten(nutzungen=12, eigene_einwuerfe_von_anderen_ausformuliert=3)
        )
    }

    assert meilensteine["nutzung-50"].stand == 12
    assert meilensteine["nutzung-50"].schwelle == 50
    assert meilensteine["nutzung-50"].art == WIRKUNG
    assert meilensteine["eingeworfen-10"].stand == 3
    assert meilensteine["eingeworfen-10"].art == UNTERSTUETZUNG
