"""
Meilenstein-Abzeichen am Anzeigenamen (#351): nur mit Zustimmung zur Sichtbarkeit,
nur mit beiden Schaltern; ein Nein wirkt sofort, auch gegen eine laufende Rechnung.
"""

import asyncio
from typing import Dict, List, Optional

import pytest

from core.config import Settings
from domain.meilensteine import Meilenstein
from domain.abzeichen_sichtbarkeit import UnbekannterWortlaut
from repositories.abzeichen_sichtbarkeit_repository import Sichtbarkeit
from services.abzeichen_service import AbzeichenService

pytestmark = pytest.mark.asyncio

WORTLAUT = "2026-11-09"


class _Repo:
    def __init__(self):
        self.antworten_je: Dict[str, bool] = {}

    def lesen(self, user_id: str) -> Optional[Sichtbarkeit]:
        if user_id not in self.antworten_je:
            return None
        return Sichtbarkeit(self.antworten_je[user_id], WORTLAUT, None)

    def antworten(self, user_id: str, zeigen: bool, wortlaut: str) -> None:
        self.antworten_je[user_id] = zeigen

    def zeigende(self) -> List[str]:
        return [k for k, v in self.antworten_je.items() if v]


def _meilenstein(erreicht: bool) -> Meilenstein:
    return Meilenstein("x", "x", "wirkung", 1, 1 if erreicht else 0)


def _service(repo, erreicht=None, an=True, meilensteine=None) -> AbzeichenService:
    erreicht = erreicht if erreicht is not None else {}

    async def standard(user_id: str) -> List[Meilenstein]:
        return [_meilenstein(True)] * erreicht.get(user_id, 0) + [_meilenstein(False)]

    settings = Settings(punkte_aktiv=an, abzeichen_sichtbar_aktiv=an)
    return AbzeichenService(repo, meilensteine or standard, settings)


async def test_ja_zeigt_die_zahl_der_erreichten_meilensteine():
    repo = _Repo()
    dienst = _service(repo, {"kim-1": 3})

    await dienst.antworten("kim-1", True, WORTLAUT)

    assert dienst.abzeichen(["kim-1", "bo-2", None]) == {"kim-1": 3}


async def test_ohne_zustimmung_kein_abzeichen():
    repo = _Repo()
    dienst = _service(repo, {"kim-1": 3, "bo-2": 2})
    repo.antworten("bo-2", False, WORTLAUT)

    await dienst.alle_aktualisieren()

    assert dienst.abzeichen(["kim-1", "bo-2"]) == {}


async def test_nein_nimmt_das_abzeichen_sofort_weg():
    repo = _Repo()
    dienst = _service(repo, {"kim-1": 3})
    await dienst.antworten("kim-1", True, WORTLAUT)

    await dienst.antworten("kim-1", False, WORTLAUT)

    assert dienst.abzeichen(["kim-1"]) == {}
    assert repo.antworten_je["kim-1"] is False


async def test_ohne_erreichten_meilenstein_kein_abzeichen():
    """Auch Startkonten und Konten ohne Art.-9-Einwilligung: Sie haben keine Meilensteine."""
    repo = _Repo()
    dienst = _service(repo, meilensteine=lambda user_id: _leer())

    await dienst.antworten("kim-1", True, WORTLAUT)

    assert dienst.abzeichen(["kim-1"]) == {}


async def _leer() -> List[Meilenstein]:
    return []


async def test_ohne_schalter_keine_abzeichen():
    repo = _Repo()
    repo.antworten("kim-1", True, WORTLAUT)
    dienst = _service(repo, {"kim-1": 3}, an=False)

    await dienst.alle_aktualisieren()

    assert dienst.abzeichen(["kim-1"]) == {}


async def test_nur_punkte_an_reicht_nicht():
    repo = _Repo()
    repo.antworten("kim-1", True, WORTLAUT)
    settings = Settings(punkte_aktiv=True, abzeichen_sichtbar_aktiv=False)

    async def drei(user_id):
        return [_meilenstein(True)] * 3

    dienst = AbzeichenService(repo, drei, settings)
    await dienst.alle_aktualisieren()

    assert dienst.abzeichen(["kim-1"]) == {}


async def test_im_takt_vergisst_wer_nicht_mehr_zustimmt():
    repo = _Repo()
    dienst = _service(repo, {"kim-1": 2})
    await dienst.antworten("kim-1", True, WORTLAUT)
    repo.antworten("kim-1", False, WORTLAUT)  # etwa aus einem zweiten Prozess

    await dienst.alle_aktualisieren()

    assert dienst.abzeichen(["kim-1"]) == {}


async def test_nein_waehrend_einer_rechnung_laesst_kein_abzeichen_zurueck():
    repo = _Repo()
    repo.antworten("kim-1", True, WORTLAUT)
    weiter = asyncio.Event()

    async def langsam(user_id):
        await weiter.wait()
        return [_meilenstein(True)]

    dienst = _service(repo, meilensteine=langsam)
    rechnung = asyncio.create_task(dienst.alle_aktualisieren())
    await asyncio.sleep(0.05)

    await dienst.antworten("kim-1", False, WORTLAUT)
    weiter.set()
    await rechnung

    assert dienst.abzeichen(["kim-1"]) == {}


async def test_widerruf_vergisst_sofort():
    repo = _Repo()
    dienst = _service(repo, {"kim-1": 1})
    await dienst.antworten("kim-1", True, WORTLAUT)

    dienst.vergessen("kim-1")

    assert dienst.abzeichen(["kim-1"]) == {}


async def test_unbekannter_wortlaut():
    dienst = _service(_Repo())

    with pytest.raises(UnbekannterWortlaut):
        await dienst.antworten("kim-1", True, "1999-01-01")


async def test_fehler_beim_rechnen_kostet_nur_das_abzeichen():
    repo = _Repo()

    async def kaputt(user_id):
        raise RuntimeError("weg")

    dienst = _service(repo, meilensteine=kaputt)
    await dienst.antworten("kim-1", True, WORTLAUT)

    assert dienst.abzeichen(["kim-1"]) == {}


async def test_widerruf_der_art9_einwilligung_nimmt_das_ja_zurueck():
    """Nach einer neuen Art.-9-Einwilligung erscheint das Abzeichen nicht ohne neue Frage."""
    repo = _Repo()
    dienst = _service(repo, {"kim-1": 2})
    await dienst.antworten("kim-1", True, WORTLAUT)

    dienst.zuruecknehmen("kim-1")

    assert dienst.abzeichen(["kim-1"]) == {}
    assert repo.antworten_je["kim-1"] is False


async def test_widerruf_ohne_frueheres_ja_schreibt_nichts():
    repo = _Repo()
    dienst = _service(repo)

    dienst.zuruecknehmen("kim-1")

    assert "kim-1" not in repo.antworten_je


async def test_im_takt_uebersteht_einen_fehler():
    from services.abzeichen_service import abzeichen_im_takt

    aufrufe = []

    class _Dienst:
        async def alle_aktualisieren(self):
            aufrufe.append(1)
            if len(aufrufe) == 1:
                raise RuntimeError("weg")
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await abzeichen_im_takt(_Dienst(), takt_sekunden=0)

    assert len(aufrufe) == 2
