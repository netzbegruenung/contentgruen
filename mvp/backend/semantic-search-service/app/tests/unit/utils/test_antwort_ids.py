"""antwort_ids: die IDs aus replysuggestions, in jeder Form, in der sie im Payload stehen (#603)."""

import json
import uuid

import pytest

from utils.antwort_ids import antwort_ids

A = str(uuid.uuid4())
B = str(uuid.uuid4())


@pytest.mark.unit
class TestAntwortIds:
    def test_liste_von_objekten_wie_upsert_sie_schreibt(self):
        assert antwort_ids([{"id": A}, {"id": B}]) == [A, B]

    def test_json_text_wie_aus_aussagen_entfernen_ihn_schreibt(self):
        assert antwort_ids(json.dumps([{"id": A}, {"id": B}])) == [A, B]

    def test_modelle_mit_uuid(self):
        class Vorschlag:
            def __init__(self, kennung):
                self.id = uuid.UUID(kennung)

        assert antwort_ids([Vorschlag(A)]) == [A]

    def test_doppelte_fallen_weg_reihenfolge_bleibt(self):
        assert antwort_ids([{"id": B}, {"id": A}, {"id": B}]) == [B, A]

    @pytest.mark.parametrize(
        "kaputt", [None, "", "kein json", "{}", 42, [{"ohne": "id"}], [None]]
    )
    def test_unlesbares_ergibt_leere_liste(self, kaputt):
        assert antwort_ids(kaputt) == []
