"""
POST /api/v1/moderation/melder/meldungen und .../melder/angaben-loeschen (#494).

Name und E-Mail-Adresse der meldenden Person reisen im Koerper, nicht in der
Adresse: Pfade stehen in Logs. Was die Suche findet und was das Loeschen tut,
pruefen die Integrationstests (tests/integration/test_meldungen_einer_person.py);
dass nur Admins duerfen, test_moderation_nur_admin.py.
"""

import uuid
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.moderation import router as moderation_router
from dependencies import get_moderation_service, get_settings
from domain.models.meldung import (
    MELDER_EMAIL_MAX,
    MELDER_NAME_MAX,
    AngabenGeloescht,
    MelderSuche,
)

ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}
SUCHE = "/api/v1/moderation/melder/meldungen"
LOESCHEN = "/api/v1/moderation/melder/angaben-loeschen"
MELDUNG_ID = "11111111-2222-3333-4444-555555555555"
MELDUNG = {"id": MELDUNG_ID, "status": "pending", "melder_email": "anna@example.org"}


@pytest.fixture
def service():
    mock = Mock()
    mock.meldungen_einer_person = AsyncMock(return_value=[MELDUNG])
    mock.angaben_der_person_loeschen = AsyncMock(
        return_value=AngabenGeloescht(geloescht=2, angaben_entfernt=1)
    )
    return mock


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(moderation_router, prefix="/api/v1/moderation")
    app.dependency_overrides[get_settings] = lambda: Mock()
    app.dependency_overrides[get_moderation_service] = lambda: service
    return TestClient(app)


@pytest.mark.unit
class TestMeldungenEinerPerson:
    def test_melder_meldungen_gibt_die_treffer(self, client, service):
        antwort = client.post(SUCHE, headers=ADMIN, json={"email": "anna@example.org"})

        assert antwort.status_code == 200
        assert antwort.json() == {"total": 1, "reports": [MELDUNG]}
        service.meldungen_einer_person.assert_awaited_once_with(
            MelderSuche(email="anna@example.org")
        )

    def test_melder_meldungen_mit_name(self, client, service):
        antwort = client.post(SUCHE, headers=ADMIN, json={"name": "Anna Beispiel"})

        assert antwort.status_code == 200
        service.meldungen_einer_person.assert_awaited_once_with(
            MelderSuche(name="Anna Beispiel")
        )

    def test_melder_meldungen_adresse_wie_gespeichert(self, client, service):
        """Wie EmailStr beim Speichern: Rand weg, Domain klein."""
        client.post(SUCHE, headers=ADMIN, json={"email": " Anna@EXAMPLE.org "})

        service.meldungen_einer_person.assert_awaited_once_with(
            MelderSuche(email="Anna@example.org")
        )

    @pytest.mark.parametrize("koerper", [{}, {"email": "  ", "name": ""}])
    def test_melder_meldungen_ohne_angabe_ist_422(self, client, service, koerper):
        antwort = client.post(SUCHE, headers=ADMIN, json=koerper)

        assert antwort.status_code == 422
        service.meldungen_einer_person.assert_not_awaited()

    def test_melder_meldungen_zu_lange_angaben_sind_422(self, client):
        zu_lang = [
            {"email": "a" * (MELDER_EMAIL_MAX + 1)},
            {"name": "a" * (MELDER_NAME_MAX + 1)},
        ]
        for koerper in zu_lang:
            assert client.post(SUCHE, headers=ADMIN, json=koerper).status_code == 422

    def test_melder_meldungen_fehler_ohne_angaben_in_der_antwort(self, client, service):
        service.meldungen_einer_person.side_effect = RuntimeError("anna@example.org")

        antwort = client.post(SUCHE, headers=ADMIN, json={"email": "anna@example.org"})

        assert antwort.status_code == 500
        assert "anna" not in antwort.text


@pytest.mark.unit
class TestAngabenLoeschen:
    def test_melder_angaben_loeschen_nennt_die_zahlen(self, client, service):
        antwort = client.post(
            LOESCHEN,
            headers=ADMIN,
            json={"email": "anna@example.org", "meldung_ids": [MELDUNG_ID]},
        )

        assert antwort.status_code == 200
        assert antwort.json() == {"geloescht": 2, "angaben_entfernt": 1}
        service.angaben_der_person_loeschen.assert_awaited_once_with(
            MelderSuche(email="anna@example.org"),
            [uuid.UUID(MELDUNG_ID)],
            dieselbe_person=False,
        )

    def test_melder_angaben_loeschen_nur_name_braucht_bestaetigung(
        self, client, service
    ):
        """Nach einer Suche nur mit dem Namen koennen die Treffer verschiedene
        Personen sein: ohne Bestaetigung des Admins kein Loeschen."""
        koerper = {"name": "Anna Beispiel", "meldung_ids": [MELDUNG_ID]}

        ohne = client.post(LOESCHEN, headers=ADMIN, json=koerper)
        assert ohne.status_code == 422
        service.angaben_der_person_loeschen.assert_not_awaited()

        mit = client.post(
            LOESCHEN, headers=ADMIN, json={**koerper, "dieselbe_person": True}
        )
        assert mit.status_code == 200
        service.angaben_der_person_loeschen.assert_awaited_once_with(
            MelderSuche(name="Anna Beispiel"),
            [uuid.UUID(MELDUNG_ID)],
            dieselbe_person=True,
        )

    def test_melder_angaben_loeschen_ohne_angabe_ist_422(self, client, service):
        antwort = client.post(
            LOESCHEN, headers=ADMIN, json={"meldung_ids": [MELDUNG_ID]}
        )

        assert antwort.status_code == 422
        service.angaben_der_person_loeschen.assert_not_awaited()

    @pytest.mark.parametrize("ids", [[], ["keine-uuid"], None])
    def test_melder_angaben_loeschen_braucht_die_gesehenen_meldungen(
        self, client, service, ids
    ):
        koerper = {"email": "anna@example.org"}
        if ids is not None:
            koerper["meldung_ids"] = ids

        antwort = client.post(LOESCHEN, headers=ADMIN, json=koerper)

        assert antwort.status_code == 422
        service.angaben_der_person_loeschen.assert_not_awaited()
