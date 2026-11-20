"""
Ab Keycloak 26.8.2 nimmt die Admin-Schnittstelle nur Tokens mit dem Scope kc-admin-api und
der Audience <keycloak>/admin/realms/<realm> an. Beides setzt der Client Scope
kc-admin-api, den Keycloak in jedem Realm anlegt, aber nur admin-cli und
security-admin-console zuweist. Ohne ihn am Client gutgesagt-einladungen endet jeder
Aufruf der Admin-Schnittstelle mit 401 (docs/KEYCLOAK_REALM.md, „Keycloak ab 26.8.2“).
"""

import json
import pathlib

WURZEL = pathlib.Path(__file__).resolve().parents[2]
VORLAGE = WURZEL / "docs/keycloak/gutgesagt-realm.json"

# Was ein Client ohne eigene Liste vom Realm bekäme (Keycloak 26.8.2,
# OIDCLoginProtocolFactory.createDefaultClientScopesImpl). Eine Liste in der Vorlage
# ersetzt diese Standardliste, was fehlt, hätte der Client danach nicht.
REALM_DEFAULT = {"web-origins", "acr", "profile", "roles", "basic", "email"}


def _realm() -> dict:
    return json.loads(VORLAGE.read_text())


def _client(client_id: str) -> dict:
    return next(c for c in _realm()["clients"] if c["clientId"] == client_id)


def test_einladungen_client_hat_admin_api_scope_als_default():
    scopes = set(_client("gutgesagt-einladungen")["defaultClientScopes"])
    assert "kc-admin-api" in scopes
    assert REALM_DEFAULT <= scopes


def test_admin_api_scope_nicht_realmweit_und_nicht_an_der_app():
    realm = _realm()
    assert "kc-admin-api" not in realm.get("defaultDefaultClientScopes", [])
    assert "kc-admin-api" not in realm.get("defaultOptionalClientScopes", [])
    app = _client("gutgesagt")
    assert "kc-admin-api" not in app.get("defaultClientScopes", [])
    assert "kc-admin-api" not in app.get("optionalClientScopes", [])


def test_vorlage_definiert_keine_eigenen_client_scopes():
    # Mit "clientScopes" legt Keycloak beim Import die Standard-Scopes (und kc-admin-api)
    # nicht an (RealmManager.isCreateDefaultClientScopes).
    assert "clientScopes" not in _realm()
