#!/usr/bin/env python3
"""
Liest aus dem Realm von Gut gesagt, wann jedes Konto der Keycloak-Pflichtaktion "Terms and Conditions" zugestimmt hat, zum Archivieren. Nur lesend.

Anlass: Die App fragt die Nutzungsbedingungen seit 0.9.8 selbst (/einwilligung), die
Pflichtaktion wird am Rollout-Tag abgeschaltet; Bestandskonten werden in der App einmal
neu gefragt (Entscheidung Maintainer, 20.11.2026). Die Zeitpunkte aus Keycloak werden
vorher archiviert (Ort und Frist: docs/LOESCHKONZEPT.md) und danach in Keycloak
geloescht. Keycloak 26.8.2 speichert sie am Konto im Attribut ``terms_and_conditions``
als Unix-Sekunden (TermsAndConditions.USER_ATTRIBUTE, processAction), nur den
Zeitpunkt, keinen Text. "Ablehnen" loescht das Attribut.

Wann die Admin-Schnittstelle das Attribut zeigt: Keycloak fuehrt es im Benutzerprofil als
eigenes Attribut, nie schreibbar und nur lesbar, solange die Pflichtaktion eingeschaltet
ist (DeclarativeUserProfileProviderFactory.createUserResourceValidation,
isTermAndConditionsEnabled). Also:

- Dieses Skript laeuft VOR dem Abschalten der Pflichtaktion. Danach sieht es kein
  Attribut mehr und meldet das.
- Ueber die Admin-Schnittstelle laesst sich das Attribut nicht loeschen (nie schreibbar;
  ein PUT ohne das Attribut laesst es stehen). Das Loeschen geht nur in der Datenbank von
  Keycloak; die Befehle stehen in docs/KEYCLOAK_REALM.md.

Laeuft im semantic-search-Container mit dessen Konfiguration (core.config):
SEMANTIC_SEARCH_KEYCLOAK_URL, _REALM, _ADMIN_CLIENT_ID, _ADMIN_CLIENT_SECRET (Client
gutgesagt-einladungen, docs/KEYCLOAK_REALM.md). Die Ausgabe nennt zuerst nur Zahlen;
nur die gehoeren in einen PR oder ein Issue. Mit --zeitpunkte folgen nach einer
Trennzeile je Konto Kennung und Zeitpunkt (Personendaten): nur ins Archiv auf dem Host.

    # 1. Nur zaehlen
    docker exec -i gutgesagt-semantic-search python - < keycloak_nb_zeitpunkte.py

    # 2. Ins Archiv (Ort, Rechte und Frist: docs/LOESCHKONZEPT.md)
    docker exec -i gutgesagt-semantic-search python - --zeitpunkte \\
        < keycloak_nb_zeitpunkte.py > <archivdatei>
"""

import argparse
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

ATTRIBUT = "terms_and_conditions"
JE_SEITE = 100
ZEITLIMIT_SEKUNDEN = 10.0
TRENNZEILE = "--- Ab hier Kennungen (Personendaten): nicht in PR, Issue oder Chat ---"


@dataclass
class Ergebnis:
    konten: int = 0
    # Kennung -> Zeitpunkt der Zustimmung (UTC)
    zeitpunkte: Dict[str, datetime] = field(default_factory=dict)
    # Kennung -> Rohwert, wenn das Attribut keine Zahl ist (wird mit archiviert)
    unlesbar: Dict[str, str] = field(default_factory=dict)
    # Dienstkonten (service-account-...) zaehlen nicht mit
    dienstkonten: int = 0

    @property
    def ohne_zeitpunkt(self) -> int:
        return self.konten - len(self.zeitpunkte) - len(self.unlesbar)


