"""
Konten im Realm von Gut gesagt ueber die Keycloak-Admin-Schnittstelle anlegen (#429).

Keycloak ist eine Attrappe hinter httpx.MockTransport. Geprueft wird, welche
Anfragen hinausgehen: Token per Client Credentials, Konto anlegen, Mail "Passwort
festlegen" ausloesen; bei einem vorhandenen Konto nichts weiter, bei einer
gescheiterten Mail das halb angelegte Konto wieder loeschen.
"""

import json

import httpx
import pytest

from infrastructure.keycloak_konten import KeycloakKonten
from domain.interfaces.konten_im_realm import KontoErgebnis

pytestmark = pytest.mark.unit

BASIS = "https://login.example.org"
KONTO_ID = "8a0c6f6e-0000-4000-8000-000000000001"


class Keycloak:
    """Zeichnet die Anfragen auf und antwortet wie Keycloak."""

    def __init__(self, anlegen_status=201, mail_status=204, erlaubte_ziele=None):
        self.anfragen: list[httpx.Request] = []
        self.anlegen_status = anlegen_status
        self.mail_status = mail_status
        # Valid Redirect URIs des Clients; None: jedes Ziel geht
        self.erlaubte_ziele = erlaubte_ziele

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.anfragen.append(request)
        pfad = request.url.path
        if pfad.endswith("/protocol/openid-connect/token"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 60})
        if request.method == "POST" and pfad.endswith("/users"):
            kopf = {"Location": f"{BASIS}/admin/realms/gutgesagt/users/{KONTO_ID}"}
            return httpx.Response(self.anlegen_status, headers=kopf)
        if pfad.endswith("/execute-actions-email"):
            ziel = request.url.params.get("redirect_uri")
            if self.erlaubte_ziele is not None and ziel not in self.erlaubte_ziele:
                return httpx.Response(
                    400, json={"errorMessage": "Invalid redirect uri."}
                )
            return httpx.Response(self.mail_status)
        if request.method == "DELETE":
            return httpx.Response(204)
        return httpx.Response(404)

    def pfade(self):
        return [(r.method, r.url.path) for r in self.anfragen]


def _konten(keycloak, **extra):
    return KeycloakKonten(
        basis_url=BASIS + "/",
        realm="gutgesagt",
        client_id="gutgesagt-einladungen",
        client_secret="geheim",
        transport=httpx.MockTransport(keycloak),
        **extra,
    )


def test_legt_konto_an_und_loest_passwort_mail_aus():
    keycloak = Keycloak()

    ergebnis = _konten(keycloak).konto_anlegen("neu@example.org")

    assert ergebnis is KontoErgebnis.ANGELEGT
    assert keycloak.pfade() == [
        ("POST", "/realms/gutgesagt/protocol/openid-connect/token"),
        ("POST", "/admin/realms/gutgesagt/users"),
        ("PUT", f"/admin/realms/gutgesagt/users/{KONTO_ID}/execute-actions-email"),
    ]
    token, anlegen, mail = keycloak.anfragen
    assert b"grant_type=client_credentials" in token.content
    konto = json.loads(anlegen.content)
    assert konto["email"] == "neu@example.org"
    assert konto["username"] == "neu@example.org"
    assert konto["enabled"] is True
    # "Passwort festlegen" auch am Konto: daran erkennt die Loeschfrist (#538) ein
    # Konto, dessen Link bestaetigt, aber nie ein Passwort gesetzt wurde.
    # Ohne "Terms and Conditions": die Nutzungsbedingungen fragt seit 0.9.8 die App.
    assert konto["requiredActions"] == ["UPDATE_PASSWORD"]
    assert anlegen.headers["Authorization"] == "Bearer tok"
    # Ohne VERIFY_EMAIL bliebe die Adresse unbestaetigt, und Keycloak schickte beim
    # ersten Anmelden eine zweite Mail.
    assert json.loads(mail.content) == ["UPDATE_PASSWORD", "VERIFY_EMAIL"]
    assert "firstName" not in konto and "lastName" not in konto


