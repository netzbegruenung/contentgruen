"""
Uebergang bis zur Umstellung der Altwerte (#214): Zwischen dem Ausrollen und dem Lauf
von scripts/manual/zustaende_umstellen.py stehen noch Altwerte im Suchindex. Sie
duerfen das Lesen nicht brechen.
"""

import uuid

import pytest

from domain.models.commentary import CommentaryDbEntry
from domain.models.content_status import ContentStatus
from tests.conftest import create_base_content_fields, create_commentary_data

pytestmark = pytest.mark.unit


def _daten(**felder) -> dict:
    return {
        **create_base_content_fields(),
        **create_commentary_data(),
        "id": str(uuid.uuid4()),
        "content_type": "commentary",
        **felder,
    }


def _kommentar(status) -> CommentaryDbEntry:
    return CommentaryDbEntry.model_validate(_daten(status=status))


@pytest.mark.parametrize(
    "altwert", ["released_internal", "approved", "draft", "duplicate", "pending_review"]
)
def test_status_altwert_liest_sich_als_sichtbar(altwert):
    assert _kommentar(altwert).status is ContentStatus.VISIBLE


@pytest.mark.parametrize(
    "wert", ["visible", "blocked", "deleted", "pending_description"]
)
def test_status_neuer_wert_bleibt(wert):
    assert _kommentar(wert).status.value == wert


def test_status_fehlt_liest_sich_als_sichtbar():
    daten = _daten()
    del daten["status"]

    assert CommentaryDbEntry.model_validate(daten).status is ContentStatus.VISIBLE


def test_status_unbekannter_wert_scheitert():
    with pytest.raises(ValueError):
        _kommentar("voellig_unbekannt")


def test_status_altes_visibility_feld_wird_ignoriert():
    beitrag = CommentaryDbEntry.model_validate(_daten(visibility="internal"))
    assert "visibility" not in beitrag.model_dump()
