"""
"Meine Beitraege" liefert nur ausformulierte Beitraege.

Beim Beitragen entstehen nebenbei Eintraege, die der Person zugeordnet sind, aber
keine Beitraege sind: die beantwortete Aussage und die Herkunftsangaben. Liste und
Gesamtzahl muessen beide auf Kommentar, Hintergrundinfo, Bild und Post eingegrenzt
sein - sonst stimmt der Paginator nicht zur Liste.

Die Beitragskarte braucht ausserdem Titel, Bildadresse und Nutzung. Titel und
Bildadresse stehen im Qdrant-Payload, die Nutzung kommt aus PostgreSQL.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import contribution as contribution_module
from api.v1.contribution import AUSFORMULIERTE_TYPEN
from api.v1.contribution import router as contribution_router
from dependencies import get_settings
from dtos.contribution import ContributionEntry
from tests.conftest import create_base_content_fields

URL = "/api/v1/contribution/getContributionsOfUser"


def beitrag(**felder) -> ContributionEntry:
    return ContributionEntry.model_validate(
        {
            "id": str(uuid.uuid4()),
            "text": "Text",
            "content_type": "commentary",
            **create_base_content_fields(original_author="person-1"),
            **felder,
        }
    )


@pytest.fixture
def repository():
    repo = MagicMock()
    repo.getByAuthor = AsyncMock(return_value=[])
    repo.getCountByAuthor = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def nutzung():
    service = MagicMock()
    service.enrich_content_with_usage.side_effect = lambda eintraege: [
        {**eintrag, "usage_count": 7} for eintrag in eintraege
    ]
    return service


@pytest.fixture
def client(repository, nutzung):
    app = FastAPI()
    app.include_router(contribution_router, prefix="/api/v1/contribution")
    app.dependency_overrides[get_settings] = lambda: Mock()

    factory = MagicMock()
    factory.create_content_repository.return_value = repository
    with patch.object(
        contribution_module, "QdrantRepositoryFactory", return_value=factory
    ), patch.object(contribution_module, "get_usage_service", return_value=nutzung):
        yield TestClient(app)


def test_liste_und_zaehlung_nur_fuer_ausformulierte_typen(client, repository):
    response = client.get(URL, headers={"X-User": "person-1"})

    assert response.status_code == 200
    erwartet = {"commentary", "generic_text", "image", "post"}
    liste = repository.getByAuthor.call_args.kwargs
    zaehlung = repository.getCountByAuthor.call_args.kwargs
    assert liste["user_id"] == "person-1"
    assert set(liste["content_types"]) == erwartet
    assert zaehlung["user_id"] == "person-1"
    assert set(zaehlung["content_types"]) == erwartet


def test_aussage_und_herkunft_sind_nicht_dabei():
    assert "statement" not in AUSFORMULIERTE_TYPEN
    assert "reference" not in AUSFORMULIERTE_TYPEN


def test_liest_mit_dem_modell_der_beitragskarte(client, repository):
    client.get(URL, headers={"X-User": "person-1"})

    assert (
        repository.getByAuthor.call_args.kwargs["eintrag_modell"] is ContributionEntry
    )


def test_liefert_titel_bildadresse_und_nutzung(client, repository):
    repository.getByAuthor.return_value = [
        beitrag(title="Wärmepumpe lohnt sich auch im Altbau"),
        beitrag(
            content_type="image",
            title="Solardach",
            image_url="https://example.org/dach.jpg",
        ),
    ]
    repository.getCountByAuthor.return_value = 2

    daten = client.get(URL, headers={"X-User": "person-1"}).json()

    assert daten["results_count"] == 2
    assert daten["total_records_count"] == 2
    kommentar, bild = daten["results"]
    assert kommentar["title"] == "Wärmepumpe lohnt sich auch im Altbau"
    assert kommentar["image_url"] is None
    assert bild["title"] == "Solardach"
    assert bild["image_url"] == "https://example.org/dach.jpg"
    assert kommentar["usage_count"] == 7
    assert bild["usage_count"] == 7


def test_liest_usage_count_null_aus_dem_payload_als_null():
    assert beitrag(usage_count=None).usage_count == 0


def test_payload_mit_usage_count_null_liefert_die_liste(client, repository):
    repository.getByAuthor.return_value = [beitrag(usage_count=None)]
    repository.getCountByAuthor.return_value = 1

    response = client.get(URL, headers={"X-User": "person-1"})

    assert response.status_code == 200
    assert response.json()["results"][0]["usage_count"] == 7


def test_nutzung_wird_fuer_alle_eintraege_einer_seite_nachgetragen(
    client, repository, nutzung
):
    eintraege = [beitrag(), beitrag()]
    repository.getByAuthor.return_value = eintraege

    client.get(URL, headers={"X-User": "person-1"})

    uebergeben = nutzung.enrich_content_with_usage.call_args.args[0]
    assert [eintrag["id"] for eintrag in uebergeben] == [e.id for e in eintraege]
