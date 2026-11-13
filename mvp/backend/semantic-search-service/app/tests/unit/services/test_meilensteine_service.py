"""
Die Meilensteine einer Person (#351): aus welchen Beitraegen, welcher Nutzung, welchen
Stimmen und Einwuerfen sie entstehen. Die Schwellen pruefen
tests/unit/domain/test_meilensteine.py.
"""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Dict, List

import pytest

from core.config import Settings
from services.meilensteine_service import MeilensteineService

pytestmark = pytest.mark.asyncio

KIM = "kim-1"
START = "start-9"
JETZT = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)


class _Quellen:
    """Steht fuer Qdrant und PostgreSQL: liefert, was ihm gegeben wird."""

    def __init__(
        self,
        beitraege=(),
        nutzung=None,
        zustimmungen=0,
        ausformuliert=0,
        eingeworfen=0,
        einwuerfe=0,
        beantwortet=(),
    ):
        self.beitraege = list(beitraege)
        self.nutzung = nutzung or {}
        self.zustimmungen_zahl = zustimmungen
        self.ausformuliert = ausformuliert
        self.eingeworfen = eingeworfen
        self.einwuerfe = einwuerfe
        self.beantwortet = {str(i) for i in beantwortet}
        self.gefragt_nach_antworten: List = []
        self.aufrufe: List[str] = []

    async def sichtbare_beitraege(self, user_id: str) -> List:
        self.aufrufe.append("beitraege")
        return self.beitraege

    def get_nutzung_entdoppelt_batch(self, ids) -> Dict[str, int]:
        return {str(i): self.nutzung.get(i, 0) for i in ids}

    def zustimmungen(self, content_ids, ausgenommen) -> int:
        self.zustimmungen_ausgenommen = ausgenommen
        return self.zustimmungen_zahl if content_ids else 0

    def einwuerfe_ausformuliert_von(self, user_id: str, ausgenommen) -> int:
        self.ausformuliert_von = user_id
        self.ausformuliert_ausgenommen = ausgenommen
        return self.ausformuliert

    def eigene_einwuerfe_von_anderen_ausformuliert(self, user_id, ausgenommen) -> int:
        self.eingeworfen_ausgenommen = ausgenommen
        return self.eingeworfen

    def eigene_einwuerfe(self, user_id: str) -> int:
        self.einwuerfe_von = user_id
        return self.einwuerfe

    async def beantwortete(self, ids) -> set:
        self.gefragt_nach_antworten.append(list(ids))
        return {str(i) for i in ids} & self.beantwortet


def _service(quellen: _Quellen, eingewilligt=lambda user_id: True):
    return MeilensteineService(
        quellen.sichtbare_beitraege,
        quellen,
        quellen,
        Settings(startkonten=START),
        quellen.beantwortete,
        eingewilligt=eingewilligt,
        jetzt=lambda: JETZT,
    )


def _beitrag(
    alter: timedelta = timedelta(hours=1), typ: str = "post"
) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), created=JETZT - alter, content_type=typ)


def _nach_kennung(meilensteine) -> dict:
    return {m.kennung: m for m in meilensteine}


async def test_meilensteine_aus_entdoppelter_nutzung_aller_beitraege():
    eins, zwei = _beitrag(), _beitrag()
    quellen = _Quellen([eins, zwei], nutzung={eins.id: 7, zwei.id: 4})

    meilensteine = _nach_kennung(await _service(quellen).meilensteine(KIM))

    assert meilensteine["nutzung-10"].stand == 11
    assert meilensteine["nutzung-10"].erreicht
    assert not meilensteine["nutzung-50"].erreicht


async def test_zustimmung_ohne_eigene_und_startkonten():
    quellen = _Quellen([_beitrag()], zustimmungen=1)

    meilensteine = _nach_kennung(await _service(quellen).meilensteine(KIM))

    assert meilensteine["zustimmung-1"].erreicht
    assert quellen.zustimmungen_ausgenommen == {KIM, START}


async def test_unterstuetzungsarbeit_ohne_startkonten():
    quellen = _Quellen(ausformuliert=10, eingeworfen=2)

    meilensteine = _nach_kennung(await _service(quellen).meilensteine(KIM))

    assert meilensteine["ausformuliert-10"].erreicht
    assert meilensteine["eingeworfen-10"].stand == 2
    assert quellen.ausformuliert_von == KIM
    assert quellen.ausformuliert_ausgenommen == {START}
    assert quellen.eingeworfen_ausgenommen == {START}


async def test_startkonto_hat_keine_meilensteine():
    quellen = _Quellen([_beitrag()], zustimmungen=5)

    assert await _service(quellen).meilensteine(START) == []
    assert quellen.aufrufe == []


async def test_ohne_einwilligung_keine_meilensteine():
    quellen = _Quellen([_beitrag()], zustimmungen=5)
    gefragt = []

    def eingewilligt(user_id):
        gefragt.append(user_id)
        return False

    assert await _service(quellen, eingewilligt).meilensteine(KIM) == []
    assert gefragt == [KIM]
    assert quellen.aufrufe == []


async def test_erster_einwurf_aus_eigenen_einwuerfen():
    quellen = _Quellen(einwuerfe=1)

    meilensteine = _nach_kennung(await _service(quellen).meilensteine(KIM))

    assert meilensteine["einwurf-1"].erreicht
    assert meilensteine["einwurf-1"].art == "weg"
    assert quellen.einwuerfe_von == KIM


async def test_erster_fremder_einwurf_ausformuliert_ab_eins():
    quellen = _Quellen(ausformuliert=1)

    meilensteine = _nach_kennung(await _service(quellen).meilensteine(KIM))

    assert meilensteine["ausformuliert-1"].erreicht
    assert not meilensteine["ausformuliert-10"].erreicht


async def test_beitrag_haelt_erst_nach_drei_tagen():
    frisch = _beitrag(timedelta(days=2, hours=23))
    quellen = _Quellen([frisch])

    meilensteine = _nach_kennung(await _service(quellen).meilensteine(KIM))
    assert not meilensteine["beitrag-gehalten-1"].erreicht

    quellen.beitraege.append(_beitrag(timedelta(days=3)))
    meilensteine = _nach_kennung(await _service(quellen).meilensteine(KIM))
    assert meilensteine["beitrag-gehalten-1"].stand == 1
    assert meilensteine["beitrag-gehalten-1"].erreicht


async def test_erster_widerspruch_nur_kommentare_die_eine_aussage_fuehrt():
    kommentar = _beitrag(typ="commentary")
    ohne_aussage = _beitrag(typ="commentary")
    post = _beitrag(typ="post")
    quellen = _Quellen(
        [kommentar, ohne_aussage, post], beantwortet=[kommentar.id, post.id]
    )

    meilensteine = _nach_kennung(await _service(quellen).meilensteine(KIM))

    assert meilensteine["aussage-kommentiert-1"].stand == 1
    assert meilensteine["aussage-kommentiert-1"].erreicht
    # Nur Kommentare werden nachgeschlagen; ein Post zaehlt nicht, auch wenn er antwortet.
    assert quellen.gefragt_nach_antworten == [[kommentar.id, ohne_aussage.id]]


async def test_ohne_kommentare_keine_abfrage_der_aussagen():
    quellen = _Quellen([_beitrag(typ="post")])

    meilensteine = _nach_kennung(await _service(quellen).meilensteine(KIM))

    assert not meilensteine["aussage-kommentiert-1"].erreicht
    assert quellen.gefragt_nach_antworten == []
