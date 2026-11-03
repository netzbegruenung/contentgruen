"""
Nie benutzte Konten aus Einladungen loeschen (#538).

Keycloak ist eine Attrappe hinter httpx.MockTransport mit einer Handvoll Konten. Nie
benutzt ist ein Konto, das noch auf seine Pflichtaktion wartet, die Mail-Adresse nie
bestaetigt hat, kein Passwort hat und mit keinem Identity Provider verknuepft ist.
"""

from datetime import datetime, timezone

import httpx
import pytest

from infrastructure.keycloak_konten import KeycloakKonten

pytestmark = pytest.mark.unit

BASIS = "https://login.example.org"
ADMIN = "/admin/realms/gutgesagt/users"
GRENZE = datetime(2026, 10, 1, tzinfo=timezone.utc)
VORHER = int(datetime(2026, 9, 30, tzinfo=timezone.utc).timestamp() * 1000)
NACHHER = int(datetime(2026, 10, 2, tzinfo=timezone.utc).timestamp() * 1000)


def _konto(kennung, angelegt=VORHER, **extra):
    konto = {
        "id": kennung,
        "createdTimestamp": angelegt,
        "emailVerified": False,
        "requiredActions": ["TERMS_AND_CONDITIONS"],
    }
    konto.update(extra)
    return konto


class Keycloak:
    """Haelt Konten, Passwoerter und Verknuepfungen; zeichnet die Anfragen auf."""

    def __init__(self, konten, passwort=(), verknuepft=(), von_hand_geloescht=()):
        self.konten = {k["id"]: k for k in konten}
        self.passwort = set(passwort)
        self.verknuepft = set(verknuepft)
        self.von_hand_geloescht = set(von_hand_geloescht)
        self.anfragen: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.anfragen.append(request)
        pfad = request.url.path
        if pfad.endswith("/protocol/openid-connect/token"):
            return httpx.Response(200, json={"access_token": "tok"})
        if request.method == "GET" and pfad == ADMIN:
            p = request.url.params
            treffer = [
                k
                for k in self.konten.values()
                if p.get("emailVerified") != "false" or not k["emailVerified"]
            ]
            erste = int(p.get("first", 0))
            anzahl = int(p["max"])
            return httpx.Response(200, json=treffer[erste : erste + anzahl])
        kennung = pfad.removeprefix(ADMIN + "/").split("/")[0]
        if pfad.endswith("/credentials"):
            typen = ["password"] if kennung in self.passwort else []
            return httpx.Response(200, json=[{"type": t} for t in typen])
        if pfad.endswith("/federated-identity"):
            idp = [{"identityProvider": "netzbegruenung"}]
            return httpx.Response(200, json=idp if kennung in self.verknuepft else [])
        if request.method == "DELETE":
            if kennung in self.von_hand_geloescht:
                return httpx.Response(404)
            self.konten.pop(kennung, None)
            return httpx.Response(204)
        return httpx.Response(404)

    def geloescht(self):
        return [
            r.url.path.rsplit("/", 1)[-1] for r in self.anfragen if r.method == "DELETE"
        ]


def _konten(keycloak):
    return KeycloakKonten(
        basis_url=BASIS,
        realm="gutgesagt",
        client_id="gutgesagt-einladungen",
        client_secret="geheim",
        transport=httpx.MockTransport(keycloak),
    )


def test_loescht_nie_benutztes_konto_vor_der_grenze():
    keycloak = Keycloak([_konto("alt"), _konto("jung", angelegt=NACHHER)])

    anzahl = _konten(keycloak).nie_benutzte_loeschen(GRENZE)

    assert anzahl == 1
    assert keycloak.geloescht() == ["alt"]


def test_benutzte_konten_bleiben():
    keycloak = Keycloak(
        [
            _konto("mit-passwort"),
            _konto("verknuepft"),
            _konto("bestaetigt", emailVerified=True),
            _konto("ohne-pflichtaktion", requiredActions=[]),
        ],
        passwort=["mit-passwort"],
        verknuepft=["verknuepft"],
    )

    anzahl = _konten(keycloak).nie_benutzte_loeschen(GRENZE)

    assert anzahl == 0
    assert keycloak.geloescht() == []


def test_liest_alle_seiten_bevor_es_loescht(monkeypatch):
    # Loeschen waehrend des Blaetterns verschoebe die Seiten, Konten fielen durch.
    monkeypatch.setattr("infrastructure.keycloak_konten.KONTEN_JE_SEITE", 2)
    keycloak = Keycloak([_konto(f"k{i}") for i in range(5)])

    anzahl = _konten(keycloak).nie_benutzte_loeschen(GRENZE)

    assert anzahl == 5
    assert sorted(keycloak.geloescht()) == [f"k{i}" for i in range(5)]
    methoden = [r.method for r in keycloak.anfragen]
    assert "GET" not in methoden[methoden.index("DELETE") :]


def test_schon_geloeschtes_konto_haelt_den_lauf_nicht_auf():
    # Zwischen Lesen und Loeschen hat jemand "weg" von Hand geloescht.
    keycloak = Keycloak([_konto("weg"), _konto("da")], von_hand_geloescht=["weg"])

    _konten(keycloak).nie_benutzte_loeschen(GRENZE)

    assert keycloak.geloescht() == ["weg", "da"]


def test_fragt_nur_unbestaetigte_konten_ab():
    keycloak = Keycloak([])

    _konten(keycloak).nie_benutzte_loeschen(GRENZE)

    liste = next(r for r in keycloak.anfragen if r.url.path == ADMIN)
    assert liste.url.params["emailVerified"] == "false"
    assert liste.url.params["briefRepresentation"] == "false"
