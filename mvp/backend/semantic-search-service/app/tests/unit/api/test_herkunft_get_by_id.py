"""
getById von Kommentar und Hintergrundinfo liefert die Herkunft mit Link (Persona-Test Gerd).

Die Ergebnisseite nach dem Speichern laedt den Beitrag ueber getById seines Typs. Ohne
``reference_text`` zeigte ihre Karte "Herkunft 1" statt der Domain mit Link; die Suche
und die Beitragsansicht ergaenzten die Herkunft schon (``herkunft_ergaenzen``).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.commentary import router as commentary_router
from api.v1.generic_text import router as generic_text_router
from dependencies import (
    get_commentary_service,
    get_generic_text_service,
    get_reference_service,
)
from domain.models.commentary import CommentaryReference
from domain.models.generic_text import GenericTextReference
from tests.unit.api.test_beitrag_responses import (
    EIGEN,
    _hintergrundinfo,
    _kommentar,
)

LINK = "https://example.org/studie"
HERKUNFT_ID = uuid.uuid4()
# Feste ID in der URL: pytest-xdist verlangt in jedem Worker dieselben Testnamen.
BEITRAG_ID = "8dec5eb1-004b-445d-95d6-b1ca2b7fea46"


def _referenz():
    return {"reference_id": HERKUNFT_ID, "created": "2026-11-13T10:00:00Z"}


def _mit_herkunft(beitrag, referenz_klasse):
    beitrag.references = [referenz_klasse(**_referenz())]
    return beitrag


def _ergaenzen(beitrag):
    for ref in beitrag.references:
        ref.reference_text = LINK
        ref.reference_description = "Studie"


@pytest.fixture
def herkunft():
    dienst = MagicMock()
    dienst.herkunft_ergaenzen = AsyncMock(side_effect=_ergaenzen)
    return dienst


@pytest.fixture
def client(herkunft):
    app = FastAPI()
    app.include_router(commentary_router, prefix="/api/v1/commentary")
    app.include_router(generic_text_router, prefix="/api/v1/generic_text")
    kommentare = MagicMock()
    kommentare.get = AsyncMock(
        side_effect=lambda i: _mit_herkunft(_kommentar(i), CommentaryReference)
    )
    hintergrundinfos = MagicMock()
    hintergrundinfos.get = AsyncMock(
        side_effect=lambda i: _mit_herkunft(_hintergrundinfo(i), GenericTextReference)
    )
    app.dependency_overrides.update(
        {
            get_commentary_service: lambda: kommentare,
            get_generic_text_service: lambda: hintergrundinfos,
            get_reference_service: lambda: herkunft,
        }
    )
    return TestClient(app)


@pytest.mark.unit
@pytest.mark.parametrize(
    "url",
    [
        f"/api/v1/commentary/getById?commentary_id={BEITRAG_ID}",
        f"/api/v1/generic_text/getById?generic_text_id={BEITRAG_ID}",
    ],
)
def test_get_by_id_liefert_den_link_der_herkunft(client, herkunft, url):
    antwort = client.get(url, headers=EIGEN)

    assert antwort.status_code == 200, antwort.text
    [referenz] = antwort.json()["references"]
    assert referenz["reference_id"] == str(HERKUNFT_ID)
    assert referenz["reference_text"] == LINK
    assert referenz["reference_description"] == "Studie"
    herkunft.herkunft_ergaenzen.assert_awaited_once()
