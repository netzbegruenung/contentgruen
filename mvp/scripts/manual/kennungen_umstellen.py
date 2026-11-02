#!/usr/bin/env python3
"""
Stellt die Kennungen auf den Realm von Gut gesagt um (#487, #488), einmalig vor dem Umstellen der BFF.

Ablauf und Reihenfolge: docs/KEYCLOAK_REALM.md, "Kennungen umstellen". Die Zuordnung
alt -> neu kommt aus dem Realm: Ein Konto dort, das mit dem Identity Provider
netzbegruenung verknuepft ist, traegt die alte Kennung als Kennung beim Identity
Provider. Umgeschrieben werden PostgreSQL und Qdrant; fuer Listen aus der
Konfiguration (Admins) gibt der Lauf die neuen Werte aus, die Loeschliste bekommt die
neuen Kennungen dazu (die alten bleiben, ihre Cookies gelten noch bis zu 14 Tage).

Das Image des Containers muss diesen Stand schon enthalten; ein aelteres bricht mit
ModuleNotFoundError ab, bevor es etwas schreibt.

Die Logik liegt im Dienst (services/wartung/kennungen_umstellen.py); das Skript
laeuft im semantic-search-Container mit dessen Code und Konfiguration (core.config):
Datenbank, Qdrant, Collection, SEMANTIC_SEARCH_ADMIN_USERS (wird mit umgestellt) und
SEMANTIC_SEARCH_KEYCLOAK_URL, _REALM, _ADMIN_CLIENT_ID, _ADMIN_CLIENT_SECRET (per
docker exec -e, falls im Container noch nicht gesetzt).

Die Ausgabe nennt zuerst nur Zahlen; nur die gehoeren in einen PR oder ein Issue.
Was danach kommt, enthaelt Kennungen (Personendaten) und bleibt auf dem Host.

    # 1. Trockenlauf - zaehlt je Tabelle und Collection, aendert nichts
    docker exec -i gutgesagt-semantic-search python - < kennungen_umstellen.py

    # 2. Umstellen
    docker exec -i gutgesagt-semantic-search python - --ausfuehren < kennungen_umstellen.py

Optionen:
    --liste NAME=K1,K2       weitere Liste umstellen, etwa ADMIN_USER_IDS der BFF;
                             mehrfach moeglich
    --loeschliste K1,K2      die Kennungen aus geloeschte-konten.txt: werden
                             ergaenzt, nie als Konto angelegt
    --konten-anlegen DATEI   Zeilen "alte-kennung,mail-adresse": legt beim Lauf
                             fuer jede, die noch kein Konto hat, eins im Realm an,
                             mit dem Identity Provider verknuepft, ohne Mail.
                             Der Trockenlauf zaehlt ihre Zeilen noch nicht mit.
    --beta-zugaenge DATEI    managed-users.json: jeder Beta-Zugang zieht in das
                             Konto mit seiner Mail-Adresse um; fehlt es, legt der
                             Lauf eins an, und Keycloak schickt "Passwort festlegen"
    --ohne-konto-zeigen      die Kennungen ohne Konto im Realm einzeln ausgeben

Idempotent: Ein zweiter Lauf zaehlt null (bis auf stehen gebliebene Saetze).
"""

import argparse
import json
import os
import sys

# Beim Lauf per stdin ist das Arbeitsverzeichnis des Containers (/app) der Paketstamm.
sys.path.insert(0, os.getcwd())

from qdrant_client import QdrantClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from core.config import Settings  # noqa: E402
from core.logging import LoggingConfig, initialize_logging  # noqa: E402

# keycloak_konten holt beim Import einen Logger; ausserhalb des Dienstes ist das
# Logging sonst nicht eingerichtet.
initialize_logging(LoggingConfig(level="WARNING"))

from domain.interfaces.konten_im_realm import BetaZugang  # noqa: E402
from infrastructure.keycloak_konten import KeycloakKonten  # noqa: E402
from services.wartung.kennungen_umstellen import umstellen  # noqa: E402

IDENTITY_PROVIDER = "netzbegruenung"
# Einstellung -> Umgebungsvariable, fuer die Meldung, was fehlt
KEYCLOAK = {
    "keycloak_url": "SEMANTIC_SEARCH_KEYCLOAK_URL",
    "keycloak_admin_client_id": "SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_ID",
    "keycloak_admin_client_secret": "SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_SECRET",
}


def _kennungen(werte: str):
    return [k.strip() for k in werte.replace("\n", ",").split(",") if k.strip()]


