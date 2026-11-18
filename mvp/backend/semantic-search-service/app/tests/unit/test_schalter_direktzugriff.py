"""
Kein Weg an den Admin-Werten vorbei (#708, Review zu PR #711, Befund 3).

Das Autouse-Fixture ``schalter_admin_alle_an`` (tests/conftest.py) setzt alle
Admin-Werte auf an; die Bestandstests pruefen deshalb nur die Obergrenze. Ein Zugriff,
der die Settings direkt liest, bliebe dort gruen. Diese Datei schliesst die Luecke:

- ``TestObergrenzeAnAdminAus``: Jede Stelle, die einen der drei Schalter nutzt, ist bei
  eingeschalteter Obergrenze und ausgeschaltetem Admin-Wert aus. Die Tests ersetzen den
  Dienst des Autouse-Fixtures ausdruecklich (``admin_werte``). Die Gegenprobe mit allen
  Admin-Werten an zeigt, dass jeder Fall wirklich am Schalter haengt.
- ``test_kein_direktzugriff_auf_die_obergrenze``: Ausserhalb von core/config.py,
  services/schalter_service.py und dem Start des Abzeichen-Takts in main.py liest kein
  Code die Obergrenze direkt.
"""

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.v1.metrics as metrics_module
import api.v1.usage as usage_module
from core.config import Settings
from dependencies import (
    get_beitrag_laden,
    get_meilensteine_service,
    get_punkte_service,
    get_settings,
)
from services.abzeichen_service import AbzeichenService, abzeichen_service_setzen
from services.schalter_service import (
    SCHALTER,
    SchalterService,
    schalter_service_setzen,
)

pytestmark = pytest.mark.unit

APP = Path(__file__).resolve().parents[2]
BEITRAG_ID = "11111111-1111-4111-8111-111111111111"
PERSON = {"X-User": "bo-2"}
ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}

ALLE_OBERGRENZEN_AN = dict(
    punkte_aktiv=True, abzeichen_sichtbar_aktiv=True, gepostet_aktiv=True
)


@pytest.fixture
def admin_werte(schalter_admin_alle_an):
    """
    Ueberschreibt das Autouse-Fixture: ein eigener Dienst, dessen Admin-Werte der Test
    vor dem ersten Aufruf setzt (``admin_werte["punkte"] = False``).
    """
    werte = {name: True for name in SCHALTER}
    schalter_service_setzen(
        SchalterService(
            admin_werte_lesen=lambda: dict(werte),
            admin_wert_setzen=lambda name, an, admin: werte.__setitem__(name, an),
        )
    )
    return werte


@pytest.fixture
def muster():
    return Mock()


@pytest.fixture
def abzeichen():
    """Ein Abzeichen-Dienst mit einem vorhandenen Abzeichen, ohne Datenbank."""
    repository = Mock()
    repository.lesen.return_value = None
    repository.zeigende.return_value = ["kim-1"]
    dienst = AbzeichenService(repository, Mock(), Settings(**ALLE_OBERGRENZEN_AN))
    dienst._abzeichen["kim-1"] = 1
    abzeichen_service_setzen(dienst)
    yield SimpleNamespace(dienst=dienst, repository=repository)
    abzeichen_service_setzen(None)


@pytest.fixture
def client(muster, abzeichen):
    app = FastAPI()
    app.include_router(usage_module.router, prefix="/api/v1/usage")
    app.include_router(metrics_module.router, prefix="/api/v1/metrics")
    app.dependency_overrides[get_settings] = lambda: Settings(**ALLE_OBERGRENZEN_AN)
    app.dependency_overrides[get_punkte_service] = lambda: Mock(
        punkte=AsyncMock(side_effect=RuntimeError("nur bis hierher"))
    )
    app.dependency_overrides[get_meilensteine_service] = lambda: Mock(
        meilensteine=AsyncMock(side_effect=RuntimeError("nur bis hierher"))
    )
    gepostet = Mock()
    gepostet.wochen.side_effect = RuntimeError("nur bis hierher")
    gepostet.stand.side_effect = RuntimeError("nur bis hierher")
    app.dependency_overrides[metrics_module.get_gepostet_service] = lambda: gepostet
    app.dependency_overrides[metrics_module.get_muster_hinweise_service] = lambda: Mock(
        **{"hinweise.side_effect": RuntimeError("nur bis hierher")}
    )

    async def laden(content_id):
        return SimpleNamespace(id=content_id, original_author="kim-1")

    app.dependency_overrides[get_beitrag_laden] = lambda: laden
    nutzung = Mock()
    nutzung.track_content_usage.return_value = True
    nutzung.get_content_usage.return_value = 1
    with patch.object(
        usage_module, "get_usage_service", return_value=nutzung
    ), patch.object(
        usage_module, "get_muster_hinweise_service", return_value=muster
    ), patch.object(
        usage_module, "get_gepostet_service", return_value=gepostet
    ):
        yield TestClient(app, raise_server_exceptions=False)


def _status_aus(feld):
    def pruefen(client, muster, abzeichen):
        antwort = client.get("/api/v1/usage/punkte/status")
        return antwort.status_code == 200 and antwort.json()[feld] is False

    return pruefen


def _404(pfad, kopf=PERSON):
    def pruefen(client, muster, abzeichen):
        return client.get(pfad, headers=kopf).status_code == 404

    return pruefen


def _admin_aktiv_aus(pfad):
    def pruefen(client, muster, abzeichen):
        antwort = client.get(pfad, headers=ADMIN)
        return antwort.status_code == 200 and antwort.json()["aktiv"] is False

    return pruefen


