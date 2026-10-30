"""
Konten im Realm von Gut gesagt ueber die Keycloak-Admin-Schnittstelle anlegen (#429).

Angemeldet wird mit einem eigenen Client im Realm (Client Credentials), dessen
Dienstkonto nur die Rolle manage-users aus realm-management hat; einen engeren
Zuschnitt fuer "Konten anlegen" bietet Keycloak nicht. Welche Schritte das
Einrichten braucht: docs/KEYCLOAK_REALM.md.

Was hinausgeht, ist nur die Mail-Adresse. Den Code der Einladung erfaehrt Keycloak
nicht (services/einladung_service.py).
"""

from typing import Optional

import httpx

from core.logging import get_logger
from domain.interfaces.konten_im_realm import KontoErgebnis

logger = get_logger(__name__)

# Die Pflichtaktion "Terms and Conditions" muss im Realm eingeschaltet sein (Schritt in
# docs/KEYCLOAK_REALM.md). Keycloak weist ein Konto mit einer unbekannten
# Pflichtaktion ab; dann schlaegt jedes Einloesen fehl.
PFLICHTAKTIONEN = ["TERMS_AND_CONDITIONS"]
# Was der Link in der Mail tut. Keycloak bestaetigt dabei auch die Mail-Adresse.
MAIL_AKTIONEN = ["UPDATE_PASSWORD"]
# So lange gilt der Link in der Mail; danach hilft "Passwort vergessen".
MAIL_GUELTIG_SEKUNDEN = 3 * 24 * 60 * 60
ZEITLIMIT_SEKUNDEN = 10.0


class KeycloakKonten:
    def __init__(
        self,
        basis_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        app_client_id: Optional[str] = None,
        app_url: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self._basis = basis_url.rstrip("/")
        self._realm = realm
        self._client_id = client_id
        self._client_secret = client_secret
        self._app_client_id = app_client_id
        self._app_url = app_url
        self._transport = transport

    def _client(self) -> httpx.Client:
        return httpx.Client(transport=self._transport, timeout=ZEITLIMIT_SEKUNDEN)

    def _token(self, http: httpx.Client) -> str:
        antwort = http.post(
            f"{self._basis}/realms/{self._realm}/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        antwort.raise_for_status()
        return antwort.json()["access_token"]

    def konto_anlegen(self, email: str) -> KontoErgebnis:
        admin = f"{self._basis}/admin/realms/{self._realm}/users"
        with self._client() as http:
            kopf = {"Authorization": f"Bearer {self._token(http)}"}
            antwort = http.post(
                admin,
                headers=kopf,
                json={
                    "username": email,
                    "email": email,
                    "enabled": True,
                    "emailVerified": False,
                    "requiredActions": PFLICHTAKTIONEN,
                },
            )
            if antwort.status_code == 409:
                return KontoErgebnis.VORHANDEN
            antwort.raise_for_status()
            konto_id = antwort.headers["Location"].rstrip("/").rsplit("/", 1)[-1]

            parameter = {"lifespan": str(MAIL_GUELTIG_SEKUNDEN)}
            if self._app_client_id and self._app_url:
                parameter["client_id"] = self._app_client_id
                parameter["redirect_uri"] = self._app_url
            try:
                http.put(
                    f"{admin}/{konto_id}/execute-actions-email",
                    headers=kopf,
                    params=parameter,
                    json=MAIL_AKTIONEN,
                ).raise_for_status()
            except httpx.HTTPError:
                # Ein Konto ohne Mail kann niemand nutzen, und es blockierte die Adresse:
                # Ein zweiter Versuch ergaebe "Konto vorhanden", ohne dass je eine Mail kam.
                try:
                    http.delete(f"{admin}/{konto_id}", headers=kopf).raise_for_status()
                except httpx.HTTPError as e:
                    # Dann bleibt das Konto ohne Mail stehen; die Person kommt ueber
                    # "Passwort vergessen" hinein. Ohne Adresse im Log.
                    logger.error(
                        f"Removing account after failed mail failed: {type(e).__name__}"
                    )
                raise
        return KontoErgebnis.ANGELEGT
