"""
Konten im Realm von Gut gesagt ueber die Keycloak-Admin-Schnittstelle anlegen (#429)
und nie benutzte wieder loeschen (#538).

Angemeldet wird mit einem eigenen Client im Realm (Client Credentials), dessen
Dienstkonto nur die Rolle manage-users aus realm-management hat; einen engeren
Zuschnitt fuer "Konten anlegen" bietet Keycloak nicht. Welche Schritte das
Einrichten braucht: docs/KEYCLOAK_REALM.md.

Was hinausgeht, sind Mail-Adresse und Name. Den Code der Einladung erfaehrt Keycloak
nicht (services/einladung_service.py).
"""

from datetime import datetime
from typing import Callable, Dict, Iterable, List, Mapping, Optional

import httpx

from core.logging import get_logger
from domain.interfaces.konten_im_realm import (
    MAIL_GUELTIG_SEKUNDEN,
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
# Ein Konto aus einer Einladung traegt dazu "Passwort festlegen" als Pflichtaktion am
# Konto. Keycloak nimmt sie weg, sobald ein Passwort gesetzt ist (ueber den Link oder
# "Passwort vergessen"). Daran erkennt nie_benutzte_loeschen ein Konto, dessen Link
# geoeffnet und bestaetigt wurde, ohne dass je ein Passwort kam; Beta-Zugaenge (#488)
# tragen sie nicht und bleiben. Doppelt gefragt wird nicht: Aktionen am Konto und im
# Link fuehrt Keycloak als eine Menge.
EINLADUNG_PFLICHTAKTIONEN = PFLICHTAKTIONEN + ["UPDATE_PASSWORD"]
# Was der Link in der Mail tut. Mit VERIFY_EMAIL setzt Keycloak die Adresse auf
# bestaetigt, sobald jemand den Link oeffnet und bestaetigt (26.8.2,
# ExecuteActionsActionTokenHandler.handleToken); ohne sie schickte Keycloak beim ersten
# Anmelden eine zweite Mail "E-Mail verifizieren", weil der Realm bestaetigte Adressen
# verlangt. Doppelt gefragt wird nicht: Die Reihenfolge der Schritte legt Keycloak nach
# den Prioritaeten im Realm fest, und VERIFY_EMAIL zeigt keine Seite, wenn die Adresse
# schon bestaetigt ist. Die Reihenfolge hier ist die, in der Mail und Bestaetigungsseite
# die Schritte nennen.
MAIL_AKTIONEN = ["UPDATE_PASSWORD", "VERIFY_EMAIL"]
# Beta-Zugaenge (#488) ziehen mit bestaetigter Adresse um; dort nannten Mail und
# Bestaetigungsseite sonst einen Schritt "E-Mail verifizieren", der nichts tut.
MAIL_AKTIONEN_BESTAETIGT = ["UPDATE_PASSWORD"]
# Wohin der Link nach dem letzten Schritt fuehrt, unter der App-Adresse: Die Seite
# startet gleich die Anmeldung (Frontend, einladung/einladung-anmelden.component.ts).
# Keycloak beendet den Link ohne Anmeldung; ohne diese Seite stuende die Person
# abgemeldet auf der Startseite. Die Adresse muss genau so unter den Valid Redirect URIs
# des Clients stehen, sonst weist Keycloak die Mail ab (_mail_ausloesen).
ANMELDEN_PFAD = "einladung/anmelden"
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

    def konto_anlegen(
        self,
        email: str,
        vorname: Optional[str] = None,
        nachname: Optional[str] = None,
    ) -> KontoErgebnis:
        admin = self._admin
        konto = _konto(
            email, email_bestaetigt=False, pflichtaktionen=EINLADUNG_PFLICHTAKTIONEN
        )
        # Beide oder keiner, wie bei _konto_mit_namen. Ohne Namen fragt Keycloak beim
        # ersten Anmelden danach, weil das Benutzerprofil sie verlangt.
        if vorname and nachname:
            konto["firstName"] = vorname
            konto["lastName"] = nachname
        with self._client() as http:
            kopf = {"Authorization": f"Bearer {self._token(http)}"}
            antwort = http.post(admin, headers=kopf, json=konto)
            if antwort.status_code == 409:
                return KontoErgebnis.VORHANDEN
            antwort.raise_for_status()
            konto_id = self._konto_id(antwort)

            try:
                self._mail_ausloesen(
                    lambda methode, url, **kw: http.request(
                        methode, url, headers=kopf, **kw
                    ),
                    konto_id,
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
        aus einer Einladung, dazu Vor- und Nachname fuer den Anzeigenamen und mit
        bestaetigter Adresse (_konto_mit_namen). Keycloak
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
                    self._mail_ausloesen(
                        sitzung.anfrage, konto_id, MAIL_AKTIONEN_BESTAETIGT
                    ).raise_for_status()
                except httpx.HTTPError:
                    ergebnis.ohne_mail.append(kennung)
        return ergebnis

    def _mail_ausloesen(
        self,
        anfrage: Callable[..., httpx.Response],
        konto_id: str,
        aktionen: List[str] = MAIL_AKTIONEN,
    ) -> httpx.Response:
        """
        Keycloak schickt die Mail "Passwort festlegen". Der Link fuehrt danach auf
        ANMELDEN_PFAD. Steht diese Adresse (noch) nicht unter den Valid Redirect URIs,
        antwortet Keycloak mit 400; dann geht die Mail mit der App-Adresse hinaus wie
        bisher, und die Person meldet sich danach selbst an. So haengt das Einloesen
        nicht davon ab, ob der Schritt in Keycloak vor oder nach dem Release kommt.
        """
        url = f"{self._admin}/{konto_id}/execute-actions-email"
        antwort = anfrage(
            "PUT", url, params=self._mail_parameter(anmelden=True), json=aktionen
        )
        if antwort.status_code == 400 and self._app_client_id and self._app_url:
            logger.warning(
                "Keycloak rejected the login route as redirect URI; "
                f"add {self._anmelden_url()} to the client's valid redirect URIs"
            )
            antwort = anfrage(
                "PUT",
                url,
                params=self._mail_parameter(anmelden=False),
                json=aktionen,
            )
        return antwort

    def _anmelden_url(self) -> str:
        return f"{(self._app_url or '').rstrip('/')}/{ANMELDEN_PFAD}"

    def _mail_parameter(self, anmelden: bool) -> Dict[str, str]:
        parameter = {"lifespan": str(MAIL_GUELTIG_SEKUNDEN)}
        if self._app_client_id and self._app_url:
            parameter["client_id"] = self._app_client_id
            parameter["redirect_uri"] = (
                self._anmelden_url() if anmelden else self._app_url
            )
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

    # --- Nie benutzte Konten loeschen (#538) -------------------------------

    def nie_benutzte_loeschen(self, angelegt_vor: datetime) -> int:
        """
        Loescht Konten, die vor ``angelegt_vor`` angelegt und nie benutzt wurden, und
        gibt die Zahl der in diesem Lauf geloeschten zurueck. Nie benutzt: Es gibt kein
        Credential (also kein Passwort) und keine Verknuepfung mit einem Identity
        Provider, und dazu eines von beiden:

        - Die Mail-Adresse ist nicht bestaetigt und die Pflichtaktion aus dem Anlegen
          steht noch aus: Den Link hat niemand geoeffnet.
        - "Passwort festlegen" steht noch am Konto (EINLADUNG_PFLICHTAKTIONEN): Den Link
          hat jemand geoeffnet und bestaetigt (VERIFY_EMAIL in MAIL_AKTIONEN bestaetigt
          dabei die Adresse), vielleicht auch den Nutzungsbedingungen zugestimmt, aber
          nie ein Passwort gesetzt.

        Vorab angelegte Konten (#487) sind verknuepft; Beta-Zugaenge (#488) sind
        bestaetigt und tragen "Passwort festlegen" nicht am Konto.
        """
        grenze_ms = int(angelegt_vor.timestamp() * 1000)
        with self._client() as http:
            sitzung = _Sitzung(self, http)
            # Erst alle Seiten lesen, dann loeschen: Loeschen verschoebe die Seiten.
            # Gelesen werden alle Konten: Nach Pflichtaktionen filtert die
            # Admin-Schnittstelle nicht. Teuer sind nur die Abfragen in _benutzt, und
            # die gehen nur an Konten, die _sieht_nie_benutzt_aus.
            faellig = [
                konto["id"]
                for konto in self._alle_konten(sitzung)
                if konto.get("createdTimestamp", grenze_ms) < grenze_ms
                and _sieht_nie_benutzt_aus(konto)
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

    def _alle_konten(self, sitzung: "_Sitzung") -> List[dict]:
        konten: List[dict] = []
        while True:
            antwort = sitzung.anfrage(
                "GET",
                self._admin,
                params={
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


def _sieht_nie_benutzt_aus(konto: Mapping[str, object]) -> bool:
    """Die Bedingungen aus nie_benutzte_loeschen, die am Konto selbst stehen."""
    aktionen = set(konto.get("requiredActions") or [])  # type: ignore[arg-type]
    # Ohne Nutzungsbedingungen: Keycloak fragt sie vor dem Passwort ab (Prioritaet 20
    # vor 57, DefaultRequiredActions) und nimmt sie nach der Zustimmung vom Konto. Wer
    # zustimmt und auf der Passwortseite abbricht, traegt nur noch UPDATE_PASSWORD.
    if "UPDATE_PASSWORD" in aktionen:
        return True
    return set(PFLICHTAKTIONEN) <= aktionen and konto.get("emailVerified") is False


def _konto(
    email: str,
    email_bestaetigt: bool,
    pflichtaktionen: List[str] = PFLICHTAKTIONEN,
) -> Dict[str, object]:
    """Ein Konto im Realm: die Adresse als Benutzername, Pflichtaktion Nutzungsbedingungen."""
    return {
        "username": email,
        "email": email,
        "enabled": True,
        "emailVerified": email_bestaetigt,
        "requiredActions": list(pflichtaktionen),
    }


def _konto_mit_namen(zugang: BetaZugang) -> Dict[str, object]:
    # Die BFF bildet den Anzeigenamen aus Vorname und dem letzten Wort des Nachnamens
    # (DisplayNamePolicy); "Anna Maria Beispiel" ergibt so wie bisher "Anna B.". Aus
    # einem einzelnen Wort machte sie keinen Namen; als Vorname allein zeigte sie es,
    # deshalb dann keiner von beiden.
    #
    # Bestaetigt: Die Adresse war schon die Anmeldung des Beta-Zugangs. Unbestaetigt
    # loeschte nie_benutzte_loeschen (#538) das Konto, sobald die Mail ungeoeffnet
    # bleibt, obwohl die Beitraege schon dorthin umgezogen sind.
    vorname, _, nachname = " ".join(zugang.name.split()).partition(" ")
    konto = _konto(zugang.email, email_bestaetigt=True)
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
