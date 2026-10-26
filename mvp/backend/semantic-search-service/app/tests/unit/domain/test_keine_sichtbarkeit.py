"""
Grün-Intern entfällt (#213): Jeder Beitrag ist sichtbar, eine Sichtbarkeits-Markierung
gibt es nicht mehr. Neue Beiträge setzen daher keine. Gespeicherte Werte bleiben bis
zur Bereinigung der Zustände liegen und dürfen weder das Lesen brechen noch beim
Zurückschreiben verloren gehen.
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
    def test_neuer_beitrag_setzt_keine_sichtbarkeit(self):
        assert _kommentar().visibility is None

    def test_neuer_beitrag_speichert_kein_gruen_intern(self):
        payload = json.loads(_kommentar().model_dump_json())
        assert payload.get("visibility") != "internal"

    @pytest.mark.parametrize("gespeichert", ["internal", "visible"])
    def test_gespeicherter_wert_bleibt_beim_zurueckschreiben(self, gespeichert):
        beitrag = _kommentar(visibility=gespeichert)
        payload = json.loads(beitrag.model_dump_json())
        assert payload["visibility"] == gespeichert
