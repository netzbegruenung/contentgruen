"""
Der Punktestand einer Person (#352): aus welchen Beitraegen, welcher Nutzung und
welchen Stimmen er entsteht. Die Rechnung selbst pruefen tests/unit/domain/test_punkte.py.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Dict, List
from unittest.mock import AsyncMock, patch

import pytest

from core.config import Settings
from services.punkte_service import PunkteService

pytestmark = pytest.mark.asyncio

JETZT = datetime(2026, 10, 30, 12, tzinfo=timezone.utc)
KIM = "kim-1"
START = "start-9"


def _beitrag(alter_tage: float) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), created=JETZT - timedelta(days=alter_tage))


class _Quellen:
    """Steht fuer Qdrant und PostgreSQL: liefert, was ihm gegeben wird."""

    def __init__(self, beitraege, nutzung=None, zustimmungen=0, einwuerfe=None):
        self.beitraege = beitraege
        self.nutzung = nutzung or {}
        self.zustimmungen_zahl = zustimmungen
        self.einwuerfe = einwuerfe or {}
        self.ausgenommen = None

    async def sichtbare_beitraege(self, user_id: str) -> List:
        return self.beitraege

    def get_nutzung_entdoppelt_batch(self, ids) -> Dict[str, int]:
        return {str(i): self.nutzung.get(i, 0) for i in ids}

    def zustimmungen(self, content_ids, ausgenommen) -> int:
        self.ausgenommen = ausgenommen
        return self.zustimmungen_zahl if content_ids else 0

    def einwuerfe_ausformuliert_je_tag(self, user_id: str, bis) -> Dict[date, int]:
        self.einwuerfe_bis = bis
        return self.einwuerfe


def _service(quellen: _Quellen, **einstellungen) -> PunkteService:
    settings = Settings(
        startkonten=START,
        punkte_nutzung=10,
        punkte_zustimmung=5,
        punkte_beitrag=1,
        punkte_einwurf_ausformuliert=1,
        punkte_deckel_tun_je_tag=3,
        **einstellungen,
    )
    return PunkteService(
        quellen.sichtbare_beitraege, quellen, quellen, settings, jetzt=lambda: JETZT
    )


async def test_punkte_wirkung_aus_entdoppelter_nutzung_und_zustimmung():
    beitrag = _beitrag(10)
    quellen = _Quellen([beitrag], nutzung={beitrag.id: 2}, zustimmungen=3)

    stand = await _service(quellen).punkte(KIM)

    assert stand.wirkung == 35


async def test_punkte_zustimmung_ohne_eigene_und_ohne_startkonten():
    quellen = _Quellen([_beitrag(10)], zustimmungen=1)

    await _service(quellen).punkte(KIM)

    assert quellen.ausgenommen == {KIM, START}


async def test_punkte_beitrag_zaehlt_erst_nach_drei_tagen():
    quellen = _Quellen([_beitrag(2.9), _beitrag(3), _beitrag(4)])

    stand = await _service(quellen).punkte(KIM)

    assert stand.tun == 2


async def test_punkte_tun_mit_ausformulierten_einwuerfen_je_tag_gedeckelt():
    tag = (JETZT - timedelta(days=5)).date()
    quellen = _Quellen(
        [_beitrag(5), _beitrag(5)], einwuerfe={tag: 2, tag - timedelta(1): 1}
    )

    stand = await _service(quellen).punkte(KIM)

    assert stand.tun == 3 + 1
    # Einwuerfe warten wie Beitraege drei Tage.
    assert quellen.einwuerfe_bis == JETZT - timedelta(days=3)


async def test_punkte_startkonto_sammelt_keine():
    beitrag = _beitrag(10)
    quellen = _Quellen([beitrag], nutzung={beitrag.id: 5}, zustimmungen=5)

    stand = await _service(quellen).punkte(START)

    assert stand.gesamt == 0


async def test_punkte_ohne_beitraege_keine_wirkung():
    """Gesperrte und entfernte Beitraege liefert die Quelle nicht: keine Punkte."""
    stand = await _service(_Quellen([])).punkte(KIM)

    assert stand.gesamt == 0


async def test_get_punkte_service_liest_nur_sichtbare_beitraege_der_person():
    """
    Gesperrte und geloeschte Beitraege verlieren ihre Punkte, weil die Verdrahtung
    get_by_author nutzt; dass get_by_author sie auslaesst, prueft
    tests/unit/repositories/test_base_repository.py.
    """
    from dependencies import get_punkte_service
    from domain.content_registry import BEITRAGSTYPEN_WERTE

    with patch(
        "repositories.aggregated.content_repository.ContentRepository"
    ) as inhalte, patch(
        "repositories.usage_tracking_repository.get_usage_repository"
    ) as nutzung, patch(
        "repositories.punkte_repository.get_punkte_repository"
    ) as stimmen:
        inhalte.return_value.get_by_author = AsyncMock(return_value=[])
        nutzung.return_value.get_nutzung_entdoppelt_batch.return_value = {}
        stimmen.return_value.zustimmungen.return_value = 0
        stimmen.return_value.einwuerfe_ausformuliert_je_tag.return_value = {}

        stand = await get_punkte_service(Settings()).punkte(KIM)

    inhalte.return_value.get_by_author.assert_awaited_once_with(
        KIM, limit=10000, offset=0, content_types=BEITRAGSTYPEN_WERTE
    )
    assert stand.gesamt == 0
