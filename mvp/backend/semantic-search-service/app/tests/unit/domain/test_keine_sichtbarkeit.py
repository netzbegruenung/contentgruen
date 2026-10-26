"""
Grün-Intern entfällt (#213): Jeder Beitrag ist sichtbar, eine Sichtbarkeits-Markierung
gibt es nicht mehr. Neue Beiträge setzen daher keine. Gespeicherte Werte bleiben bis
zur Bereinigung der Zustände liegen und dürfen weder das Lesen brechen noch beim
Zurückschreiben verloren gehen. Den Schreibweg über `_upsert` prüft
`tests/unit/services/test_base_content_service.py`.
"""

import json
import uuid

import pytest

from domain.models.commentary import CommentaryDbEntry
from tests.conftest import create_base_content_fields, create_commentary_data


def _kommentar(**felder) -> CommentaryDbEntry:
    daten = {
        **create_base_content_fields(),
        **create_commentary_data(),
        "id": str(uuid.uuid4()),
        "content_type": "commentary",
        **felder,
    }
    return CommentaryDbEntry.model_validate(daten)


@pytest.mark.unit
class TestKeineSichtbarkeit:
    def test_visibility_default_neuer_beitrag_ist_none(self):
        beitrag = _kommentar()
        payload = json.loads(beitrag.model_dump_json())

        assert beitrag.visibility is None
        assert payload["visibility"] is None

    @pytest.mark.parametrize("gespeichert", ["internal", "visible"])
    def test_visibility_gespeicherter_wert_bleibt_im_payload(self, gespeichert):
        beitrag = _kommentar(visibility=gespeichert)
        payload = json.loads(beitrag.model_dump_json())
        assert payload["visibility"] == gespeichert
