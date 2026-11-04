"""
Konten im Realm von Gut gesagt ueber die Keycloak-Admin-Schnittstelle anlegen (#429)
und nie benutzte wieder loeschen (#538).

Angemeldet wird mit einem eigenen Client im Realm (Client Credentials), dessen
Dienstkonto nur die Rolle manage-users aus realm-management hat; einen engeren
Zuschnitt fuer "Konten anlegen" bietet Keycloak nicht. Welche Schritte das
Einrichten braucht: docs/KEYCLOAK_REALM.md.

Was hinausgeht, ist nur die Mail-Adresse. Den Code der Einladung erfaehrt Keycloak
nicht (services/einladung_service.py).
"""

from datetime import datetime
from typing import Dict, Iterable, List, Mapping, Optional

import httpx

from core.logging import get_logger
from domain.interfaces.konten_im_realm import (
    MAIL_GUELTIG_SEKUNDEN,
    KontoErgebnis,
    VerknuepfteKonten,
)

logger = get_logger(__name__)

# Die Pflichtaktion "Terms and Conditions" muss im Realm eingeschaltet sein (Schritt in
# docs/KEYCLOAK_REALM.md). Keycloak weist ein Konto mit einer unbekannten
# Pflichtaktion ab; dann schlaegt jedes Einloesen fehl.
PFLICHTAKTIONEN = ["TERMS_AND_CONDITIONS"]
# Was der Link in der Mail tut. Keycloak bestaetigt dabei auch die Mail-Adresse.
MAIL_AKTIONEN = ["UPDATE_PASSWORD"]
ZEITLIMIT_SEKUNDEN = 10.0
KONTEN_JE_SEITE = 100


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

    @property
    def _admin(self) -> str:
        return f"{self._basis}/admin/realms/{self._realm}/users"

    @staticmethod
    def _konto_id(angelegt: httpx.Response) -> str:
        return angelegt.headers["Location"].rstrip("/").rsplit("/", 1)[-1]

    def konto_anlegen(self, email: str) -> KontoErgebnis:
        admin = self._admin
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
            konto_id = self._konto_id(antwort)

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

    # --- Kennungen umstellen (#487) ---------------------------------------
    # Viele Anfragen hintereinander: Laeuft das Token ab (Standard 5 Minuten), holt
    # _Sitzung.anfrage ein neues und wiederholt die Anfrage einmal.

    def kennungen_zuordnen(
        self, identity_provider: str, kennungen: Iterable[str]
    ) -> Dict[str, str]:
        """
        Alte Kennung -> Kennung im Realm. Alt ist die Kennung beim Identity Provider,
        mit der das Konto im Realm verknuepft ist; ohne verknuepftes Konto fehlt sie.
        """
        zuordnung: Dict[str, str] = {}
        with self._client() as http:
            sitzung = _Sitzung(self, http)
            for kennung in kennungen:
                konto = self._verknuepftes_konto(sitzung, identity_provider, kennung)
                if konto:
                    zuordnung[kennung] = konto
        return zuordnung

    def konten_verknuepft_anlegen(
        self, identity_provider: str, konten: Mapping[str, str]
    ) -> VerknuepfteKonten:
        """
        Je alte Kennung (-> Mail-Adresse) ein Konto im Realm, mit dem Identity
        Provider verknuepft. Keine Mail: Angemeldet wird weiter ueber den Identity
        Provider, und Keycloak findet das Konto dann ueber die Verknuepfung.
        Ist die Adresse im Realm schon vergeben, wird nichts verknuepft.
        """
        ergebnis = VerknuepfteKonten()
        with self._client() as http:
            sitzung = _Sitzung(self, http)
            for kennung, email in konten.items():
                # Nach einem abgebrochenen Lauf gibt es das Konto vielleicht schon; ein
                # POST bekaeme dann 409 und stuende faelschlich unter "vergeben".
                if self._verknuepftes_konto(sitzung, identity_provider, kennung):
                    continue
                antwort = sitzung.anfrage(
                    "POST",
                    self._admin,
                    json={
                        "username": email,
                        "email": email,
                        "enabled": True,
                        # Der Identity Provider hat sie bestaetigt (Trust Email).
                        "emailVerified": True,
                        "requiredActions": PFLICHTAKTIONEN,
                        "federatedIdentities": [
                            {
                                "identityProvider": identity_provider,
                                "userId": kennung,
                                "userName": email,
                            }
                        ],
                    },
                )
                if antwort.status_code == 409:
                    ergebnis.vergeben.append(kennung)
                    continue
                antwort.raise_for_status()
                ergebnis.angelegt[kennung] = self._konto_id(antwort)
        return ergebnis

    def _verknuepftes_konto(
        self, sitzung: "_Sitzung", identity_provider: str, kennung: str
    ) -> Optional[str]:
        antwort = sitzung.anfrage(
            "GET",
            self._admin,
            params={
                "idpAlias": identity_provider,
                "idpUserId": kennung,
                "briefRepresentation": "true",
            },
        )
        antwort.raise_for_status()
        treffer = antwort.json()
        # Keycloak vergleicht beides exakt; eine Kennung beim Identity Provider ist
        # hoechstens mit einem Konto verknuepft.
        return treffer[0]["id"] if treffer else None

    # --- Nie benutzte Konten loeschen (#538) -------------------------------

    def nie_benutzte_loeschen(self, angelegt_vor: datetime) -> int:
        """
        Loescht Konten, die vor ``angelegt_vor`` angelegt und nie benutzt wurden, und
        gibt die Zahl der in diesem Lauf geloeschten zurueck. Nie benutzt: Die
        Mail-Adresse ist nicht bestaetigt, die Pflichtaktion aus dem Anlegen steht noch
        aus, es gibt kein Passwort und keine Verknuepfung mit einem Identity Provider.
        So sieht ein Konto aus einer Einladung aus, dessen Link niemand geoeffnet hat;
        wer ihn oeffnet, setzt ein Passwort und bestaetigt dabei die Adresse. Vorab
        angelegte Konten (#487) sind verknuepft.
        """
        grenze_ms = int(angelegt_vor.timestamp() * 1000)
        with self._client() as http:
            sitzung = _Sitzung(self, http)
            # Erst alle Seiten lesen, dann loeschen: Loeschen verschoebe die Seiten.
            faellig = [
                konto["id"]
                for konto in self._unbestaetigte_konten(sitzung)
                # emailVerified auch hier: Der Filter in der Anfrage allein haelt ein
                # bestaetigtes Konto nicht fern, falls Keycloak ihn uebergeht.
                if konto.get("emailVerified") is False
                and konto.get("createdTimestamp", grenze_ms) < grenze_ms
                and set(PFLICHTAKTIONEN) <= set(konto.get("requiredActions") or [])
                and not self._benutzt(sitzung, konto["id"])
            ]
            geloescht = 0
            for konto_id in faellig:
                antwort = sitzung.anfrage("DELETE", f"{self._admin}/{konto_id}")
                # 404: inzwischen von Hand geloescht; das Ziel ist erreicht, gezaehlt
                # wird es nicht.
                if antwort.status_code == 404:
                    continue
                antwort.raise_for_status()
                geloescht += 1
        return geloescht

    def _unbestaetigte_konten(self, sitzung: "_Sitzung") -> List[dict]:
        konten: List[dict] = []
        while True:
            antwort = sitzung.anfrage(
                "GET",
                self._admin,
                params={
                    "emailVerified": "false",
                    # Die kurze Form laesst requiredActions weg.
                    "briefRepresentation": "false",
                    "first": str(len(konten)),
                    "max": str(KONTEN_JE_SEITE),
                },
            )
            antwort.raise_for_status()
            seite = antwort.json()
            konten.extend(seite)
            if len(seite) < KONTEN_JE_SEITE:
                return konten

    def _benutzt(self, sitzung: "_Sitzung", konto_id: str) -> bool:
        for teil in ("credentials", "federated-identity"):
            antwort = sitzung.anfrage("GET", f"{self._admin}/{konto_id}/{teil}")
            antwort.raise_for_status()
            if antwort.json():
                return True
        return False


class _Sitzung:
    """Ein HTTP-Client mit dem aktuellen Token; bei 401 einmal ein neues holen."""

    def __init__(self, konten: KeycloakKonten, http: httpx.Client) -> None:
        self._konten = konten
        self._http = http
        self._token = konten._token(http)

    def anfrage(self, methode: str, url: str, **kwargs) -> httpx.Response:
        for versuch in range(2):
            kopf = {"Authorization": f"Bearer {self._token}"}
            antwort = self._http.request(methode, url, headers=kopf, **kwargs)
            if antwort.status_code != 401 or versuch:
                return antwort
            self._token = self._konten._token(self._http)
        return antwort
