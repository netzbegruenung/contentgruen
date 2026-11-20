#!/usr/bin/env python3
"""
Liest aus dem Realm von Gut gesagt, wann jedes Konto der Keycloak-Pflichtaktion "Terms and Conditions" zugestimmt hat, zum Archivieren; mit --attribut-loeschen entfernt es danach das Attribut.

Anlass: Die App fragt die Nutzungsbedingungen kuenftig selbst (/einwilligung), danach
schaltet der Maintainer die Pflichtaktion ab; Bestandskonten werden in der App einmal
neu gefragt (Entscheidung Maintainer, 20.11.2026). Die Zeitpunkte in Keycloak sollen
vorher exportiert und archiviert werden. Keycloak 26.8.2 speichert sie am Konto im
Attribut ``terms_and_conditions`` als Unix-Sekunden (TermsAndConditions.USER_ATTRIBUTE,
services/src/main/java/org/keycloak/authentication/requiredactions/TermsAndConditions.java,
processAction), nur den Zeitpunkt, keinen Text. "Ablehnen" loescht das Attribut.

Das Attribut gehoert nicht zum Benutzerprofil des Realms ("unmanaged attribute"). Die
Admin-Schnittstelle zeigt es nur, wenn unter Realm settings -> General -> Unmanaged
attributes mindestens "Admin can view" steht; die Vorlage docs/keycloak/gutgesagt-realm.json
setzt nichts (Standard: aus). Dann zaehlt das Skript alle Konten als "ohne Zeitpunkt"
und sagt das.

Nach dem Archivieren loescht ``--attribut-loeschen`` das Attribut an jedem Konto
(Pflichtschritt am Rollout-Tag, Entscheidung Maintainer 20.11.2026; die
Datenschutzerklaerung sagt, die Angabe gehe mit der Umstellung). Ohne ``--ausfuehren``
nur ein Trockenlauf, der zaehlt. Zum Schreiben muss "Unmanaged attributes" auf "Admin
can edit" stehen: Mit "Admin can view" uebergeht Keycloak das Entfernen still
(DefaultAttributes.isReadOnly); der Lauf zaehlt danach nach und meldet das. Geschrieben
wird je Konto die frisch gelesene Darstellung ohne das Attribut (PUT, alle anderen
Attribute bleiben; UserResource.updateUser entfernt nur, was in ``attributes`` fehlt).

Laeuft im semantic-search-Container mit dessen Konfiguration (core.config):
SEMANTIC_SEARCH_KEYCLOAK_URL, _REALM, _ADMIN_CLIENT_ID, _ADMIN_CLIENT_SECRET (Client
gutgesagt-einladungen, docs/KEYCLOAK_REALM.md). Die Ausgabe nennt zuerst nur Zahlen;
nur die gehoeren in einen PR oder ein Issue. Mit --zeitpunkte folgen nach einer
Trennzeile je Konto Kennung und Zeitpunkt (Personendaten): nur in eine Datei auf dem
Host, die archiviert wird.

    # 1. Nur zaehlen
    docker exec -i gutgesagt-semantic-search python - < keycloak_nb_zeitpunkte.py

    # 2. Zum Archivieren (Ort und Frist: docs/LOESCHKONZEPT.md)
    docker exec -i gutgesagt-semantic-search python - --zeitpunkte \\
        < keycloak_nb_zeitpunkte.py > nb-zeitpunkte-keycloak.txt

    # 3. Attribut loeschen: Trockenlauf, dann wirklich
    docker exec -i gutgesagt-semantic-search python - --attribut-loeschen \\
        < keycloak_nb_zeitpunkte.py
    docker exec -i gutgesagt-semantic-search python - --attribut-loeschen --ausfuehren \\
        < keycloak_nb_zeitpunkte.py
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
    # Attribut vorhanden, aber keine Zahl
    unlesbar: int = 0
    # Dienstkonten (service-account-...) zaehlen nicht mit
    dienstkonten: int = 0
    # Kennungen mit Attribut ohne lesbare Zahl (fuer --attribut-loeschen)
    unlesbar_kennungen: List[str] = field(default_factory=list)

    @property
    def ohne_zeitpunkt(self) -> int:
        return self.konten - len(self.zeitpunkte) - self.unlesbar


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
                    ergebnis.unlesbar += 1
                    ergebnis.unlesbar_kennungen.append(konto["id"])
                else:
                    ergebnis.zeitpunkte[konto["id"]] = zeitpunkt
            erstes += len(seite)
            if len(seite) < JE_SEITE:
                return ergebnis


@dataclass
class Loeschbericht:
    mit_attribut: int = 0
    geloescht: int = 0
    # Keycloak antwortete mit Fehler (nur der Status wird gezaehlt)
    fehler: int = 0
    # PUT angenommen, das Attribut steht aber noch (Unmanaged attributes nicht "Admin can edit")
    unveraendert: int = 0
    ausgefuehrt: bool = False


def attribut_loeschen(
    basis_url: str,
    realm: str,
    client_id: str,
    client_secret: str,
    ausfuehren: bool,
    transport: Optional[httpx.BaseTransport] = None,
) -> Loeschbericht:
    """
    Entfernt ATTRIBUT an jedem Konto, das es traegt. Ohne ``ausfuehren`` nur zaehlen.
    Je Konto: frisch lesen, Attribut aus ``attributes`` nehmen, die ganze Darstellung
    zurueckschreiben, erneut lesen und pruefen.
    """
    zeitpunkte = zeitpunkte_lesen(basis_url, realm, client_id, client_secret, transport)
    bericht = Loeschbericht(ausgefuehrt=ausfuehren)
    # Auch unlesbare Werte tragen das Attribut; zeitpunkte_lesen zaehlt sie nur.
    kennungen = list(zeitpunkte.zeitpunkte) + list(zeitpunkte.unlesbar_kennungen)
    bericht.mit_attribut = len(kennungen)
    if not ausfuehren or not kennungen:
        return bericht
    basis = basis_url.rstrip("/")
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
        for kennung in kennungen:
            url = f"{basis}/admin/realms/{realm}/users/{kennung}"
            gelesen = http.get(url, headers=kopf)
            if gelesen.status_code != 200:
                bericht.fehler += 1
                continue
            darstellung = gelesen.json()
            attribute = dict(darstellung.get("attributes") or {})
            if ATTRIBUT not in attribute:
                bericht.geloescht += 1
                continue
            attribute.pop(ATTRIBUT)
            darstellung["attributes"] = attribute
            geschrieben = http.put(url, headers=kopf, json=darstellung)
            if geschrieben.status_code >= 300:
                bericht.fehler += 1
                continue
            danach = http.get(url, headers=kopf)
            if danach.status_code == 200 and ATTRIBUT in (
                danach.json().get("attributes") or {}
            ):
                bericht.unveraendert += 1
            else:
                bericht.geloescht += 1
    return bericht


def loeschbericht_ausgeben(bericht: Loeschbericht) -> None:
    print("Lauf: geschrieben" if bericht.ausgefuehrt else "Trockenlauf: nichts geaendert")
    print(f"Konten mit Attribut {ATTRIBUT}: {bericht.mit_attribut}")
    if bericht.ausgefuehrt:
        print(f"  entfernt: {bericht.geloescht}")
        print(f"  Fehler (Keycloak lehnte ab): {bericht.fehler}")
        print(f"  unveraendert: {bericht.unveraendert}")
        if bericht.unveraendert:
            print(
                "Hinweis: Keycloak hat das Attribut stehen lassen. Realm settings ->"
                " General -> Unmanaged attributes auf \"Admin can edit\", dann erneut."
            )


def zahlen_ausgeben(ergebnis: Ergebnis) -> None:
    print("Nur gelesen: nichts geaendert")
    print(f"Konten im Realm (ohne Dienstkonten): {ergebnis.konten}")
    print(f"  mit Zeitpunkt der Zustimmung: {len(ergebnis.zeitpunkte)}")
    print(f"  Attribut ohne lesbare Zahl: {ergebnis.unlesbar}")
    print(f"  ohne Zeitpunkt: {ergebnis.ohne_zeitpunkt}")
    if ergebnis.zeitpunkte:
        print(f"  fruehester: {min(ergebnis.zeitpunkte.values()).date().isoformat()}")
        print(f"  spaetester: {max(ergebnis.zeitpunkte.values()).date().isoformat()}")
    if ergebnis.konten and not ergebnis.zeitpunkte and not ergebnis.unlesbar:
        print(
            "Hinweis: kein Konto mit Zeitpunkt. Zeigt die Admin-Schnittstelle das"
            f" Attribut {ATTRIBUT} nicht? Realm settings -> General -> Unmanaged"
            " attributes auf \"Admin can view\", dann erneut laufen lassen."
        )


def zeitpunkte_ausgeben(ergebnis: Ergebnis) -> None:
    print()
    print(TRENNZEILE)
    print("kennung,zugestimmt_am_utc")
    for kennung, zeitpunkt in sorted(ergebnis.zeitpunkte.items()):
        print(f"{kennung},{zeitpunkt.isoformat()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--zeitpunkte",
        action="store_true",
        help="nach den Zahlen je Konto Kennung und Zeitpunkt ausgeben (Personendaten)",
    )
    parser.add_argument(
        "--attribut-loeschen",
        action="store_true",
        help=f"das Attribut {ATTRIBUT} an jedem Konto entfernen (erst nach dem Archivieren)",
    )
    parser.add_argument(
        "--ausfuehren",
        action="store_true",
        help="mit --attribut-loeschen wirklich schreiben (sonst nur zaehlen)",
    )
    args = parser.parse_args()
    if args.ausfuehren and not args.attribut_loeschen:
        print("--ausfuehren nur mit --attribut-loeschen", file=sys.stderr)
        return 2

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
    if args.attribut_loeschen:
        try:
            bericht = attribut_loeschen(
                konfiguration.keycloak_url,
                konfiguration.keycloak_realm,
                konfiguration.keycloak_admin_client_id,
                konfiguration.keycloak_admin_client_secret,
                ausfuehren=args.ausfuehren,
            )
        except httpx.HTTPStatusError as e:
            print(f"Keycloak antwortet {e.response.status_code}", file=sys.stderr)
            return 1
        loeschbericht_ausgeben(bericht)
        return 1 if bericht.fehler or bericht.unveraendert else 0
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
    zahlen_ausgeben(ergebnis)
    if args.zeitpunkte:
        zeitpunkte_ausgeben(ergebnis)
    return 0


if __name__ == "__main__":
    sys.exit(main())
