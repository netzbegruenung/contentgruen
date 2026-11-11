"""
Der Nutzungszaehler und die eigene Kopie.

Der Zaehler sagt, wie oft andere einen Beitrag brauchbar fanden. Wer den eigenen
Text kopiert, erhoeht ihn deshalb nicht. Geprueft wird das serverseitig an
``X-User``, den das BFF setzt (IdentityHeaderTransform.cs) und ein Client nicht
faelschen kann.
"""

import asyncio
import uuid
from datetime import datetime, time, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from api.v1 import usage as usage_module
from api.v1.usage import router as usage_router
from dependencies import get_beitrag_laden
from services.beitrag_laden import BeitragUnlesbar, beitrag_laden
from core.config import Settings
from dependencies import get_settings
from services.entdoppelung import pruefwert
from repositories.art9_einwilligung_repository import Art9Einwilligung

BEITRAG_ID = "11111111-1111-4111-8111-111111111111"
AUTORIN = "kim-1"
STARTKONTO = "start-9"


def einstellungen() -> Settings:
    return Settings(startkonten=STARTKONTO, punkte_aktiv=True)


@pytest.fixture
def dienst():
    """Der Usage-Service als Mock; der Zaehler steht auf 4."""
    dienst = Mock()
    dienst.track_content_usage.return_value = True
    dienst.get_content_usage.return_value = 4
    return dienst


@pytest.fixture
def client(dienst, muster):
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = einstellungen

    async def laden(content_id):
        if str(content_id) != BEITRAG_ID:
            return None
        return SimpleNamespace(id=content_id, original_author=AUTORIN)

    app.dependency_overrides[get_beitrag_laden] = lambda: laden
    with patch.object(
        usage_module, "get_usage_service", return_value=dienst
    ), patch.object(usage_module, "get_muster_hinweise_service", return_value=muster):
        yield TestClient(app)


@pytest.fixture
def muster():
    return Mock()


def zaehlen(client, user=None, agent=None, adresse=None):
    kopf = {"X-User": user} if user else {}
    if agent:
        kopf["User-Agent"] = agent
    if adresse:
        kopf["X-Real-IP"] = adresse
    return client.post(
        f"/api/v1/usage/content/{BEITRAG_ID}/usage", json={}, headers=kopf
    )


class TestEigeneKopie:
    def test_fremde_kopie_zaehlt(self, client, dienst):
        antwort = zaehlen(client, "bo-2")

        assert antwort.status_code == 200
        assert antwort.json()["usage_count"] == 4
        dienst.track_content_usage.assert_called_once()

    def test_anonyme_kopie_zaehlt(self, client, dienst):
        assert zaehlen(client).status_code == 200
        assert zaehlen(client, "anonymous").status_code == 200
        assert dienst.track_content_usage.call_count == 2

    def test_eigene_kopie_zaehlt_nicht(self, client, dienst):
        antwort = zaehlen(client, AUTORIN)

        assert antwort.status_code == 200
        assert antwort.json()["success"] is True
        assert antwort.json()["usage_count"] == 4
        dienst.track_content_usage.assert_not_called()


class TestStartkonto:
    """Ein Startkonto vergibt keine Nutzung (GLOSSARY.md "Startkonto", #352)."""

    def test_nutzung_durch_startkonto_zaehlt_nicht(self, client, dienst, muster):
        antwort = zaehlen(client, STARTKONTO)

        assert antwort.status_code == 200
        assert antwort.json()["success"] is True
        assert antwort.json()["usage_count"] == 4
        dienst.track_content_usage.assert_not_called()
        muster.nutzung_melden.assert_not_called()


