"""
Loeschauftraege nach dem Widerruf der Art.-9-Einwilligung (DSFA R9b): Liste und
Ausfuehren (GET/POST /api/v1/moderation/loeschauftraege), dazu der Dienst
(services/loeschauftrag_service.py) mit gemocktem Repository und Qdrant. Gegen
PostgreSQL: tests/integration/test_loeschauftraege.py.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.loeschauftraege import router
from repositories.loeschauftrag_repository import (
    FRIST_TAGE,
    Loeschauftrag,
    PostgresBericht,
)
from services import loeschauftrag_service as modul
from services.loeschauftrag_service import (
    AuftragErledigt,
    AuftragUnbekannt,
    LoeschauftragService,
)

pytestmark = [pytest.mark.unit, pytest.mark.api]

BASIS = "/api/v1/moderation/loeschauftraege"
ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}
JETZT = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _auftrag(user_id="person-1", tage_alt=1, erledigt=None, auftrag_id=ID):
    angelegt = JETZT - timedelta(days=tage_alt)
    return Loeschauftrag(
        id=auftrag_id,
        user_id=user_id,
        angelegt_am=angelegt,
        frist=angelegt + timedelta(days=FRIST_TAGE),
        erledigt_am=erledigt,
    )


@pytest.fixture
def repository():
    repo = MagicMock()
    repo.offene.return_value = []
    repo.ausfuehren.return_value = PostgresBericht(einwuerfe=2, saetze=1)
    return repo


@pytest.fixture
def qdrant():
    return MagicMock(return_value=3)


@pytest.fixture
def dienst(repository, qdrant):
    return LoeschauftragService(
        repository, qdrant, lambda kennungen: {"person-1": "Anna B."}
    )


@pytest.fixture
def client(dienst, monkeypatch):
    monkeypatch.setattr(modul, "_service", dienst)
    app = FastAPI()
    app.include_router(router, prefix=BASIS)
    return TestClient(app, raise_server_exceptions=False)


def test_frist_sieben_tage():
    """Die Frist der freigegebenen Option: binnen sieben Tagen ausfuehren."""
    assert FRIST_TAGE == 7


class TestDienst:
    def test_offene_mit_name_und_ueberfaellig(self, dienst, repository):
        repository.offene.return_value = [
            _auftrag("person-1", tage_alt=8),
            _auftrag("person-2", tage_alt=1, auftrag_id=uuid.uuid4()),
        ]

        offene = dienst.offene(JETZT)

        assert [(a.user_id, a.anzeigename, a.ueberfaellig) for a in offene] == [
            ("person-1", "Anna B.", True),
            ("person-2", None, False),
        ]

    def test_ohne_offene_fragt_keine_namen(self, repository, qdrant):
        namen = MagicMock()
        LoeschauftragService(repository, qdrant, namen).offene(JETZT)

        namen.assert_not_called()

    def test_ausfuehren_erst_qdrant_dann_postgres(self, dienst, repository, qdrant):
        reihenfolge = []
        qdrant.side_effect = lambda kennung: reihenfolge.append("qdrant") or 3
        repository.ausfuehren.side_effect = lambda auftrag: (
            reihenfolge.append("postgres") or PostgresBericht(einwuerfe=2, saetze=1)
        )
        repository.laden.return_value = _auftrag()

        ergebnis = dienst.ausfuehren(ID)

        assert reihenfolge == ["qdrant", "postgres"]
        qdrant.assert_called_once_with("person-1")
        assert (ergebnis.beitraege, ergebnis.einwuerfe, ergebnis.saetze) == (3, 2, 1)

    def test_scheitert_qdrant_bleibt_der_auftrag_offen(
        self, dienst, repository, qdrant
    ):
        repository.laden.return_value = _auftrag()
        qdrant.side_effect = RuntimeError("Qdrant weg")

        with pytest.raises(RuntimeError):
            dienst.ausfuehren(ID)

        repository.ausfuehren.assert_not_called()

    def test_unbekannt(self, dienst, repository):
        repository.laden.return_value = None

        with pytest.raises(AuftragUnbekannt):
            dienst.ausfuehren(ID)

    def test_erledigt_nicht_noch_einmal(self, dienst, repository, qdrant):
        repository.laden.return_value = _auftrag(erledigt=JETZT)

        with pytest.raises(AuftragErledigt):
            dienst.ausfuehren(ID)

        qdrant.assert_not_called()


class TestApi:
    def test_nur_fuer_admins(self, client, repository):
        assert client.get(BASIS).status_code == 401
        assert client.get(BASIS, headers={"X-User": "person-1"}).status_code == 403
        antwort = client.post(
            f"{BASIS}/{ID}/ausfuehren", headers={"X-User": "person-1"}
        )
        assert antwort.status_code == 403
        repository.ausfuehren.assert_not_called()

    def test_liste(self, client, repository):
        repository.offene.return_value = [_auftrag(tage_alt=8)]

        antwort = client.get(BASIS, headers=ADMIN)

        assert antwort.status_code == 200
        daten = antwort.json()
        assert daten["frist_tage"] == 7
        (auftrag,) = daten["auftraege"]
        assert auftrag["id"] == str(ID)
        assert auftrag["user_id"] == "person-1"
        assert auftrag["anzeigename"] == "Anna B."
        assert auftrag["ueberfaellig"] is True

    def test_liste_fehler_500(self, client, repository):
        repository.offene.side_effect = RuntimeError("Datenbank weg")

        assert client.get(BASIS, headers=ADMIN).status_code == 500

    def test_ausfuehren(self, client, repository):
        repository.laden.return_value = _auftrag()

        antwort = client.post(f"{BASIS}/{ID}/ausfuehren", headers=ADMIN)

        assert antwort.status_code == 200
        assert antwort.json() == {"beitraege": 3, "einwuerfe": 2, "saetze": 1}

    def test_ausfuehren_unbekannt_404(self, client, repository):
        repository.laden.return_value = None

        assert client.post(f"{BASIS}/{ID}/ausfuehren", headers=ADMIN).status_code == 404

    def test_ausfuehren_erledigt_409(self, client, repository):
        repository.laden.return_value = _auftrag(erledigt=JETZT)

        assert client.post(f"{BASIS}/{ID}/ausfuehren", headers=ADMIN).status_code == 409

    def test_ausfuehren_fehler_500(self, client, repository, qdrant):
        repository.laden.return_value = _auftrag()
        qdrant.side_effect = RuntimeError("Qdrant weg")

        assert client.post(f"{BASIS}/{ID}/ausfuehren", headers=ADMIN).status_code == 500