def test_vor_und_nachname_kommen_ans_konto():
    keycloak = Keycloak()

    _konten(keycloak).konto_anlegen("neu@example.org", "Anna Maria", "Beispiel")

    konto = json.loads(keycloak.anfragen[1].content)
    assert konto["firstName"] == "Anna Maria"
    assert konto["lastName"] == "Beispiel"
    # Unbestaetigt bis zum Klick auf den Link; die Loeschfrist (#538) braucht das.
    assert konto["emailVerified"] is False


def test_nur_ein_name_geht_nicht_ans_konto():
    keycloak = Keycloak()

    _konten(keycloak).konto_anlegen("neu@example.org", "Anna", None)

    konto = json.loads(keycloak.anfragen[1].content)
    assert "firstName" not in konto and "lastName" not in konto


@pytest.mark.parametrize(
    "app_url", ["https://app.example.org", "https://app.example.org/"]
)
def test_nach_der_mail_fuehrt_der_link_in_die_anmeldung(app_url):
    keycloak = Keycloak()

    _konten(keycloak, app_client_id="gutgesagt", app_url=app_url).konto_anlegen(
        "neu@example.org"
    )

    mail = keycloak.anfragen[-1]
    assert mail.url.params["client_id"] == "gutgesagt"
    assert (
        mail.url.params["redirect_uri"] == "https://app.example.org/einladung/anmelden"
    )


def test_ohne_erlaubte_anmelde_adresse_fuehrt_der_link_in_die_app():
    # Keycloak kennt nur die App-Adresse (Vorlage vor diesem Schritt): Die Mail geht
    # trotzdem hinaus, mit dem Ziel von bisher.
    keycloak = Keycloak(erlaubte_ziele={"https://app.example.org/"})

    ergebnis = _konten(
        keycloak, app_client_id="gutgesagt", app_url="https://app.example.org/"
    ).konto_anlegen("neu@example.org")

    assert ergebnis is KontoErgebnis.ANGELEGT
    mails = [r for r in keycloak.anfragen if r.url.path.endswith("actions-email")]
    assert [m.url.params["redirect_uri"] for m in mails] == [
        "https://app.example.org/einladung/anmelden",
        "https://app.example.org/",
    ]
    assert ("DELETE", f"/admin/realms/gutgesagt/users/{KONTO_ID}") not in (
        keycloak.pfade()
    )


def test_ohne_app_adresse_kein_zweiter_versuch():
    keycloak = Keycloak(mail_status=400)

    with pytest.raises(httpx.HTTPStatusError):
        _konten(keycloak).konto_anlegen("neu@example.org")

    mails = [r for r in keycloak.anfragen if r.url.path.endswith("actions-email")]
    assert len(mails) == 1


def test_vorhandenes_konto_bleibt_unberuehrt():
    keycloak = Keycloak(anlegen_status=409)

    ergebnis = _konten(keycloak).konto_anlegen("alt@example.org")

    assert ergebnis is KontoErgebnis.VORHANDEN
    assert [p for p in keycloak.pfade() if "execute-actions" in p[1]] == []


def test_gescheiterte_mail_loescht_das_konto_wieder():
    keycloak = Keycloak(mail_status=500)

    with pytest.raises(httpx.HTTPStatusError):
        _konten(keycloak).konto_anlegen("neu@example.org")

    assert keycloak.pfade()[-1] == (
        "DELETE",
        f"/admin/realms/gutgesagt/users/{KONTO_ID}",
    )


def test_fehler_beim_anlegen_wird_gemeldet():
    keycloak = Keycloak(anlegen_status=403)

    with pytest.raises(httpx.HTTPStatusError):
        _konten(keycloak).konto_anlegen("neu@example.org")