def _zeitpunkt(werte: Optional[List[str]]) -> Optional[datetime]:
    """Unix-Sekunden aus dem Attribut; None, wenn keine Zahl."""
    if not werte:
        return None
    try:
        return datetime.fromtimestamp(int(werte[0]), tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def zeitpunkte_lesen(
    basis_url: str,
    realm: str,
    client_id: str,
    client_secret: str,
    transport: Optional[httpx.BaseTransport] = None,
) -> Ergebnis:
    """Alle Konten des Realms seitenweise lesen, nur GET (ausser dem Token)."""
    basis = basis_url.rstrip("/")
    ergebnis = Ergebnis()
    with httpx.Client(transport=transport, timeout=ZEITLIMIT_SEKUNDEN) as http:
        token = http.post(
            f"{basis}/realms/{realm}/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        token.raise_for_status()
        kopf = {"Authorization": f"Bearer {token.json()['access_token']}"}
        erstes = 0
        while True:
            antwort = http.get(
                f"{basis}/admin/realms/{realm}/users",
                headers=kopf,
                params={
                    # Die kurze Form laesst die Attribute weg.
                    "briefRepresentation": "false",
                    "first": str(erstes),
                    "max": str(JE_SEITE),
                },
            )
            antwort.raise_for_status()
            seite = antwort.json()
            for konto in seite:
                if str(konto.get("username", "")).startswith("service-account-"):
                    ergebnis.dienstkonten += 1
                    continue
                ergebnis.konten += 1
                werte = (konto.get("attributes") or {}).get(ATTRIBUT)
                if werte is None:
                    continue
                zeitpunkt = _zeitpunkt(werte)
                if zeitpunkt is None:
                    ergebnis.unlesbar[konto["id"]] = ",".join(map(str, werte))
                else:
                    ergebnis.zeitpunkte[konto["id"]] = zeitpunkt
            erstes += len(seite)
            if len(seite) < JE_SEITE:
                return ergebnis


def zahlen_ausgeben(ergebnis: Ergebnis) -> None:
    print("Nur gelesen: nichts geaendert")
    print(f"Konten im Realm (ohne Dienstkonten): {ergebnis.konten}")
    print(f"  mit Zeitpunkt der Zustimmung: {len(ergebnis.zeitpunkte)}")
    print(f"  Attribut ohne lesbare Zahl: {len(ergebnis.unlesbar)}")
    print(f"  ohne Zeitpunkt: {ergebnis.ohne_zeitpunkt}")
    if ergebnis.zeitpunkte:
        print(f"  fruehester: {min(ergebnis.zeitpunkte.values()).date().isoformat()}")
        print(f"  spaetester: {max(ergebnis.zeitpunkte.values()).date().isoformat()}")
    if ergebnis.konten and not ergebnis.zeitpunkte and not ergebnis.unlesbar:
        print(
            f"Hinweis: kein Konto mit Zeitpunkt. Keycloak zeigt {ATTRIBUT} nur, solange"
            ' die Pflichtaktion "Terms and Conditions" eingeschaltet ist; ist sie'
            ' schon aus, vorher kurz wieder einschalten (nur "Enabled", nicht'
            ' "Set as default action") und erneut laufen lassen.'
        )


def zeitpunkte_ausgeben(ergebnis: Ergebnis) -> None:
    print()
    print(TRENNZEILE)
    print("kennung,zugestimmt_am_utc")
    for kennung, zeitpunkt in sorted(ergebnis.zeitpunkte.items()):
        print(f"{kennung},{zeitpunkt.isoformat()}")
    for kennung, rohwert in sorted(ergebnis.unlesbar.items()):
        print(f"{kennung},unlesbar:{rohwert}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--zeitpunkte",
        action="store_true",
        help="nach den Zahlen je Konto Kennung und Zeitpunkt ausgeben (Personendaten)",
    )
    args = parser.parse_args()

    # Beim Lauf per stdin ist das Arbeitsverzeichnis des Containers (/app) der Paketstamm.
    sys.path.insert(0, os.getcwd())
    from core.config import Settings

    konfiguration = Settings()
    fehlt = [
        env
        for name, env in {
            "keycloak_url": "SEMANTIC_SEARCH_KEYCLOAK_URL",
            "keycloak_admin_client_id": "SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_ID",
            "keycloak_admin_client_secret": "SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_SECRET",
        }.items()
        if not getattr(konfiguration, name)
    ]
    if fehlt:
        print(f"Es fehlt: {', '.join(fehlt)}", file=sys.stderr)
        return 2
    try:
        ergebnis = zeitpunkte_lesen(
            konfiguration.keycloak_url,
            konfiguration.keycloak_realm,
            konfiguration.keycloak_admin_client_id,
            konfiguration.keycloak_admin_client_secret,
        )
    except httpx.HTTPStatusError as e:
        # Nur der Status: Keycloak-Fehlertexte koennen Werte tragen.
        print(f"Keycloak antwortet {e.response.status_code}", file=sys.stderr)
        return 1
    except httpx.RequestError as e:
        # Ohne Text und URL: beide koennen Kennungen tragen.
        print(f"Keycloak nicht erreichbar: {type(e).__name__}", file=sys.stderr)
        return 1
    zahlen_ausgeben(ergebnis)
    if args.zeitpunkte:
        zeitpunkte_ausgeben(ergebnis)
    return 0


if __name__ == "__main__":
    sys.exit(main())