class TestEntdoppelung:
    """Fuer Punkte und "oft genutzt" zaehlt eine Nutzung je Person, Beitrag und Tag."""

    def test_angemeldete_nutzung_bekommt_pruefwert_der_person(self, client, dienst):
        zaehlen(client, "bo-2", agent="Browser A")
        zaehlen(client, "bo-2", agent="Browser B")

        erster, zweiter = [
            c.kwargs["pruefwert"] for c in dienst.track_content_usage.call_args_list
        ]
        assert erster and erster == zweiter

    def test_besucher_bekommt_pruefwert_des_tagespseudonyms(self, client, dienst):
        """Ohne Sitzungskennung (#446): Besucher unterscheidet das Besuchermerkmal,
        also der Anschluss; der User-Agent geht nicht ein (#495)."""
        zaehlen(client, "anonymous", agent="Browser A", adresse="198.51.100.5")
        zaehlen(client, "anonymous", agent="Browser B", adresse="198.51.100.5")
        zaehlen(client, "anonymous", agent="Browser A", adresse="198.51.100.6")

        pruefwerte = [
            c.kwargs["pruefwert"] for c in dienst.track_content_usage.call_args_list
        ]
        assert pruefwerte[0] and pruefwerte[0] == pruefwerte[1]
        assert pruefwerte[2] and pruefwerte[2] != pruefwerte[0]

    def test_pruefwert_und_tag_gehoeren_zum_selben_tag(self, client, dienst):
        zaehlen(client, "bo-2")

        aufruf = dienst.track_content_usage.call_args
        mittag = datetime.combine(aufruf.kwargs["tag"], time(12), timezone.utc)
        assert aufruf.kwargs["pruefwert"] == pruefwert(
            "bo-2", None, uuid.UUID(BEITRAG_ID), mittag
        )

    def test_nutzung_wird_fuer_muster_gemeldet(self, client, muster):
        zaehlen(client, "bo-2")

        muster.nutzung_melden.assert_called_once()
        nutzende, autor, moment = muster.nutzung_melden.call_args.args
        assert (nutzende, autor) == ("bo-2", AUTORIN)
        assert moment.tzinfo is not None

    def test_ohne_punkte_keine_meldung_fuer_muster(self, client, muster):
        client.app.dependency_overrides[get_settings] = lambda: Settings()

        zaehlen(client, "bo-2")

        muster.nutzung_melden.assert_not_called()


class TestArt9Einwilligung:
    """
    Ohne geltende Art.-9-Einwilligung (#559): Die Kopie zaehlt am Kartenzaehler
    (Kopieren ist Lesen, #556 F489-2), aber es entsteht kein Pruefwert, also keine
    entdoppelte Nutzung und keine Punkte, und keine Meldung fuer die Muster-Hinweise.
    """

    def test_ohne_einwilligung_zaehlt_ohne_pruefwert_und_muster(
        self, client, dienst, muster, art9_einwilligung_ohne_datenbank
    ):
        art9_einwilligung_ohne_datenbank.lesen.return_value = None

        antwort = zaehlen(client, "bo-2")

        assert antwort.status_code == 200
        assert antwort.json()["usage_count"] == 4
        dienst.track_content_usage.assert_called_once()
        assert dienst.track_content_usage.call_args.kwargs["pruefwert"] is None
        muster.nutzung_melden.assert_not_called()

    def test_widerruf_wirkt_sofort_fuer_die_naechste_kopie(
        self, client, dienst, muster, art9_einwilligung_ohne_datenbank
    ):
        zaehlen(client, "bo-2")
        art9_einwilligung_ohne_datenbank.lesen.return_value = Art9Einwilligung(
            wortlaut="2026-11-05",
            eingewilligt_am=datetime(2026, 11, 5, tzinfo=timezone.utc),
            widerrufen_am=datetime(2026, 11, 5, 10, tzinfo=timezone.utc),
        )
        zaehlen(client, "bo-2")

        vorher, nachher = [
            c.kwargs["pruefwert"] for c in dienst.track_content_usage.call_args_list
        ]
        assert vorher
        assert nachher is None
        muster.nutzung_melden.assert_called_once()

    def test_einwilligung_wird_je_kopie_gefragt(
        self, client, art9_einwilligung_ohne_datenbank
    ):
        zaehlen(client, "bo-2")
        zaehlen(client, "bo-2")

        gefragt = [
            c.args[0] for c in art9_einwilligung_ohne_datenbank.lesen.call_args_list
        ]
        assert gefragt.count("bo-2") == 2

    def test_autorin_ohne_einwilligung_kein_muster_aber_pruefwert(
        self, client, dienst, muster, art9_einwilligung_ohne_datenbank
    ):
        """Ein Muster-Hinweis nennt auch die Autorin; hat sie widerrufen, keiner."""
        art9_einwilligung_ohne_datenbank.lesen.side_effect = lambda kennung: (
            None
            if kennung == AUTORIN
            else Art9Einwilligung(
                wortlaut="2026-11-05",
                eingewilligt_am=datetime(2026, 11, 5, tzinfo=timezone.utc),
                widerrufen_am=None,
            )
        )

        assert zaehlen(client, "bo-2").status_code == 200

        assert dienst.track_content_usage.call_args.kwargs["pruefwert"]
        muster.nutzung_melden.assert_not_called()

    def test_unlesbare_einwilligung_der_autorin_kein_muster(
        self, client, dienst, muster, art9_einwilligung_ohne_datenbank
    ):
        """Im Zweifel ohne Einwilligung der Autorin: Pruefwert ja, Meldung nein."""
        stand = art9_einwilligung_ohne_datenbank.lesen.return_value

        def lesen(kennung):
            if kennung == AUTORIN:
                raise RuntimeError("weg")
            return stand

        art9_einwilligung_ohne_datenbank.lesen.side_effect = lesen

        assert zaehlen(client, "bo-2").status_code == 200

        assert dienst.track_content_usage.call_args.kwargs["pruefwert"]
        muster.nutzung_melden.assert_not_called()

    def test_eigene_kopie_und_startkonto_fragen_nicht(
        self, client, art9_einwilligung_ohne_datenbank
    ):
        """Was ohnehin nicht zaehlt, braucht keine Abfrage."""
        zaehlen(client, AUTORIN)
        zaehlen(client, STARTKONTO)

        art9_einwilligung_ohne_datenbank.lesen.assert_not_called()

    def test_besucher_braucht_keine_einwilligung(
        self, client, dienst, art9_einwilligung_ohne_datenbank
    ):
        art9_einwilligung_ohne_datenbank.lesen.return_value = None

        zaehlen(client, "anonymous", agent="Browser A")

        assert dienst.track_content_usage.call_args.kwargs["pruefwert"]
        art9_einwilligung_ohne_datenbank.lesen.assert_not_called()

    def test_unlesbare_einwilligung_zaehlt_ohne_pruefwert(
        self, client, dienst, muster, art9_einwilligung_ohne_datenbank
    ):
        """Im Zweifel ohne Einwilligung: die Kopie zaehlt, mehr entsteht nicht."""
        art9_einwilligung_ohne_datenbank.lesen.side_effect = RuntimeError("weg")

        antwort = zaehlen(client, "bo-2")

        assert antwort.status_code == 200
        assert dienst.track_content_usage.call_args.kwargs["pruefwert"] is None
        muster.nutzung_melden.assert_not_called()


