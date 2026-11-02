"""
Fehlerantworten der API tragen keinen Fehlertext einer Ausnahme (#486).

Ein 500er aus Datenbank, Qdrant oder einer Bibliothek bekommt einen festen Text; sonst
stuenden Interna und oft Eingabewerte in der Antwort. Hinaus geht nur der Text eines
eigenen Validierungsfehlers (core/fehler.py), der fuer Aufrufer formuliert ist, und
zwar ueber ``e.meldung``. Ein beliebiger ValueError ist kein solcher Fehler.

Der Waechter ist das Gegenstueck zu tests/unit/core/test_kein_fehlertext_im_log.py, fuer
Antworten statt Logzeilen: In einem ``except``-Block unter api/ darf die Ausnahme nur als
``type(e)``, ``e.meldung`` oder ``raise ... from e`` vorkommen (Log-Aufrufe prueft der
andere Waechter). Ein Fehlertext, der erst gespeichert und spaeter ausgeliefert wird, den
sieht er nicht.
"""

import ast
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.image import router as image_router
from api.v1.statement import router as statement_router
from api.v1.voting import router as voting_router
from core.fehler import INTERNER_FEHLER, UNGUELTIGE_ANFRAGE, Validierungsfehler
from dependencies import (
    get_aussage_themen_service,
    get_image_service,
    get_settings,
    get_voting_service,
)
from domain.themen import ThemaUngueltig
from services.content.base_content_service import BaseContentService

pytestmark = pytest.mark.unit

API = Path(__file__).resolve().parents[3] / "api"
ERLAUBTE_ATTRIBUTE = {"meldung"}
GEHEIM = "host=db-intern password=geheim eingabe=Solardach"


def _ist_log_aufruf(knoten: ast.AST) -> bool:
    return (
        isinstance(knoten, ast.Call)
        and isinstance(knoten.func, ast.Attribute)
        and "log" in ast.unparse(knoten.func.value).lower()
    )


def _verwendungen(knoten: ast.AST, name: str) -> list[ast.Name]:
    """``name`` in ``knoten``, ausser in type(name), name.meldung und Log-Aufrufen."""
    if _ist_log_aufruf(knoten):
        return []
    if (
        isinstance(knoten, ast.Call)
        and isinstance(knoten.func, ast.Name)
        and knoten.func.id == "type"
    ):
        return []
    if (
        isinstance(knoten, ast.Attribute)
        and knoten.attr in ERLAUBTE_ATTRIBUTE
        and isinstance(knoten.value, ast.Name)
    ):
        return []
    if isinstance(knoten, ast.Raise):
        return _verwendungen(knoten.exc, name) if knoten.exc else []
    if isinstance(knoten, ast.Name):
        return [knoten] if knoten.id == name else []
    gefunden: list[ast.Name] = []
    for kind in ast.iter_child_nodes(knoten):
        gefunden.extend(_verwendungen(kind, name))
    return gefunden


def _fundstellen() -> list[str]:
    funde = []
    for pfad in sorted(API.rglob("*.py")):
        baum = ast.parse(pfad.read_text(encoding="utf-8"), filename=str(pfad))
        for handler in ast.walk(baum):
            if not isinstance(handler, ast.ExceptHandler) or not handler.name:
                continue
            for teil in handler.body:
                funde.extend(
                    f"{pfad.relative_to(API)}:{n.lineno}"
                    for n in _verwendungen(teil, handler.name)
                )
    return sorted(set(funde))


