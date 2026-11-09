"""
Das Meilenstein-Abzeichen am Anzeigenamen (#351): nur fuer Angemeldete, nur an
Beitraegen, nur fuer Personen, die der Dienst kennt (Zustimmung, Schalter).
"""

from typing import Optional

import pytest
from pydantic import BaseModel

from services import abzeichen_service as abzeichen_modul
from services.beitrag_fuer_aufrufer import AUSSAGE, Aufrufer, fuer_aufrufer

AUTORIN = "kim-1"
ANDERE = "bo-2"


class _Beitrag(BaseModel):
    original_author: Optional[str] = None
    autor_name: Optional[str] = None
    ist_eigener_beitrag: Optional[bool] = None
    autor_abzeichen: Optional[int] = None


class _Aussage(BaseModel):
    original_author: Optional[str] = None
    autor_name: Optional[str] = None
    ist_eigene_aussage: Optional[bool] = None
    autor_abzeichen: Optional[int] = None


class _Dienst:
    def abzeichen(self, kennungen):
        return {k: 3 for k in kennungen if k == AUTORIN}


@pytest.fixture(autouse=True)
def dienst(monkeypatch, anzeigenamen_ohne_datenbank):
    anzeigenamen_ohne_datenbank.anzeigenamen.side_effect = lambda ids: {
        k: "Anna B." for k in ids
    }
    monkeypatch.setattr(abzeichen_modul, "_service", _Dienst())


def test_angemeldete_sehen_das_abzeichen_der_autorin():
    beitraege = [_Beitrag(original_author=AUTORIN), _Beitrag(original_author=ANDERE)]

    fuer_aufrufer(beitraege, Aufrufer(kennung="ali-3"))

    assert [b.autor_abzeichen for b in beitraege] == [3, None]
    assert beitraege[0].original_author is None


def test_besucher_sehen_kein_abzeichen():
    beitraege = [_Beitrag(original_author=AUTORIN)]

    fuer_aufrufer(beitraege, Aufrufer(kennung="anonymous"))

    assert beitraege[0].autor_abzeichen is None
    assert beitraege[0].autor_name is None


def test_ohne_dienst_kein_abzeichen(monkeypatch):
    monkeypatch.setattr(abzeichen_modul, "_service", None)
    beitraege = [_Beitrag(original_author=AUTORIN)]

    fuer_aufrufer(beitraege, Aufrufer(kennung="ali-3"))

    assert beitraege[0].autor_abzeichen is None


def test_nur_an_beitraegen_nicht_an_aussagen():
    aussagen = [_Aussage(original_author=AUTORIN)]

    fuer_aufrufer(aussagen, Aufrufer(kennung="ali-3"), AUSSAGE)

    assert aussagen[0].autor_abzeichen is None
