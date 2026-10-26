"""
Dieselben Faelle wie tests/unit/services/test_beitraege_anonymisieren.py, aber gegen
einen echten Qdrant: Der Speicher-Modus von qdrant_client wertet Filter wie
``authors[].name`` selbst aus, hier tut es der Server. Eine eigene Collection je
Lauf, die der Test wieder abraeumt.
"""

import pytest
from qdrant_client import QdrantClient

from tests.integration.conftest import QDRANT_URL, requires_qdrant
from tests.unit.services import test_beitraege_anonymisieren as faelle

pytestmark = [pytest.mark.integration, requires_qdrant]


@pytest.fixture
def client():
    client = QdrantClient(url=QDRANT_URL, timeout=10, check_compatibility=False)
    faelle.punkte_anlegen(client)
    yield client
    client.delete_collection(faelle.COLLECTION)


class TestAnonymisierenGegenQdrant(faelle.TestAnonymisieren):
    pass