def _kein_muster_hinweis(client, muster, abzeichen):
    client.post(f"/api/v1/usage/content/{BEITRAG_ID}/usage", json={}, headers=PERSON)
    return not muster.nutzung_melden.called


def _keine_abzeichen(client, muster, abzeichen):
    return abzeichen.dienst.abzeichen(["kim-1"]) == {}


def _takt_rechnet_nicht(client, muster, abzeichen):
    asyncio.run(abzeichen.dienst.alle_aktualisieren())
    return not abzeichen.repository.zeigende.called


STELLEN = {
    "status_punkte": (_status_aus("aktiv"), ("punkte",)),
    "eigene_punkte": (_404("/api/v1/usage/users/me/punkte"), ("punkte",)),
    "meilensteine": (_404("/api/v1/usage/users/me/meilensteine"), ("punkte",)),
    "punkte_einwilligung": (
        _404("/api/v1/usage/users/me/punkte-einwilligung"),
        ("punkte",),
    ),
    "muster_hinweise_melden": (_kein_muster_hinweis, ("punkte",)),
    "muster_hinweise_admin": (
        _admin_aktiv_aus("/api/v1/metrics/muster-hinweise"),
        ("punkte",),
    ),
    # Abzeichen wirken nur zusammen mit den Punkten: Beide Admin-Werte schalten sie aus.
    "status_abzeichen": (
        _status_aus("abzeichen_sichtbar"),
        ("abzeichen_sichtbar", "punkte"),
    ),
    "abzeichen_sichtbarkeit": (
        _404("/api/v1/usage/users/me/abzeichen-sichtbarkeit"),
        ("abzeichen_sichtbar", "punkte"),
    ),
    "abzeichen_am_namen": (_keine_abzeichen, ("abzeichen_sichtbar", "punkte")),
    "abzeichen_takt": (_takt_rechnet_nicht, ("abzeichen_sichtbar", "punkte")),
    "gepostet_rueckfrage": (_404("/api/v1/usage/users/me/gepostet"), ("gepostet",)),
    "gepostet_admin": (_admin_aktiv_aus("/api/v1/metrics/gepostet"), ("gepostet",)),
}

FAELLE = [
    pytest.param(stelle, schalter, id=f"{stelle}-{schalter}-aus")
    for stelle, (_, alle) in STELLEN.items()
    for schalter in alle
]


class TestObergrenzeAnAdminAus:
    @pytest.mark.parametrize("stelle, schalter", FAELLE)
    def test_aus(self, stelle, schalter, admin_werte, client, muster, abzeichen):
        admin_werte[schalter] = False

        assert STELLEN[stelle][0](client, muster, abzeichen)

    @pytest.mark.parametrize("stelle", list(STELLEN))
    def test_gegenprobe_alle_admin_werte_an(
        self, stelle, admin_werte, client, muster, abzeichen
    ):
        assert not STELLEN[stelle][0](client, muster, abzeichen)


# Felder der Obergrenze in Settings (und die Property, die zwei davon verknuepft).
FELDER = {schalter.feld for schalter in SCHALTER.values()}
OBERGRENZE = FELDER | {"abzeichen_sichtbar"}
# Wo die Obergrenze direkt gelesen werden darf: die Definition, der Dienst, und der
# Start des Abzeichen-Takts (laeuft nur mit Obergrenze; ob er rechnet, entscheidet je
# Lauf der Admin-Wert).
ERLAUBT = {
    Path("core/config.py"): None,
    Path("services/schalter_service.py"): None,
    Path("main.py"): {"settings.abzeichen_sichtbar"},
}


def _direktzugriffe():
    for datei in sorted(APP.rglob("*.py")):
        relativ = datei.relative_to(APP)
        if relativ.parts[0] in ("tests", ".venv", "venv"):
            continue
        erlaubt = ERLAUBT.get(relativ, set())
        if erlaubt is None:
            continue
        for knoten in ast.walk(ast.parse(datei.read_text(encoding="utf-8"))):
            if isinstance(knoten, ast.Attribute) and knoten.attr in OBERGRENZE:
                zugriff = ast.unparse(knoten)
            elif isinstance(knoten, ast.Constant) and knoten.value in FELDER:
                # getattr(settings, "punkte_aktiv") ginge sonst am Waechter vorbei;
                # "abzeichen_sichtbar" allein ist auch der Name des Schalters.
                zugriff = repr(knoten.value)
            else:
                continue
            if zugriff not in erlaubt:
                yield f"{relativ}:{knoten.lineno}: {zugriff}"


def test_kein_direktzugriff_auf_die_obergrenze():
    """Alle Stellen fragen schalter_wirksam (services/schalter_service.py)."""
    assert list(_direktzugriffe()) == []


def test_waechter_erkennt_einen_direktzugriff(tmp_path, monkeypatch):
    """Der Waechter selbst: ein Direktzugriff in einer neuen Datei macht ihn rot."""
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "neu.py").write_text(
        "def f(settings):\n    return settings.punkte_aktiv\n", encoding="utf-8"
    )
    (tmp_path / "api" / "auch.py").write_text(
        "def g(s):\n    return getattr(s, 'gepostet_aktiv')\n", encoding="utf-8"
    )
    monkeypatch.setitem(globals(), "APP", tmp_path)

    assert list(_direktzugriffe()) == [
        "api/auch.py:2: 'gepostet_aktiv'",
        "api/neu.py:2: settings.punkte_aktiv",
    ]