class TestWaechter:
    def test_keine_fehlerantwort_traegt_den_fehlertext_einer_ausnahme(self):
        assert _fundstellen() == []

    def test_waechter_erkennt_die_ausnahme_in_der_antwort(self, tmp_path, monkeypatch):
        """Gegenprobe: der Waechter schlaegt an, wo er soll, und nur dort."""
        (tmp_path / "beispiel.py").write_text(
            "def f(logger):\n"
            "    try:\n"
            "        pass\n"
            "    except ValueError as e:\n"
            "        raise HTTPException(status_code=400, detail=str(e))\n"
            "    except RuntimeError as e:\n"
            "        raise HTTPException(500, detail=f'kaputt: {e}')\n"
            "    except KeyError as e:\n"
            "        return {'error': e}\n"
            "    except Validierungsfehler as e:\n"
            "        logger.warning(f'{type(e).__name__}', exc_info=e)\n"
            "        raise HTTPException(status_code=422, detail=e.meldung) from e\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(sys.modules[__name__], "API", tmp_path)

        assert _fundstellen() == ["beispiel.py:5", "beispiel.py:7", "beispiel.py:9"]


class TestValidierungsfehler:
    def test_meldung_ist_der_formulierte_text(self):
        assert Validierungsfehler("Begruendung fehlt").meldung == "Begruendung fehlt"

    def test_ist_ein_value_error(self):
        """Bestehende ``except ValueError`` fangen ihn weiter."""
        assert isinstance(Validierungsfehler("x"), ValueError)


@pytest.fixture
def bild_client():
    dienst = Mock(spec=BaseContentService)
    dienst.get_all = AsyncMock(side_effect=RuntimeError(GEHEIM))
    app = FastAPI()
    app.include_router(image_router, prefix="/api/v1/image")
    app.dependency_overrides[get_image_service] = lambda: dienst
    return TestClient(app)


@pytest.fixture
def stimm_dienst():
    return MagicMock()


@pytest.fixture
def stimm_client(stimm_dienst):
    repository = MagicMock()
    repository.get = AsyncMock(return_value=object())
    fabrik = Mock()
    fabrik.return_value.create_content_repository.return_value = repository
    app = FastAPI()
    app.include_router(voting_router, prefix="/api/v1/voting")
    app.dependency_overrides[get_settings] = lambda: Mock()
    app.dependency_overrides[get_voting_service] = lambda: stimm_dienst
    with patch(
        "repositories.implementations.qdrant.qdrant_repository_factory.QdrantRepositoryFactory",
        fabrik,
    ):
        yield TestClient(app)


class TestFehlerantworten:
    def test_500_hat_einen_festen_text(self, bild_client):
        antwort = bild_client.get("/api/v1/image/getAll")

        assert antwort.status_code == 500
        assert antwort.json() == {"detail": INTERNER_FEHLER}

    def test_400_aus_beliebigem_value_error_hat_einen_festen_text(
        self, stimm_client, stimm_dienst
    ):
        stimm_dienst.set_like.side_effect = ValueError(GEHEIM)

        antwort = stimm_client.put(
            f"/api/v1/voting/content/{uuid.uuid4()}/like", headers={"X-User": "k-1"}
        )

        assert antwort.status_code == 400
        assert antwort.json() == {"detail": UNGUELTIGE_ANFRAGE}

    def test_400_aus_eigenem_validierungsfehler_traegt_seinen_text(
        self, stimm_client, stimm_dienst
    ):
        stimm_dienst.set_like.side_effect = Validierungsfehler("Bitte erneut versuchen")

        antwort = stimm_client.put(
            f"/api/v1/voting/content/{uuid.uuid4()}/like", headers={"X-User": "k-1"}
        )

        assert antwort.status_code == 400
        assert antwort.json() == {"detail": "Bitte erneut versuchen"}

    def test_503_ohne_fehlertext_der_verbindung(self, stimm_client, stimm_dienst):
        stimm_dienst.remove_like.side_effect = ConnectionError(GEHEIM)

        antwort = stimm_client.delete(
            f"/api/v1/voting/content/{uuid.uuid4()}/like", headers={"X-User": "k-1"}
        )

        assert antwort.status_code == 503
        assert GEHEIM not in antwort.text

    def test_422_aus_eigenem_validierungsfehler_traegt_seinen_text(self):
        dienst = MagicMock()
        dienst.zuordnen = AsyncMock(side_effect=ThemaUngueltig("Unbekanntes Thema"))
        app = FastAPI()
        app.include_router(statement_router, prefix="/api/v1/statement")
        app.dependency_overrides[get_aussage_themen_service] = lambda: dienst

        antwort = TestClient(app).put(
            "/api/v1/statement/themen/zuordnen",
            json={"statement_id": str(uuid.uuid4()), "themen": ["windkraft"]},
            headers={"X-User": "k-1"},
        )

        assert antwort.status_code == 422
        assert antwort.json() == {"detail": "Unbekanntes Thema"}
