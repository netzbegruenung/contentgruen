"""Die Entscheidung ueber eine Dublette, gleich fuer Kommentar und Hintergrundinfo."""

import uuid
from types import SimpleNamespace

import pytest

from dtos.beitrag import VorhandenDto
from services.content.base_content_service import Dublettenpruefung
from services.dublette import (
    Dublette,
    VorhandenWeg,
    entscheidung_anwenden,
    ist_gezeigter,
)


def _vorhanden(autor="person-1", titel="Vorhandener Titel"):
    return SimpleNamespace(id=uuid.uuid4(), original_author=autor, title=titel)


class TestIstGezeigter:
    def test_gleiche_id_auch_als_text(self):
        vorhanden = _vorhanden()
        assert ist_gezeigter(vorhanden, vorhanden.id)
        assert ist_gezeigter(vorhanden, str(vorhanden.id))

    def test_andere_id_oder_nichts(self):
        vorhanden = _vorhanden()
        assert not ist_gezeigter(vorhanden, uuid.uuid4())
        assert not ist_gezeigter(vorhanden, None)
        assert not ist_gezeigter(None, vorhanden.id)


class TestEntscheidungAnwenden:
    def test_ohne_entscheidung_bleibt_die_pruefung(self):
        pruefung = Dublettenpruefung(vorhanden=_vorhanden(), aehnlichster=None)
        assert entscheidung_anwenden(pruefung, None, None) is pruefung

    def test_trotz_des_gezeigten_gilt_keiner_als_vorhanden(self):
        vorhanden = _vorhanden()
        aehnlichster = _vorhanden()
        pruefung = Dublettenpruefung(vorhanden=vorhanden, aehnlichster=aehnlichster)
        ergebnis = entscheidung_anwenden(pruefung, vorhanden.id, None)
        assert ergebnis == Dublettenpruefung(vorhanden=None, aehnlichster=aehnlichster)

    def test_trotz_eines_anderen_bleibt_der_vorhandene(self):
        pruefung = Dublettenpruefung(vorhanden=_vorhanden(), aehnlichster=None)
        assert entscheidung_anwenden(pruefung, uuid.uuid4(), None) is pruefung

    def test_nehmen_ohne_vorhandenen_wirft(self):
        pruefung = Dublettenpruefung(vorhanden=None, aehnlichster=None)
        with pytest.raises(VorhandenWeg):
            entscheidung_anwenden(pruefung, None, uuid.uuid4())

    def test_nehmen_mit_vorhandenem_bleibt(self):
        vorhanden = _vorhanden()
        pruefung = Dublettenpruefung(vorhanden=vorhanden, aehnlichster=None)
        assert entscheidung_anwenden(pruefung, None, vorhanden.id) is pruefung


class TestDublette:
    def test_ohne_vorhandenen_keine(self):
        assert Dublette.aus(None, "person-1", None) is None

    def test_fremder_wird_nie_genommen(self):
        vorhanden = _vorhanden(autor="person-2")
        dublette = Dublette.aus(vorhanden, "person-1", vorhanden.id)
        assert dublette.eigen is False
        assert dublette.genommen is False

    def test_eigener_nur_genommen_wenn_gezeigt_gewaehlt(self):
        vorhanden = _vorhanden()
        assert Dublette.aus(vorhanden, "person-1", None).genommen is False
        assert Dublette.aus(vorhanden, "person-1", uuid.uuid4()).genommen is False
        assert Dublette.aus(vorhanden, "person-1", vorhanden.id).genommen is True

    def test_antwort_nennt_titel_und_eigen(self):
        dublette = Dublette.aus(_vorhanden(autor="person-2"), "person-1", None)
        antwort = VorhandenDto.aus(dublette.vorhanden, dublette.eigen)
        assert antwort.titel == "Vorhandener Titel"
        assert antwort.eigen is False
