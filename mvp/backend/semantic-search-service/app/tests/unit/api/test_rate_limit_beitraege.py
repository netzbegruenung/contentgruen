"""
Das Anlegen von Beitraegen ist je Person gedrosselt (RateLimitMiddleware).

Der Post hat mit #297 ein Formular bekommen und zaehlt damit zu den Wegen, auf
denen jemand schnell viele Beitraege anlegen kann.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.rate_limit import RateLimitMiddleware


def _client(pfad: str) -> TestClient:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, requests_per_minute=2)

    @app.post(pfad)
    async def anlegen():
        return {"ok": True}

    return TestClient(app)


@pytest.mark.parametrize(
    "pfad", ["/api/v1/post/addPost", "/api/v1/commentary/addCommentary"]
)
def test_anlegen_ueber_dem_limit_ist_429(pfad):
    client = _client(pfad)
    kopf = {"X-User": "alice"}

    antworten = [client.post(pfad, headers=kopf).status_code for _ in range(3)]

    assert antworten == [200, 200, 429]


def test_andere_person_hat_ein_eigenes_limit():
    pfad = "/api/v1/post/addPost"
    client = _client(pfad)
    for _ in range(2):
        client.post(pfad, headers={"X-User": "alice"})

    assert client.post(pfad, headers={"X-User": "bob"}).status_code == 200
