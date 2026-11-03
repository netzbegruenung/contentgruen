"""
Varianten (#356) gegen ein echtes PostgreSQL: die Verknuepfung "beruht auf"
festhalten, je Original zaehlen und loesen. Wegwerf-Schema aus der Fixture
``datenbank`` von ``test_loeschkommando.py``.
"""

import uuid

import pytest

from repositories.varianten_repository import VariantenRepository
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

pytestmark = pytest.mark.integration


class TestVariantenRepository:
    def test_zaehlt_je_original_und_listet_die_varianten(self, datenbank):  # noqa: F811
        repo = VariantenRepository(datenbank)
        original, anderes, ohne = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        erste, zweite, dritte = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

        repo.festhalten(erste, original)
        repo.festhalten(zweite, original)
        repo.festhalten(dritte, anderes)

        assert repo.anzahl_je_original([original, anderes, ohne]) == {
            original: 2,
            anderes: 1,
        }
        assert set(repo.varianten_von(original)) == {erste, zweite}
        assert repo.varianten_von(ohne) == []

    def test_eine_variante_hat_genau_ein_original(self, datenbank):  # noqa: F811
        repo = VariantenRepository(datenbank)
        original, anderes, variante = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

        repo.festhalten(variante, original)
        repo.festhalten(variante, anderes)

        assert repo.anzahl_je_original([original, anderes]) == {original: 1}

    def test_entfernen_loest_nur_diese_variante(self, datenbank):  # noqa: F811
        repo = VariantenRepository(datenbank)
        original, erste, zweite = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        repo.festhalten(erste, original)
        repo.festhalten(zweite, original)

        repo.variante_entfernen(erste)

        assert repo.varianten_von(original) == [zweite]
        assert repo.anzahl_je_original([]) == {}
