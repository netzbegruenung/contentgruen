"""
Fristen der Muster-Hinweise und der Pruefwerte (#352). Das Erkennen selbst pruefen
tests/integration/test_muster_hinweise.py gegen PostgreSQL.
"""

import asyncio
from datetime import date
from unittest.mock import Mock

import pytest

from services.muster_hinweise_service import MusterHinweiseService, loeschen_im_takt


def test_fristen_anwenden_verwirft_pruefwerte_und_loescht_nach_acht_wochen():
    hinweise, nutzung = Mock(), Mock()

    MusterHinweiseService(hinweise, nutzung).fristen_anwenden(date(2026, 10, 30))

    nutzung.vergangene_tage_verwerfen.assert_called_once_with(date(2026, 10, 30))
    hinweise.loeschen_vor.assert_called_once_with(date(2026, 9, 4))


@pytest.mark.asyncio
async def test_loeschen_im_takt_laeuft_nach_fehler_weiter():
    hinweise, nutzung = Mock(), Mock()
    nutzung.vergangene_tage_verwerfen = Mock(side_effect=[RuntimeError("weg"), 0, 0])

    task = asyncio.create_task(
        loeschen_im_takt(MusterHinweiseService(hinweise, nutzung), takt_sekunden=0)
    )
    while nutzung.vergangene_tage_verwerfen.call_count < 2:
        await asyncio.sleep(0.01)
    task.cancel()

    assert nutzung.vergangene_tage_verwerfen.call_count >= 2
