"""
Die Stimmen fuer die Guete (#427), gegen ein echtes PostgreSQL: je Beitrag aus einer
Abfrage, ohne ausgenommene Kennungen. Wegwerf-Schema aus der Fixture ``datenbank``
von ``test_loeschkommando.py``.
"""

import uuid

import pytest

from repositories.vote_repository import VoteRepository
from tests.integration.test_loeschkommando import datenbank  # noqa: F401
from tests.integration.test_punkte_quellen import _stimme

pytestmark = pytest.mark.integration


def test_stimmen_je_beitrag_ohne_ausgenommene(datenbank):  # noqa: F811
    repo = VoteRepository(datenbank)
    eins, zwei, ohne = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    _stimme(datenbank, "bo-2", eins, "like")
    _stimme(datenbank, "start-9", eins, "like")
    _stimme(datenbank, "ali-3", zwei, "dislike")
    _stimme(datenbank, "bo-2", uuid.uuid4(), "like")

    stimmen = repo.stimmen_je_beitrag([eins, zwei, ohne], {"start-9"})

    assert stimmen == {
        str(eins): [("bo-2", "like")],
        str(zwei): [("ali-3", "dislike")],
    }
    assert len(repo.stimmen_je_beitrag([eins], ())[str(eins)]) == 2
    assert repo.stimmen_je_beitrag([], {"start-9"}) == {}
