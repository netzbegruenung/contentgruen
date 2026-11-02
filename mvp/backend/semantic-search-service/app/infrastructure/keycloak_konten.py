"""
Konten im Realm von Gut gesagt ueber die Keycloak-Admin-Schnittstelle anlegen (#429).

Angemeldet wird mit einem eigenen Client im Realm (Client Credentials), dessen
Dienstkonto nur die Rolle manage-users aus realm-management hat; einen engeren
Zuschnitt fuer "Konten anlegen" bietet Keycloak nicht. Welche Schritte das
Einrichten braucht: docs/KEYCLOAK_REALM.md.

Was hinausgeht, ist nur die Mail-Adresse. Den Code der Einladung erfaehrt Keycloak
nicht (services/einladung_service.py).
"""

from typing import Dict, Iterable, Mapping, Optional

import httpx

from core.logging import get_logger
from domain.interfaces.konten_im_realm import (
    BetaZugang,
    KontenMitPasswort,
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
                json=_konto(email, email_bestaetigt=False),
            )
            if antwort.status_code == 409:
                return KontoErgebnis.VORHANDEN
            antwort.raise_for_status()
            konto_id = self._konto_id(antwort)

            try:
                http.put(
                    f"{admin}/{konto_id}/execute-actions-email",
                    headers=kopf,
                    params=self._mail_parameter(),
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
                        # Der Identity Provider hat sie bestaetigt (Trust Email).
                        **_konto(email, email_bestaetigt=True),
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

    # --- Beta-Zugaenge umziehen (#488) -------------------------------------

    def konten_nach_adresse(self, adressen: Iterable[str]) -> Dict[str, str]:
        """Mail-Adresse (klein geschrieben) -> Konto im Realm, nur wo es eins gibt."""
        konten: Dict[str, str] = {}
        with self._client() as http:
            sitzung = _Sitzung(self, http)
            for adresse in adressen:
                konto = self._konto_zur_adresse(sitzung, adresse)
                if konto:
                    konten[adresse.lower()] = konto
        return konten

    def konten_mit_passwort_anlegen(
        self, zugaenge: Mapping[str, BetaZugang]
    ) -> KontenMitPasswort:
        """
        Je Beta-Zugang (alte Kennung -> Eintrag) ein Konto mit Mail und Passwort, wie
        aus einer Einladung, dazu Vor- und Nachname fuer den Anzeigenamen. Keycloak
        schickt "Passwort festlegen"; das Passwort aus managed-users.json laesst sich
        nicht mitnehmen (bcrypt kennt Keycloak nicht).

        Anders als bei der Einladung bleibt das Konto, wenn die Mail scheitert: Die
        Beitraege ziehen gleich danach dorthin um. Die Person kommt dann ueber
        "Passwort vergessen" hinein. Gibt es zur Adresse inzwischen ein Konto, gilt
        dieses.
        """
        ergebnis = KontenMitPasswort()
        with self._client() as http:
            sitzung = _Sitzung(self, http)
            for kennung, zugang in zugaenge.items():
                antwort = sitzung.anfrage(
                    "POST", self._admin, json=_konto_mit_namen(zugang)
                )
                if antwort.status_code == 400:
                    # Keycloak weist den Eintrag ab (etwa eine ungueltige Adresse). Nur
                    # dieser bleibt ohne Konto; ein Abbruch mitten in der Schleife liesse
                    # angelegte Konten und verschickte Mails ohne Umstellung zurueck.
                    ergebnis.abgewiesen.append(kennung)
                    continue
                if antwort.status_code == 409:
                    vorhanden = self._konto_zur_adresse(sitzung, zugang.email)
                    if vorhanden:
                        ergebnis.angelegt[kennung] = vorhanden
                    else:
                        ergebnis.vergeben.append(kennung)
                    continue
                antwort.raise_for_status()
                konto_id = self._konto_id(antwort)
                ergebnis.angelegt[kennung] = konto_id
                try:
                    sitzung.anfrage(
                        "PUT",
                        f"{self._admin}/{konto_id}/execute-actions-email",
                        params=self._mail_parameter(),
                        json=MAIL_AKTIONEN,
                    ).raise_for_status()
                except httpx.HTTPError:
                    ergebnis.ohne_mail.append(kennung)
        return ergebnis

    def _mail_parameter(self) -> Dict[str, str]:
        parameter = {"lifespan": str(MAIL_GUELTIG_SEKUNDEN)}
        if self._app_client_id and self._app_url:
            parameter["client_id"] = self._app_client_id
            parameter["redirect_uri"] = self._app_url
        return parameter

    def _konto_zur_adresse(self, sitzung: "_Sitzung", adresse: str) -> Optional[str]:
        antwort = sitzung.anfrage(
            "GET",
            self._admin,
            params={"email": adresse, "exact": "true", "briefRepresentation": "true"},
        )
        if antwort.is_error:
            # Nicht raise_for_status: Dessen Meldung nennt die URL und damit die Adresse.
            raise httpx.HTTPStatusError(
                f"Konto zur Adresse suchen: HTTP {antwort.status_code}",
                request=antwort.request,
                response=antwort,
            )
        # exact vergleicht ohne Gross und Klein; Keycloak speichert Adressen klein.
        treffer = [
            k
            for k in antwort.json()
            if (k.get("email") or "").lower() == adresse.lower()
        ]
        return treffer[0]["id"] if treffer else None

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


def _konto(email: str, email_bestaetigt: bool) -> Dict[str, object]:
    """Ein Konto im Realm: die Adresse als Benutzername, Pflichtaktion Nutzungsbedingungen."""
    return {
        "username": email,
        "email": email,
        "enabled": True,
        "emailVerified": email_bestaetigt,
        "requiredActions": PFLICHTAKTIONEN,
    }


def _konto_mit_namen(zugang: BetaZugang) -> Dict[str, object]:
    # Die BFF bildet den Anzeigenamen aus Vorname und dem letzten Wort des Nachnamens
    # (DisplayNamePolicy); "Anna Maria Beispiel" ergibt so wie bisher "Anna B.". Aus
    # einem einzelnen Wort machte sie keinen Namen; als Vorname allein zeigte sie es,
    # deshalb dann keiner von beiden.
    vorname, _, nachname = " ".join(zugang.name.split()).partition(" ")
    konto = _konto(zugang.email, email_bestaetigt=False)
    if nachname:
        konto["firstName"] = vorname
        konto["lastName"] = nachname
    return konto


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
