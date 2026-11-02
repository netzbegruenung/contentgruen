#!/usr/bin/env python3
"""
Stellt die Kennungen auf den Realm von Gut gesagt um (#487), einmalig vor dem Umstellen der BFF.

Ablauf und Reihenfolge: docs/KEYCLOAK_REALM.md, "Kennungen umstellen". Die Zuordnung
alt -> neu kommt aus dem Realm: Ein Konto dort, das mit dem Identity Provider
netzbegruenung verknuepft ist, traegt die alte Kennung als Kennung beim Identity
Provider. Umgeschrieben werden PostgreSQL und Qdrant; fuer Listen aus der
Konfiguration (Admins) gibt der Lauf die neuen Werte aus, die Loeschliste bekommt die
neuen Kennungen dazu (die alten bleiben, ihre Cookies gelten noch bis zu 14 Tage).

Das Image des Containers muss diesen Stand schon enthalten; ein aelteres bricht mit
ModuleNotFoundError ab, bevor es etwas schreibt.

Die Logik liegt im Dienst (services/wartung/kennungen_umstellen.py); das Skript
laeuft im semantic-search-Container mit dessen Code und Umgebung:
SEMANTIC_SEARCH_APP_DATABASE_URL, SEMANTIC_SEARCH_QDRANT_URL,
SEMANTIC_SEARCH_QDRANT_COLLECTION, SEMANTIC_SEARCH_ADMIN_USERS (wird mit umgestellt)
und SEMANTIC_SEARCH_KEYCLOAK_URL, _REALM, _ADMIN_CLIENT_ID, _ADMIN_CLIENT_SECRET
(per docker exec -e, falls im Container noch nicht gesetzt).

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
    --ohne-konto-zeigen      die Kennungen ohne Konto im Realm einzeln ausgeben

Idempotent: Ein zweiter Lauf zaehlt null (bis auf stehen gebliebene Saetze).
"""

import argparse
import os
import sys

# Beim Lauf per stdin ist das Arbeitsverzeichnis des Containers (/app) der Paketstamm.
sys.path.insert(0, os.getcwd())

from qdrant_client import QdrantClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from core.logging import LoggingConfig, initialize_logging  # noqa: E402

# keycloak_konten holt beim Import einen Logger; ausserhalb des Dienstes ist das
# Logging sonst nicht eingerichtet.
initialize_logging(LoggingConfig(level="WARNING"))

from infrastructure.keycloak_konten import KeycloakKonten  # noqa: E402
from services.wartung.kennungen_umstellen import umstellen  # noqa: E402

IDENTITY_PROVIDER = "netzbegruenung"
KEYCLOAK = (
    "SEMANTIC_SEARCH_KEYCLOAK_URL",
    "SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_ID",
    "SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_SECRET",
)


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--ausfuehren", action="store_true", help="wirklich schreiben (sonst nur zaehlen)"
    )
    parser.add_argument("--liste", type=_liste, action="append", default=[])
    parser.add_argument("--konten-anlegen", metavar="DATEI")
    parser.add_argument("--loeschliste", type=_kennungen, default=[])
    parser.add_argument("--ohne-konto-zeigen", action="store_true")
    args = parser.parse_args()

    fehlt = [name for name in KEYCLOAK if not os.environ.get(name)]
    if fehlt:
        print(f"Es fehlt: {', '.join(fehlt)}", file=sys.stderr)
        return 2

    listen = {}
    if os.environ.get("SEMANTIC_SEARCH_ADMIN_USERS"):
        listen["SEMANTIC_SEARCH_ADMIN_USERS"] = _kennungen(
            os.environ["SEMANTIC_SEARCH_ADMIN_USERS"]
        )
    listen.update(args.liste)
    anzulegen = _konten_lesen(args.konten_anlegen) if args.konten_anlegen else None

    realm = KeycloakKonten(
        basis_url=os.environ["SEMANTIC_SEARCH_KEYCLOAK_URL"],
        realm=os.environ.get("SEMANTIC_SEARCH_KEYCLOAK_REALM") or "gutgesagt",
        client_id=os.environ["SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_ID"],
        client_secret=os.environ["SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_SECRET"],
    )
    qdrant = QdrantClient(
        url=os.environ.get("SEMANTIC_SEARCH_QDRANT_URL", "http://localhost:6333"),
        timeout=60,
        check_compatibility=False,
    )
    collection = os.environ.get(
        "SEMANTIC_SEARCH_QDRANT_COLLECTION", "content_collection"
    )
    engine = create_engine(os.environ["SEMANTIC_SEARCH_APP_DATABASE_URL"])
    try:
        with engine.connect() as verbindung:
            ergebnis = umstellen(
                verbindung,
                qdrant,
                collection,
                realm,
                IDENTITY_PROVIDER,
                listen=listen,
                loeschliste=args.loeschliste,
                anzulegen=anzulegen,
                ausfuehren=args.ausfuehren,
            )
    finally:
        engine.dispose()

    print("Lauf: geschrieben" if ergebnis.ausgefuehrt else "Trockenlauf: nichts geaendert")
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
    if args.ohne_konto_zeigen:
        for kennung in ergebnis.ohne_konto:
            print(f"  {kennung}")
    if anzulegen is not None:
        print(
            f"Konten anzulegen beim Lauf: {len(ergebnis.anzulegen)}"
            " (ihre Zeilen und Beitraege zaehlt erst der Lauf)"
        )
        print(f"Adresse im Realm schon vergeben: {len(ergebnis.vergeben)}")
        for kennung in ergebnis.vergeben:
            print(f"  {kennung}")
    if ergebnis.listen:
        print("Listen, neue Werte (von Hand setzen):")
        for name, werte in ergebnis.listen.items():
            print(f"  {name}={','.join(werte)}")
    if args.loeschliste:
        print("geloeschte-konten.txt, neuer Inhalt (eine Kennung je Zeile):")
        for kennung in ergebnis.loeschliste:
            print(f"  {kennung}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
