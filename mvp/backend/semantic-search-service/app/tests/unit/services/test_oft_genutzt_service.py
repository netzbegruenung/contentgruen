"""
"Diese Woche oft genutzt" (#364): welche Beitraege die Startseite zeigt und wann
der Bereich ganz entfaellt.
"""

import uuid
from typing import Dict, List, Optional

import pytest

from services.oft_genutzt_service import OftGenutztService

pytestmark = pytest.mark.asyncio


class _Nutzung:
    """Steht fuer die Trend-Abfrage: liefert, was ihr gegeben wird, und merkt sich den Aufruf."""

    def __init__(self, trend: List[Dict]):
        self.trend = trend
        self.aufrufe: List[Dict] = []

    def get_trending_content(self, limit: int = 10, hours: int = 24):
        self.aufrufe.append({"limit": limit, "hours": hours})
        return self.trend[:limit]


def _trend(*nutzungen: int) -> List[Dict]:
    return [
        {"content_id": str(uuid.uuid4()), "recent_uses": n, "total_uses": n + 10}
        for n in nutzungen
    ]


def _service(trend: List[Dict], unsichtbar: frozenset = frozenset()):
    async def beitrag_laden(beitrag_id: uuid.UUID) -> Optional[Dict]:
        if str(beitrag_id) in unsichtbar:
            return None
        return {"id": str(beitrag_id), "title": f"Titel {beitrag_id}"}

    nutzung = _Nutzung(trend)
    return OftGenutztService(nutzung, beitrag_laden), nutzung


async def test_beitraege_zu_wenig_nutzung_leer():
    # Nur zwei Beitraege erreichen die Mindestnutzung - zu wenig fuer einen Bereich.
    service, _ = _service(_trend(5, 3, 1, 1))

    assert await service.beitraege() == []


async def test_beitraege_genug_nutzung_meistgenutzte_zuerst():
    trend = _trend(7, 4, 2, 1)
    service, _ = _service(trend)

    beitraege = await service.beitraege()

    assert [b["id"] for b in beitraege] == [t["content_id"] for t in trend[:3]]
    assert [b["recent_uses"] for b in beitraege] == [7, 4, 2]


async def test_beitraege_fragt_die_letzten_sieben_tage_ab():
    service, nutzung = _service(_trend(3, 3, 3))

    await service.beitraege()

    assert nutzung.aufrufe[0]["hours"] == 7 * 24


async def test_beitraege_hoechstens_fuenf():
    service, _ = _service(_trend(9, 8, 7, 6, 5, 4, 3))

    assert len(await service.beitraege()) == 5


async def test_beitraege_unsichtbare_fallen_weg_und_zaehlen_nicht():
    # Gesperrt oder geloescht: Der Beitrag fehlt, und ohne ihn bleiben zwei -
    # der Bereich entfaellt, statt mit einer Luecke dazustehen.
    trend = _trend(6, 5, 4)
    service, _ = _service(trend, unsichtbar=frozenset({trend[1]["content_id"]}))

    assert await service.beitraege() == []


async def test_beitraege_unsichtbare_machen_platz_fuer_naechste():
    trend = _trend(9, 8, 7, 6, 5, 4)
    service, _ = _service(trend, unsichtbar=frozenset({trend[0]["content_id"]}))

    beitraege = await service.beitraege()

    assert [b["recent_uses"] for b in beitraege] == [8, 7, 6, 5, 4]


async def test_beitraege_ohne_nutzung_leer():
    service, _ = _service([])

    assert await service.beitraege() == []
