"""
Fristen der Muster-Hinweise und der Pruefwerte (#352). Das Erkennen selbst pruefen
tests/integration/test_muster_hinweise.py gegen PostgreSQL.
"""

import asyncio
from datetime import date
from unittest.mock import Mock

import pytest

from services.entdoppelung import pruefwerte_verwerfen_im_takt
from services.muster_hinweise_service import MusterHinweiseService, loeschen_im_takt


def test_fristen_anwenden_verwirft_paare_und_loescht_nach_acht_wochen():
    hinweise = Mock()

    MusterHinweiseService(hinweise).fristen_anwenden(date(2026, 10, 30))

    # Paar-Pruefwerte bleiben sieben Tage: den heutigen und die sechs davor.
    hinweise.paare_verwerfen_vor.assert_called_once_with(date(2026, 10, 24))
    hinweise.loeschen_vor.assert_called_once_with(date(2026, 9, 4))


@pytest.mark.asyncio
async def test_loeschen_im_takt_laeuft_nach_fehler_weiter():
    hinweise = Mock()
    hinweise.loeschen_vor = Mock(side_effect=[RuntimeError("weg"), 0, 0])

    task = asyncio.create_task(
        loeschen_im_takt(MusterHinweiseService(hinweise), takt_sekunden=0)
    )
    while hinweise.loeschen_vor.call_count < 2:
        await asyncio.sleep(0.01)
    task.cancel()

    assert hinweise.loeschen_vor.call_count >= 2


@pytest.mark.asyncio
async def test_pruefwerte_verwerfen_im_takt_laeuft_nach_fehler_weiter():
    """Die Pruefwerte der Entdoppelung gehen auch ohne Punkte und Muster-Hinweise."""
    nutzung = Mock()
    nutzung.vergangene_tage_verwerfen = Mock(side_effect=[RuntimeError("weg"), 0, 0])

    task = asyncio.create_task(pruefwerte_verwerfen_im_takt(nutzung, takt_sekunden=0))
    while nutzung.vergangene_tage_verwerfen.call_count < 2:
        await asyncio.sleep(0.01)
    task.cancel()

    assert nutzung.vergangene_tage_verwerfen.call_count >= 2
