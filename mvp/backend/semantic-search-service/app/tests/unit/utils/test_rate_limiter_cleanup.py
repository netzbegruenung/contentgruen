"""
Aufraeumen der Rate-Limiter im Hintergrund.

Die Datenschutzerklaerung sagt fuer die Suchaussage: Der Adress-Hash wird nach
spaetestens elf Minuten verworfen - zehn Minuten Fenster plus ein Aufraeumtakt.
Frueher lief der Task stuendlich und rief cleanup() ohne await; abgelaufene
Schluessel blieben bis zum Neustart im Speicher.
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from utils import rate_limiter as modul
from utils.rate_limiter import (
    RateLimiter,
    aufraeumen,
    aufraeumen_im_takt,
    report_rate_limiter,
    search_query_statement_rate_limiter,
)


def test_frist_der_datenschutzerklaerung_haelt():
    """Fenster plus Takt ergibt die elf Minuten, die die Erklaerung nennt."""
    fenster = search_query_statement_rate_limiter.window
    takt = timedelta(seconds=modul.AUFRAEUM_TAKT_SEKUNDEN)

    assert fenster + takt <= timedelta(minutes=11)


@pytest.mark.asyncio
async def test_aufraeumen_entfernt_abgelaufene_schluessel_und_behaelt_frische():
    limiter = RateLimiter(max_requests=5, window_minutes=10)
    await limiter.is_rate_limited("ip:alt")
    await limiter.is_rate_limited("ip:frisch")
    limiter._requests["ip:alt"] = [datetime.utcnow() - timedelta(minutes=10, seconds=1)]

    await aufraeumen([limiter])

    assert "ip:alt" not in limiter._requests
    assert "ip:frisch" in limiter._requests


@pytest.mark.asyncio
async def test_aufraeumen_laeuft_bei_fehler_eines_limiters_weiter():
    class Kaputt(RateLimiter):
        async def cleanup(self):
            raise RuntimeError("kaputt")

    heil = RateLimiter(max_requests=5, window_minutes=10)
    heil._requests["ip:alt"] = [datetime.utcnow() - timedelta(minutes=11)]

    await aufraeumen([Kaputt(max_requests=1, window_minutes=1), heil])

    assert "ip:alt" not in heil._requests


@pytest.mark.asyncio
async def test_aufraeumen_im_takt_raeumt_wiederholt_auf(monkeypatch):
    aufrufe = []

    async def zaehlen(limiters):
        aufrufe.append(list(limiters))

    monkeypatch.setattr(modul, "aufraeumen", zaehlen)
    task = asyncio.create_task(aufraeumen_im_takt([report_rate_limiter], 0.01))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert len(aufrufe) >= 2
    assert aufrufe[0] == [report_rate_limiter]


def test_main_raeumt_beide_limiter_im_takt_auf():
    """Der Start in main.py nennt beide Limiter - nicht nur den fuer Meldungen."""
    import inspect
    import main

    quelle = inspect.getsource(main.lifespan)
    assert "aufraeumen_im_takt" in quelle
    assert "report_rate_limiter" in quelle
    assert "search_query_statement_rate_limiter" in quelle


def test_main_haelt_den_task_und_bricht_ihn_beim_shutdown_ab():
    import inspect
    import main

    quelle = inspect.getsource(main.lifespan)
    assert "app.state.rate_limiter_aufraeumen = asyncio.create_task(" in quelle
    assert "rate_limiter_aufraeumen" in quelle.split("finally:", 1)[1]
    assert ".cancel()" in quelle.split("finally:", 1)[1]
