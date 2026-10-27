"""
"Diese Woche oft genutzt" (#364): welche Beitraege die Startseite zeigt und wann
der Bereich ganz entfaellt.
"""

import logging
import uuid
from types import SimpleNamespace
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, ValidationError

from domain.models.content_type import ContentType
from services.oft_genutzt_service import OftGenutztService, sichtbaren_beitrag_laden

pytestmark = pytest.mark.asyncio


class _Nutzung:
    """Steht fuer die Nutzungsabfrage: liefert, was ihr gegeben wird, und merkt sich den Aufruf."""

    def __init__(self, kandidaten: List[Dict]):
        self.kandidaten = kandidaten
        self.aufrufe: List[Dict] = []

    def get_trending_content(self, limit: int = 10, hours: int = 24):
        self.aufrufe.append({"limit": limit, "hours": hours})
        return self.kandidaten[:limit]


def _kandidaten(*nutzungen: int) -> List[Dict]:
    return [
        {"content_id": str(uuid.uuid4()), "recent_uses": n, "total_uses": n + 10}
        for n in nutzungen
    ]


def _service(kandidaten: List[Dict], unsichtbar: frozenset = frozenset()):
    async def beitrag_laden(beitrag_id: uuid.UUID) -> Optional[Dict]:
        if str(beitrag_id) in unsichtbar:
            return None
        return {"id": str(beitrag_id), "title": f"Titel {beitrag_id}"}

    nutzung = _Nutzung(kandidaten)
    return OftGenutztService(nutzung, beitrag_laden), nutzung


async def test_beitraege_zu_wenig_nutzung_leer():
    # Nur zwei Beitraege erreichen die Mindestnutzung - zu wenig fuer einen Bereich.
    service, _ = _service(_kandidaten(5, 3, 1, 1))

    assert await service.beitraege() == []


async def test_beitraege_genug_nutzung_meistgenutzte_zuerst():
    kandidaten = _kandidaten(7, 4, 2, 1)
    service, _ = _service(kandidaten)

    beitraege = await service.beitraege()

    assert [b["id"] for b in beitraege] == [t["content_id"] for t in kandidaten[:3]]
    assert [b["recent_uses"] for b in beitraege] == [7, 4, 2]


async def test_beitraege_fragt_die_letzten_sieben_tage_ab():
    service, nutzung = _service(_kandidaten(3, 3, 3))

    await service.beitraege()

    assert nutzung.aufrufe[0]["hours"] == 7 * 24


async def test_beitraege_hoechstens_fuenf():
    service, _ = _service(_kandidaten(9, 8, 7, 6, 5, 4, 3))

    assert len(await service.beitraege()) == 5


async def test_beitraege_unsichtbare_fallen_weg_und_zaehlen_nicht():
    # Gesperrt oder geloescht: Der Beitrag fehlt, und ohne ihn bleiben zwei -
    # der Bereich entfaellt, statt mit einer Luecke dazustehen.
    kandidaten = _kandidaten(6, 5, 4)
    service, _ = _service(
        kandidaten, unsichtbar=frozenset({kandidaten[1]["content_id"]})
    )

    assert await service.beitraege() == []


async def test_beitraege_unsichtbare_machen_platz_fuer_naechste():
    kandidaten = _kandidaten(9, 8, 7, 6, 5, 4)
    service, _ = _service(
        kandidaten, unsichtbar=frozenset({kandidaten[0]["content_id"]})
    )

    beitraege = await service.beitraege()

    assert [b["recent_uses"] for b in beitraege] == [8, 7, 6, 5, 4]


async def test_beitraege_ohne_nutzung_leer():
    service, _ = _service([])

    assert await service.beitraege() == []


def _validierungsfehler() -> ValidationError:
    class _Pflicht(BaseModel):
        text: str

    try:
        _Pflicht()
    except ValidationError as fehler:
        return fehler
    raise AssertionError("ValidationError erwartet")


def _lader(typ_get, beitrag_get):
    """sichtbaren_beitrag_laden mit Repositories, die nur ``get`` kennen."""
    alle_typen = MagicMock()
    alle_typen.get = AsyncMock(side_effect=typ_get)
    des_typs = MagicMock()
    des_typs.get = AsyncMock(side_effect=beitrag_get)
    factory = MagicMock()
    factory.create_content_repository.return_value = alle_typen
    factory.create_registry_repository.return_value = des_typs
    herkunft = MagicMock()
    herkunft.herkunft_ergaenzen = AsyncMock()
    return sichtbaren_beitrag_laden(MagicMock(), factory, herkunft), herkunft


def _post(_id):
    return SimpleNamespace(content_type=ContentType.POST)


async def test_laden_sichtbarer_post_mit_herkunft_und_typ():
    beitrag = MagicMock()
    beitrag.model_dump.return_value = {"id": "p-1"}
    laden, herkunft = _lader(_post, lambda _id: beitrag)

    daten = await laden(uuid.uuid4())

    assert daten == {"id": "p-1", "result_type": "post"}
    herkunft.herkunft_ergaenzen.assert_awaited_once_with(beitrag)


async def test_laden_gesperrt_oder_geloescht_ist_none(caplog):
    def weg(_id):
        raise ValueError("not found")

    laden, _ = _lader(_post, weg)

    with caplog.at_level(logging.ERROR):
        assert await laden(uuid.uuid4()) is None
    assert caplog.records == []


async def test_laden_kaputter_datensatz_fehlt_und_wird_geloggt(caplog):
    fehler = _validierungsfehler()

    def kaputt(_id):
        raise fehler

    laden, _ = _lader(_post, kaputt)

    with caplog.at_level(logging.ERROR):
        assert await laden(uuid.uuid4()) is None
    assert any("not readable" in r.getMessage() for r in caplog.records)
