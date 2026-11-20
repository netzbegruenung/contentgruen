"""
Nie benutzte Konten aus Einladungen loeschen (#538).

Keycloak ist eine Attrappe hinter httpx.MockTransport mit einer Handvoll Konten. Nie
benutzt ist ein Konto, das noch auf seine Pflichtaktion wartet, kein Passwort hat, mit
keinem Identity Provider verknuepft ist und entweder die Mail-Adresse nie bestaetigt
hat oder "Passwort festlegen" noch am Konto traegt (Link bestaetigt, Passwort nie
gesetzt).
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
            treffer = list(self.konten.values())
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


def test_link_bestaetigt_aber_nie_ein_passwort_wird_geloescht():
    # Entscheidung 20.11.: Die Frist gilt auch, wenn der Link die Adresse bestaetigt
    # hat, aber nie ein Passwort kam.
    keycloak = Keycloak(
        [
            _konto(
                "abgebrochen",
                emailVerified=True,
                requiredActions=["TERMS_AND_CONDITIONS", "UPDATE_PASSWORD"],
            ),
            # Nutzungsbedingungen angenommen, dann auf der Passwortseite abgebrochen:
            # Keycloak hat TERMS_AND_CONDITIONS schon vom Konto genommen.
            _konto(
                "nach-bedingungen",
                emailVerified=True,
                requiredActions=["UPDATE_PASSWORD"],
            ),
            _konto(
                "abgebrochen-jung",
                angelegt=NACHHER,
                emailVerified=True,
                requiredActions=["TERMS_AND_CONDITIONS", "UPDATE_PASSWORD"],
            ),
        ]
    )

    anzahl = _konten(keycloak).nie_benutzte_loeschen(GRENZE)

    assert anzahl == 2
    assert keycloak.geloescht() == ["abgebrochen", "nach-bedingungen"]


def test_beta_zugang_und_vorab_angelegte_bleiben_ohne_nachfrage():
    # Beta-Zugang (#488): bestaetigt, ohne Passwort, ohne "Passwort festlegen" am
    # Konto; seine Beitraege sind schon umgezogen. Vorab angelegt (#487): bestaetigt.
    keycloak = Keycloak(
        [
            _konto("beta", emailVerified=True),
            _konto("vorab", emailVerified=True),
        ],
        verknuepft=["vorab"],
    )

    anzahl = _konten(keycloak).nie_benutzte_loeschen(GRENZE)

    assert anzahl == 0
    assert keycloak.geloescht() == []
    # Fuer sie fragt der Lauf weder Passwort noch Verknuepfung ab.
    assert [r for r in keycloak.anfragen if r.url.path.startswith(ADMIN + "/")] == []


def test_link_bestaetigt_mit_passwort_aus_passwort_vergessen_bleibt():
    keycloak = Keycloak(
        [
            _konto(
                "nachgeholt",
                emailVerified=True,
                requiredActions=["TERMS_AND_CONDITIONS", "UPDATE_PASSWORD"],
            )
        ],
        passwort=["nachgeholt"],
    )

    assert _konten(keycloak).nie_benutzte_loeschen(GRENZE) == 0
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

    anzahl = _konten(keycloak).nie_benutzte_loeschen(GRENZE)

    assert keycloak.geloescht() == ["weg", "da"]
    # "weg" hat dieser Lauf nicht geloescht; das Log zaehlt nur "da".
    assert anzahl == 1


def test_liest_alle_konten_mit_pflichtaktionen():
    keycloak = Keycloak([])

    _konten(keycloak).nie_benutzte_loeschen(GRENZE)

    liste = next(r for r in keycloak.anfragen if r.url.path == ADMIN)
    # Kein Filter emailVerified mehr: Auch bestaetigte Konten koennen faellig sein.
    assert "emailVerified" not in liste.url.params
    assert liste.url.params["briefRepresentation"] == "false"


def test_seit_0_9_8_ohne_nutzungsbedingungen_am_konto():
    """
    Konten aus Einladungen ab 0.9.8 tragen nur UPDATE_PASSWORD (PFLICHTAKTIONEN leer):
    Link nie geoeffnet wird geloescht. Ein unbestaetigtes Konto ganz ohne Pflichtaktion
    stammt aus keiner Einladung und bleibt; ebenso ein Beta-Zugang ohne Pflichtaktion.
    """
    keycloak = Keycloak(
        [
            _konto("nie-geoeffnet", requiredActions=["UPDATE_PASSWORD"]),
            _konto("ohne-aktion", requiredActions=[]),
            _konto("beta-neu", emailVerified=True, requiredActions=[]),
        ]
    )

    anzahl = _konten(keycloak).nie_benutzte_loeschen(GRENZE)

    assert anzahl == 1
    assert keycloak.geloescht() == ["nie-geoeffnet"]
