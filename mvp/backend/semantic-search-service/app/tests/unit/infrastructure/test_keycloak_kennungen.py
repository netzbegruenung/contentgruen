"""
Kennungen umstellen (#487): Zuordnung alt -> neu aus dem Realm von Gut gesagt und
Konten mit Verknuepfung zum Identity Provider vorab anlegen.

Keycloak ist eine Attrappe hinter httpx.MockTransport: Ein Konto im Realm ist mit
der Netzbegruenung verknuepft, die Kennung dort ist die alte.
"""

import json

import httpx
import pytest

from infrastructure.keycloak_konten import PFLICHTAKTIONEN, KeycloakKonten

pytestmark = pytest.mark.unit

BASIS = "https://login.example.org"
ADMIN = "/admin/realms/gutgesagt/users"
ALT = "alt-netzbegruenung-1"
NEU = "8a0c6f6e-0000-4000-8000-000000000001"
ANGELEGT = "8a0c6f6e-0000-4000-8000-000000000002"


class Keycloak:
    def __init__(self, verknuepft=None, vergeben=(), abgelaufen=0):
        # (Identity Provider, Kennung dort) -> Konto im Realm
        self.verknuepft = dict(verknuepft or {})
        self.vergeben = set(vergeben)
        self.anfragen: list[httpx.Request] = []
        # So viele Admin-Anfragen antworten 401, als sei das Token abgelaufen.
        self.abgelaufen = abgelaufen

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.anfragen.append(request)
        pfad = request.url.path
        if pfad.endswith("/protocol/openid-connect/token"):
            return httpx.Response(200, json={"access_token": "tok"})
        if pfad == ADMIN and self.abgelaufen:
            self.abgelaufen -= 1
            return httpx.Response(401)
        if pfad == ADMIN and request.method == "GET":
            p = request.url.params
            konto = self.verknuepft.get((p.get("idpAlias"), p.get("idpUserId")))
            return httpx.Response(200, json=[{"id": konto}] if konto else [])
        if pfad == ADMIN and request.method == "POST":
            if json.loads(request.content)["email"] in self.vergeben:
                return httpx.Response(409)
            return httpx.Response(
                201, headers={"Location": f"{BASIS}{ADMIN}/{ANGELEGT}"}
            )
        return httpx.Response(404)

    def angelegt(self):
        return [
            json.loads(r.content)
            for r in self.anfragen
            if r.method == "POST" and r.url.path == ADMIN
        ]


def _konten(keycloak):
    return KeycloakKonten(
        basis_url=BASIS,
        realm="gutgesagt",
        client_id="gutgesagt-einladungen",
        client_secret="geheim",
        transport=httpx.MockTransport(keycloak),
    )


class TestKennungenZuordnen:
    def test_ordnet_ueber_die_verknuepfung_mit_dem_identity_provider_zu(self):
        keycloak = Keycloak(verknuepft={("netzbegruenung", ALT): NEU})

        zuordnung = _konten(keycloak).kennungen_zuordnen(
            "netzbegruenung", [ALT, "ohne-konto"]
        )

        assert zuordnung == {ALT: NEU}

    def test_verknuepfung_mit_anderem_identity_provider_zaehlt_nicht(self):
        keycloak = Keycloak(verknuepft={("gruenes-netz", ALT): NEU})

        assert _konten(keycloak).kennungen_zuordnen("netzbegruenung", [ALT]) == {}

    def test_ein_token_fuer_alle_anfragen(self):
        keycloak = Keycloak()

        _konten(keycloak).kennungen_zuordnen("netzbegruenung", ["a", "b", "c"])

        tokens = [r for r in keycloak.anfragen if r.url.path.endswith("/token")]
        assert len(tokens) == 1
        assert all(
            r.headers["Authorization"] == "Bearer tok"
            for r in keycloak.anfragen
            if r.url.path == ADMIN
        )

    def test_abgelaufenes_token_wird_einmal_erneuert(self):
        keycloak = Keycloak(verknuepft={("netzbegruenung", ALT): NEU}, abgelaufen=1)

        zuordnung = _konten(keycloak).kennungen_zuordnen("netzbegruenung", [ALT])

        assert zuordnung == {ALT: NEU}
        tokens = [r for r in keycloak.anfragen if r.url.path.endswith("/token")]
        assert len(tokens) == 2

    def test_bleibt_es_bei_401_bricht_der_lauf_ab(self):
        keycloak = Keycloak(abgelaufen=2)

        with pytest.raises(httpx.HTTPStatusError):
            _konten(keycloak).kennungen_zuordnen("netzbegruenung", [ALT])


class TestKontenVerknuepftAnlegen:
    def test_legt_konto_mit_verknuepfung_an_ohne_mail(self):
        keycloak = Keycloak()

        ergebnis = _konten(keycloak).konten_verknuepft_anlegen(
            "netzbegruenung", {ALT: "anna@example.org"}
        )

        assert ergebnis.angelegt == {ALT: ANGELEGT}
        assert ergebnis.vergeben == []
        (konto,) = keycloak.angelegt()
        assert konto["email"] == "anna@example.org"
        assert konto["emailVerified"] is True
        assert konto["requiredActions"] == PFLICHTAKTIONEN
        assert konto["federatedIdentities"] == [
            {
                "identityProvider": "netzbegruenung",
                "userId": ALT,
                "userName": "anna@example.org",
            }
        ]
        # Keine Mail "Passwort festlegen": Angemeldet wird ueber den Identity Provider.
        assert not any(
            r.url.path.endswith("/execute-actions-email") for r in keycloak.anfragen
        )

    def test_vergebene_adresse_wird_gemeldet_und_nicht_verknuepft(self):
        keycloak = Keycloak(vergeben={"anna@example.org"})

        ergebnis = _konten(keycloak).konten_verknuepft_anlegen(
            "netzbegruenung", {ALT: "anna@example.org"}
        )

        assert ergebnis.angelegt == {}
        assert ergebnis.vergeben == [ALT]

    def test_schon_verknuepfte_kennung_bekommt_kein_zweites_konto(self):
        keycloak = Keycloak(verknuepft={("netzbegruenung", ALT): NEU})

        ergebnis = _konten(keycloak).konten_verknuepft_anlegen(
            "netzbegruenung", {ALT: "anna@example.org"}
        )

        assert ergebnis.angelegt == {}
        assert keycloak.angelegt() == []