class TestUnbekannterBeitrag:
    def test_unbekannte_id_ist_404(self, client, dienst):
        antwort = client.post(
            "/api/v1/usage/content/22222222-2222-4222-8222-222222222222/usage",
            json={},
        )

        assert antwort.status_code == 404
        dienst.track_content_usage.assert_not_called()

    def test_kaputte_id_ist_400(self, client, dienst):
        antwort = client.post("/api/v1/usage/content/keine-uuid/usage", json={})

        assert antwort.status_code == 400
        dienst.track_content_usage.assert_not_called()


class TestUnlesbarerBeitrag:
    """
    Ein Datensatz, den Pydantic nicht validieren kann, ist kaputt - nicht abwesend.
    Weil ValidationError ein ValueError ist, waere er ohne eigenen Zweig als 404
    durchgegangen und die Kopie haette niemand gezaehlt.
    """

    def test_laden_meldet_unlesbar_statt_nicht_gefunden(self):
        class Winzig(BaseModel):
            zahl: int

        try:
            Winzig(zahl="keine Zahl")
        except ValidationError as echt:
            fehler = echt

        repository = Mock()
        repository.get = AsyncMock(side_effect=fehler)

        with pytest.raises(BeitragUnlesbar):
            asyncio.run(beitrag_laden(uuid.UUID(BEITRAG_ID), repository))

    def test_laden_meldet_fehlenden_als_none(self):
        repository = Mock()
        repository.get = AsyncMock(side_effect=ValueError("not found"))

        assert asyncio.run(beitrag_laden(uuid.UUID(BEITRAG_ID), repository)) is None

    def test_unlesbarer_beitrag_zaehlt_trotzdem(self, dienst):
        """Im Zweifel zaehlen: wem er gehoert, ist dann nicht feststellbar."""
        app = FastAPI()
        app.include_router(usage_router, prefix="/api/v1/usage")
        app.dependency_overrides[get_settings] = einstellungen

        async def kaputt(content_id):
            raise BeitragUnlesbar(str(content_id))

        app.dependency_overrides[get_beitrag_laden] = lambda: kaputt
        with patch.object(usage_module, "get_usage_service", return_value=dienst):
            client = TestClient(app)
            antwort = client.post(
                f"/api/v1/usage/content/{BEITRAG_ID}/usage",
                json={},
                headers={"X-User": AUTORIN},
            )

        assert antwort.status_code == 200
        dienst.track_content_usage.assert_called_once()


class TestKeineSitzungskennung:
    """Seit #446 haelt eine Kopie keine Sitzungskennung mehr fest."""

    def test_mitgeschickte_sitzungskennung_wird_nicht_weitergegeben(
        self, client, dienst
    ):
        """Ein alter Client schickt noch session_id mit; sie wird verworfen."""
        antwort = client.post(
            f"/api/v1/usage/content/{BEITRAG_ID}/usage",
            json={"session_id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301"},
        )

        assert antwort.status_code == 200
        _, kwargs = dienst.track_content_usage.call_args
        assert "session_id" not in kwargs