def _liste(argument: str):
    name, gleich, werte = argument.partition("=")
    if not gleich or not name:
        raise argparse.ArgumentTypeError("NAME=K1,K2 erwartet")
    return name, _kennungen(werte)


def _konten_lesen(pfad: str):
    konten = {}
    with open(pfad, encoding="utf-8") as datei:
        for zeile in datei:
            zeile = zeile.strip()
            if not zeile or zeile.startswith("#"):
                continue
            kennung, _, email = zeile.partition(",")
            if not kennung.strip() or "@" not in email:
                raise SystemExit("--konten-anlegen: Zeile ohne Kennung oder Adresse")
            konten[kennung.strip()] = email.strip()
    return konten


def _beta_zugaenge_lesen(pfad: str):
    """userId -> BetaZugang; bricht vor jedem Schreiben ab, wenn ein Feld fehlt."""
    with open(pfad, encoding="utf-8") as datei:
        eintraege = json.load(datei).get("users", [])
    zugaenge = {}
    for eintrag in eintraege:
        kennung = str(eintrag.get("userId") or "").strip()
        email = str(eintrag.get("email") or "").strip()
        if not kennung or "@" not in email:
            raise SystemExit("--beta-zugaenge: Eintrag ohne userId oder email")
        if kennung in zugaenge:
            raise SystemExit("--beta-zugaenge: userId doppelt")
        admin = eintrag.get("isAdmin", False)
        if not isinstance(admin, bool):
            raise SystemExit("--beta-zugaenge: isAdmin ist nicht true oder false")
        zugaenge[kennung] = BetaZugang(
            email=email,
            name=str(eintrag.get("displayName") or ""),
            admin=admin,
        )
    return zugaenge


def _beta_zahlen_ausgeben(ergebnis, beta) -> None:
    mit_konto = sum(1 for k in beta if k in ergebnis.zuordnung)
    print(f"Beta-Zugaenge: {len(beta)}, mit Konto im Realm: {mit_konto}")
    print(
        f"Beta-Zugaenge anzulegen beim Lauf: {len(ergebnis.beta_anzulegen)}"
        " (ihre Zeilen und Beitraege zaehlt erst der Lauf)"
    )
    print(
        "Beta-Zugaenge nicht umgezogen, Adresse gehoert im Realm schon zu einer"
        f" anderen Kennung: {len(ergebnis.beta_vergeben)}"
    )
    print(
        "Beta-Zugaenge ohne Mail \"Passwort festlegen\":"
        f" {len(ergebnis.beta_ohne_mail)}"
    )
    print(
        "Beta-Zugaenge, deren Konto Keycloak abwies:"
        f" {len(ergebnis.beta_abgewiesen)}"
    )


def _zahlen_ausgeben(ergebnis, mit_anzulegenden: bool) -> None:
    print(
        "Trockenlauf: nichts geaendert"
        if not ergebnis.ausgefuehrt
        else "Lauf: geschrieben"
    )
    print(f"Kennungen mit Konto im Realm: {len(ergebnis.zuordnung)}")
    print("PostgreSQL (Zeilen je Tabelle und Spalte):")
    for spalte, anzahl in ergebnis.postgres.geaendert.items():
        print(f"  {spalte}: {anzahl}")
    print(
        "  raw_input_drafts mit alter Kennung stehen geblieben:"
        f" {ergebnis.postgres.stehen_geblieben}"
    )
    print("Qdrant (Beitraege je Collection):")
    for name, anzahl in ergebnis.qdrant.items():
        print(f"  {name}: {anzahl}")
    print(f"Ohne Konto im Realm, bleiben: {len(ergebnis.ohne_konto)}")
    if mit_anzulegenden:
        print(
            f"Konten anzulegen beim Lauf: {len(ergebnis.anzulegen)}"
            " (ihre Zeilen und Beitraege zaehlt erst der Lauf)"
        )
        print(f"Adresse im Realm schon vergeben: {len(ergebnis.vergeben)}")


