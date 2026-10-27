"""
GET /api/v1/usage/trending/woche (#364): die Antwort fuer "Diese Woche oft genutzt".

Der Pfad ist fuer Besucher offen (EndpointPolicy.cs, "/api/v1/usage/trending").
Besucher sehen deshalb weder Anzeigenamen noch Kennungen, Angemeldete den
Anzeigenamen wie bei /content/recent.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import usage as usage_module
from api.v1.usage import router as usage_router
from dependencies import get_reference_service, get_settings

URL = "/api/v1/usage/trending/woche"
AUTORIN = "kim-1"


def _beitrag(nummer: int) -> dict:
    return {
        "id": f"00000000-0000-4000-8000-00000000000{nummer}",
        "result_type": "commentary",
        "title": f"Titel {nummer}",
        "original_author": AUTORIN,
        "last_modified_by": AUTORIN,
        "authors": [{"name": AUTORIN}],
        "edit_history": [],
        "recent_uses": 5 - nummer,
    }


@pytest.fixture
def namen(anzeigenamen_ohne_datenbank):
    anzeigenamen_ohne_datenbank.anzeigenamen.return_value = {AUTORIN: "Kim L."}
    return anzeigenamen_ohne_datenbank


def _client(beitraege):
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = lambda: Mock()
    app.dependency_overrides[get_reference_service] = lambda: Mock()

    nutzung = Mock()
    nutzung.enrich_content_with_usage.side_effect = lambda eintraege: [
        {**e, "usage_count": 12} for e in eintraege
    ]

    class _Service:
        def __init__(self, *_):
            pass

        async def beitraege(self):
            return [dict(b) for b in beitraege]

    return patch.multiple(
        usage_module,
        get_usage_service=Mock(return_value=nutzung),
        OftGenutztService=_Service,
        sichtbaren_beitrag_laden=Mock(),
    ), TestClient(app)


@pytest.mark.unit
class TestOftGenutztApi:
    def test_oft_genutzt_besucher_ohne_namen_und_kennungen(self, namen):
        patcher, client = _client([_beitrag(1), _beitrag(2), _beitrag(3)])
        with patcher:
            antwort = client.get(URL)

        assert antwort.status_code == 200
        results = antwort.json()["results"]
        assert [r["title"] for r in results] == ["Titel 1", "Titel 2", "Titel 3"]
        assert [r["recent_uses"] for r in results] == [4, 3, 2]
        assert {r["original_author"] for r in results} == {""}
        assert {r.get("autor_name") for r in results} == {None}
        assert results[0]["authors"] == []

    def test_oft_genutzt_angemeldet_mit_anzeigename_und_nutzung(self, namen):
        patcher, client = _client([_beitrag(1), _beitrag(2), _beitrag(3)])
        with patcher:
            antwort = client.get(URL, headers={"X-User": "leserin"})

        results = antwort.json()["results"]
        assert {r["autor_name"] for r in results} == {"Kim L."}
        assert {r["usage_count"] for r in results} == {12}

    def test_oft_genutzt_zu_wenig_nutzung_leere_liste(self, namen):
        patcher, client = _client([])
        with patcher:
            antwort = client.get(URL)

        assert antwort.status_code == 200
        assert antwort.json() == {"results": []}
