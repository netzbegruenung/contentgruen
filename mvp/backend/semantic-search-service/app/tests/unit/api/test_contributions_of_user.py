"""
"Meine Beitraege" liefert nur ausformulierte Beitraege.

Beim Beitragen entstehen nebenbei Eintraege, die der Person zugeordnet sind, aber
keine Beitraege sind: die beantwortete Aussage und die Herkunftsangaben. Liste und
Gesamtzahl muessen beide auf Kommentar, Hintergrundinfo, Bild und Post eingegrenzt
sein - sonst stimmt der Paginator nicht zur Liste.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import contribution as contribution_module
from api.v1.contribution import AUSFORMULIERTE_TYPEN
from api.v1.contribution import router as contribution_router
from dependencies import get_settings

URL = "/api/v1/contribution/getContributionsOfUser"


@pytest.fixture
def repository():
    repo = MagicMock()
    repo.getByAuthor = AsyncMock(return_value=[])
    repo.getCountByAuthor = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def client(repository):
    app = FastAPI()
    app.include_router(contribution_router, prefix="/api/v1/contribution")
    app.dependency_overrides[get_settings] = lambda: Mock()

    factory = MagicMock()
    factory.create_content_repository.return_value = repository
    with patch.object(
        contribution_module, "QdrantRepositoryFactory", return_value=factory
    ):
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