def _kennungen_ausgeben(ergebnis, args) -> None:
    abschnitte = []
    if args.ohne_konto_zeigen and ergebnis.ohne_konto:
        abschnitte.append(("Ohne Konto im Realm:", ergebnis.ohne_konto))
    if ergebnis.vergeben:
        abschnitte.append(("Adresse im Realm schon vergeben:", ergebnis.vergeben))
    if ergebnis.beta_vergeben:
        abschnitte.append(
            (
                "Beta-Zugaenge nicht umgezogen (Admin entscheidet, wessen Konto"
                " bleibt):",
                ergebnis.beta_vergeben,
            )
        )
    if ergebnis.beta_abgewiesen:
        abschnitte.append(
            (
                "Beta-Zugaenge ohne Konto, von Keycloak abgewiesen (Adresse in der"
                " Datei pruefen, dann erneut laufen lassen):",
                ergebnis.beta_abgewiesen,
            )
        )
    if ergebnis.beta_ohne_mail:
        abschnitte.append(
            (
                "Beta-Zugaenge ohne Mail (\"Passwort vergessen\" oder Passwort"
                " in der Admin-Konsole setzen):",
                ergebnis.beta_ohne_mail,
            )
        )
    # Im Trockenlauf fehlen die erst anzulegenden Konten noch: nur eine Vorschau.
    setzen = (
        "(von Hand setzen)"
        if ergebnis.ausgefuehrt
        else "(Vorschau, nicht setzen: erst die Werte aus dem Lauf)"
    )
    if ergebnis.listen:
        abschnitte.append(
            (
                f"Listen, neue Werte {setzen}:",
                [f"{n}={','.join(w)}" for n, w in ergebnis.listen.items()],
            )
        )
    if ergebnis.beta_admins:
        abschnitte.append(
            (
                f"Admins unter den Beta-Zugaengen, neue Kennungen {setzen}: in"
                " ADMIN_USER_IDS und SEMANTIC_SEARCH_ADMIN_USERS ergaenzen",
                ergebnis.beta_admins,
            )
        )
    if args.loeschliste:
        abschnitte.append(
            (
                f"geloeschte-konten.txt, neuer Inhalt {setzen}, eine Kennung je Zeile:",
                ergebnis.loeschliste,
            )
        )
    if not abschnitte:
        return
    print()
    print("--- Ab hier Kennungen (Personendaten): nicht in PR, Issue oder Chat ---")
    for titel, zeilen in abschnitte:
        print(titel)
        for zeile in zeilen:
            print(f"  {zeile}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--ausfuehren",
        action="store_true",
        help="wirklich schreiben (sonst nur zaehlen)",
    )
    parser.add_argument("--liste", type=_liste, action="append", default=[])
    parser.add_argument("--konten-anlegen", metavar="DATEI")
    parser.add_argument("--loeschliste", type=_kennungen, default=[])
    parser.add_argument("--beta-zugaenge", metavar="DATEI")
    parser.add_argument("--ohne-konto-zeigen", action="store_true")
    args = parser.parse_args()

    # Neu gelesen, nicht core.config.settings: dieselben Standardwerte wie der Dienst,
    # mit der Umgebung dieses Aufrufs (docker exec -e).
    konfiguration = Settings()
    fehlt = [env for name, env in KEYCLOAK.items() if not getattr(konfiguration, name)]
    if fehlt:
        print(f"Es fehlt: {', '.join(fehlt)}", file=sys.stderr)
        return 2

    listen = {}
    if konfiguration.admin_users:
        listen["SEMANTIC_SEARCH_ADMIN_USERS"] = _kennungen(konfiguration.admin_users)
    listen.update(args.liste)
    anzulegen = _konten_lesen(args.konten_anlegen) if args.konten_anlegen else None
    beta = _beta_zugaenge_lesen(args.beta_zugaenge) if args.beta_zugaenge else None

    realm = KeycloakKonten(
        basis_url=konfiguration.keycloak_url,
        realm=konfiguration.keycloak_realm,
        client_id=konfiguration.keycloak_admin_client_id,
        client_secret=konfiguration.keycloak_admin_client_secret,
    )
    qdrant = QdrantClient(
        url=konfiguration.qdrant_url, timeout=60, check_compatibility=False
    )
    engine = create_engine(konfiguration.app_database_url)
    try:
        with engine.connect() as verbindung:
            ergebnis = umstellen(
                verbindung,
                qdrant,
                konfiguration.qdrant_collection,
                realm,
                IDENTITY_PROVIDER,
                listen=listen,
                loeschliste=args.loeschliste,
                anzulegen=anzulegen,
                beta_zugaenge=beta,
                ausfuehren=args.ausfuehren,
            )
    finally:
        engine.dispose()

    _zahlen_ausgeben(ergebnis, anzulegen is not None)
    if beta is not None:
        _beta_zahlen_ausgeben(ergebnis, beta)
    _kennungen_ausgeben(ergebnis, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
