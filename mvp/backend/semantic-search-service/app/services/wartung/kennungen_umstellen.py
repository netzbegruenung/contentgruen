"""
Kennungen auf den Realm von Gut gesagt umstellen (#487), einmalig vor dem Umstellen
der BFF (docs/KEYCLOAK_REALM.md, "Reihenfolge beim Umstellen").

Mitglieder der Netzbegruenung bekommen im eigenen Realm ein neues Konto und damit
eine neue Kennung. Die Zuordnung alt -> neu kommt aus dem Realm: Das neue Konto ist
mit dem Identity Provider ``netzbegruenung`` verknuepft, und die Kennung dort ist die
alte (infrastructure/keycloak_konten.py, ``kennungen_zuordnen``).

Umgeschrieben wird ueberall, wo eine Kennung steht: die Spalten in PostgreSQL
(``SPALTEN``, dieselben wie im Loeschkommando mvp/scripts/manual/person_loeschen.sql),
die vier Felder an Beitraegen in Qdrant und Listen aus der Konfiguration (Admins,
Loeschliste), deren neue Werte der Lauf ausgibt.

Ohne ausfuehren=True wird nur gezaehlt (Trockenlauf). Idempotent: Nach einem Lauf
steht keine alte Kennung mehr da, ein zweiter zaehlt null. Bricht ein Lauf zwischen
PostgreSQL und Qdrant ab, holt ein zweiter den Rest nach.

Aufruf: mvp/scripts/manual/kennungen_umstellen.py
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Set

from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
    SetPayload,
    SetPayloadOperation,
)
from sqlalchemy import text
from sqlalchemy.engine import Connection

from services.anzeigename_service import (
    EHEMALIGE_PERSON_KENNUNG,
    KENNUNGSFELDER,
    KENNUNGSLISTEN,
    angemeldet,
)
from services.wartung.beitraege_anonymisieren import ALTER_PLATZHALTER

SEITE = 256

# Tabelle -> Spalten mit einer Kennung. Was eine Kennung nur gehasht traegt
# (Tagespseudonym an search_events), laesst sich nicht umschreiben und muss es nicht:
# Es verbindet ohnehin nichts ueber den Tag hinaus.
SPALTEN = {
    "users": ("user_id",),
    "gesehene_nutzung": ("user_id",),
    "votes": ("user_id",),
    "raw_inputs": ("submitted_by", "destilled_by"),
    "raw_input_drafts": ("user_id",),
    "raw_input_content_links": ("created_by",),
    "content_reports": ("reported_by_user_id", "reviewed_by"),
    "sperren": ("autor", "gesperrt_von", "geprueft_von"),
}

Zuordnung = Mapping[str, str]


def _platzhalter(kennung: str) -> bool:
    return kennung in (EHEMALIGE_PERSON_KENNUNG, ALTER_PLATZHALTER) or (
        kennung.startswith(EHEMALIGE_PERSON_KENNUNG + "-")
    )


def _person(kennung: Any) -> bool:
    """Eine Kennung, die eine Person bezeichnet: kein Platzhalter, nicht anonym."""
    return (
        isinstance(kennung, str)
        and angemeldet(kennung)
        and kennung == kennung.strip()
        and not _platzhalter(kennung)
    )


def zuordnung_pruefen(zuordnung: Zuordnung) -> None:
    """Bricht ab, bevor etwas geschrieben wird, wenn die Zuordnung nicht eindeutig ist."""
    for alt, neu in zuordnung.items():
        if not (_person(alt) and _person(neu)) or alt == neu:
            raise ValueError("Zuordnung mit einer Kennung, die niemanden bezeichnet")
    if set(zuordnung.values()) & set(zuordnung):
        raise ValueError("Eine neue Kennung wird selbst umgestellt")
    if len(set(zuordnung.values())) != len(zuordnung):
        raise ValueError("Zwei alte Kennungen auf dieselbe neue")


def liste_umschreiben(werte: Iterable[str], zuordnung: Zuordnung) -> List[str]:
    """Admins, Loeschliste: zugeordnete Kennungen ersetzt, Reihenfolge wie vorher."""
    return [zuordnung.get(w, w) for w in werte]


# --- PostgreSQL -----------------------------------------------------------


@dataclass
class PostgresBericht:
    # "tabelle.spalte" -> Zeilen, die eine alte Kennung trugen (umgeschrieben, oder
    # verworfen, weil die neue Kennung dort schon eine Zeile hatte)
    geaendert: Dict[str, int] = field(default_factory=dict)
    # Saetze, die mit alter Kennung stehen bleiben: Die neue hat am selben Einwurf
    # schon einen, und der Index (raw_input_id, user_id) laesst keinen zweiten zu.
    stehen_geblieben: int = 0


# Wo eine Kennung Teil eines eindeutigen Schluessels ist, gewinnt die Zeile der neuen
# Kennung, falls es sie schon gibt; die der alten geht vorher. (Tabelle, Spalte,
# weitere Spalten des Schlüssels)
_ZEILE_DER_NEUEN_GEWINNT = {
    ("users", "user_id"): (),
    ("gesehene_nutzung", "user_id"): (),
    ("votes", "user_id"): ("content_id",),
}


def _gleicher_schluessel(spalten: Iterable[str]) -> str:
    return "".join(f" AND n.{s} = t.{s}" for s in spalten)


def postgres_umschreiben(
    verbindung: Connection, zuordnung: Zuordnung, ausfuehren: bool = False
) -> PostgresBericht:
    """
    Alles in einer Transaktion; der Trockenlauf fuehrt dieselben Anweisungen aus und
    rollt zurueck, die Zahlen sind also dieselben wie beim echten Lauf.
    """
    zuordnung_pruefen(zuordnung)
    bericht = PostgresBericht()
    transaktion = verbindung.begin()
    try:
        verbindung.execute(
            text(
                "CREATE TEMP TABLE kennungen_zuordnung"
                " (alt TEXT PRIMARY KEY, neu TEXT NOT NULL) ON COMMIT DROP"
            )
        )
        if zuordnung:
            verbindung.execute(
                text("INSERT INTO kennungen_zuordnung (alt, neu) VALUES (:alt, :neu)"),
                [{"alt": a, "neu": n} for a, n in zuordnung.items()],
            )
        for tabelle, spalten in SPALTEN.items():
            for spalte in spalten:
                bericht.geaendert[f"{tabelle}.{spalte}"] = _spalte_umschreiben(
                    verbindung, tabelle, spalte
                )
        bericht.stehen_geblieben = verbindung.execute(
            text(
                "SELECT count(*) FROM raw_input_drafts AS t"
                " JOIN kennungen_zuordnung AS z ON t.user_id = z.alt"
            )
        ).scalar_one()
    except BaseException:
        transaktion.rollback()
        raise
    if ausfuehren:
        transaktion.commit()
    else:
        transaktion.rollback()
    return bericht


def _spalte_umschreiben(verbindung: Connection, tabelle: str, spalte: str) -> int:
    anzahl = 0
    schluessel = _ZEILE_DER_NEUEN_GEWINNT.get((tabelle, spalte))
    if schluessel is not None:
        anzahl += verbindung.execute(
            text(
                f"DELETE FROM {tabelle} AS t USING kennungen_zuordnung AS z"
                f" WHERE t.{spalte} = z.alt AND EXISTS (SELECT 1 FROM {tabelle} AS n"
                f" WHERE n.{spalte} = z.neu{_gleicher_schluessel(schluessel)})"
            )
        ).rowcount
    bedingung = ""
    if (tabelle, spalte) == ("raw_input_drafts", "user_id"):
        # Satz der neuen Kennung am selben Einwurf: der alte bleibt stehen (Bericht).
        bedingung = (
            " AND NOT EXISTS (SELECT 1 FROM raw_input_drafts AS n"
            " WHERE n.user_id = z.neu AND n.raw_input_id = t.raw_input_id)"
        )
    anzahl += verbindung.execute(
        text(
            f"UPDATE {tabelle} AS t SET {spalte} = z.neu FROM kennungen_zuordnung AS z"
            f" WHERE t.{spalte} = z.alt{bedingung}"
        )
    ).rowcount
    return anzahl


def kennungen_in_postgres(verbindung: Connection) -> Set[str]:
    teile = [
        f"SELECT DISTINCT {spalte} FROM {tabelle}"
        for tabelle, spalten in SPALTEN.items()
        for spalte in spalten
    ]
    # Eigene Transaktion, damit postgres_umschreiben danach seine beginnen kann.
    with verbindung.begin():
        werte = verbindung.execute(text(" UNION ".join(teile))).scalars().all()
    return {k for k in werte if _person(k)}


# --- Qdrant ---------------------------------------------------------------


def _felder(payload: Dict[str, Any]) -> Iterable[Any]:
    for feld in KENNUNGSFELDER:
        yield payload.get(feld)
    for feld, schluessel in KENNUNGSLISTEN:
        for eintrag in payload.get(feld) or []:
            if isinstance(eintrag, dict):
                yield eintrag.get(schluessel)


def felder_ersetzt(payload: Dict[str, Any], zuordnung: Zuordnung) -> Dict[str, Any]:
    """Nur die Felder, in denen eine zugeordnete Kennung vorkommt, mit der neuen."""
    neu: Dict[str, Any] = {
        feld: zuordnung[payload[feld]]
        for feld in KENNUNGSFELDER
        if payload.get(feld) in zuordnung
    }
    for feld, schluessel in KENNUNGSLISTEN:
        eintraege = payload.get(feld) or []
        if any(e.get(schluessel) in zuordnung for e in eintraege):
            neu[feld] = [
                (
                    {**e, schluessel: zuordnung[e[schluessel]]}
                    if e.get(schluessel) in zuordnung
                    else e
                )
                for e in eintraege
            ]
    return neu


def kennungen_in_qdrant(client: QdrantClient, collection: str) -> Set[str]:
    kennungen: Set[str] = set()
    offset = None
    while True:
        punkte, offset = client.scroll(
            collection_name=collection,
            limit=SEITE,
            offset=offset,
            with_payload=[*KENNUNGSFELDER, *(f for f, _ in KENNUNGSLISTEN)],
            with_vectors=False,
        )
        for punkt in punkte:
            kennungen.update(k for k in _felder(punkt.payload or {}) if _person(k))
        if offset is None:
            return kennungen


def qdrant_umschreiben(
    client: QdrantClient,
    collection: str,
    zuordnung: Zuordnung,
    ausfuehren: bool = False,
) -> int:
    """Zahl der Beitraege, an denen eine alte Kennung steht (bzw. stand)."""
    zuordnung_pruefen(zuordnung)
    if not zuordnung:
        return 0
    alte = list(zuordnung)
    traegt_alte = Filter(
        should=[
            FieldCondition(key=k, match=MatchAny(any=alte))
            for k in (*KENNUNGSFELDER, *(f"{f}[].{s}" for f, s in KENNUNGSLISTEN))
        ]
    )
    # Erst alle Treffer sammeln, dann schreiben: Ein Scroll ueber den Filter, waehrend
    # die Treffer aus ihm herausfallen, koennte Seiten ueberspringen.
    neu_je_punkt = []
    offset = None
    while True:
        punkte, offset = client.scroll(
            collection_name=collection,
            scroll_filter=traegt_alte,
            limit=SEITE,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for punkt in punkte:
            neu = felder_ersetzt(punkt.payload or {}, zuordnung)
            if neu:
                neu_je_punkt.append((punkt.id, neu))
        if offset is None:
            break

    if ausfuehren:
        for start in range(0, len(neu_je_punkt), SEITE):
            client.batch_update_points(
                collection_name=collection,
                update_operations=[
                    SetPayloadOperation(
                        set_payload=SetPayload(payload=neu, points=[punkt_id])
                    )
                    for punkt_id, neu in neu_je_punkt[start : start + SEITE]
                ],
                wait=True,
            )
    return len(neu_je_punkt)


# --- Ablauf ---------------------------------------------------------------


class IKennungenImRealm(Protocol):
    """infrastructure/keycloak_konten.py"""

    def kennungen_zuordnen(
        self, identity_provider: str, kennungen: Iterable[str]
    ) -> Dict[str, str]: ...

    def konten_verknuepft_anlegen(
        self, identity_provider: str, konten: Mapping[str, str]
    ) -> Any: ...


@dataclass
class Umstellung:
    ausgefuehrt: bool
    # alte Kennung -> Kennung im Realm, fuer alle, die umgeschrieben werden
    zuordnung: Dict[str, str]
    postgres: PostgresBericht
    # Collection -> Beitraege mit einer alten Kennung
    qdrant: Dict[str, int]
    # Name der Liste -> neue Werte (Admins, Loeschliste)
    listen: Dict[str, List[str]]
    # Kennungen ohne verknuepftes Konto im Realm: bleiben, wie sie sind (Beta-Zugaenge,
    # Konten aus Einladungen, Mitglieder, fuer die noch kein Konto angelegt ist)
    ohne_konto: List[str]
    # Mit Mail-Adresse genannt und ohne Konto: wird beim Lauf angelegt (Trockenlauf)
    anzulegen: List[str] = field(default_factory=list)
    # Konto sollte angelegt werden, die Adresse hat im Realm aber schon eins
    vergeben: List[str] = field(default_factory=list)


def umstellen(
    verbindung: Connection,
    qdrant: QdrantClient,
    collection: str,
    realm: IKennungenImRealm,
    identity_provider: str,
    listen: Optional[Mapping[str, List[str]]] = None,
    anzulegen: Optional[Mapping[str, str]] = None,
    ausfuehren: bool = False,
) -> Umstellung:
    """
    Sucht alle Kennungen in PostgreSQL, Qdrant und den Listen, ordnet sie ueber den
    Realm zu und schreibt sie um. ``anzulegen`` (alte Kennung -> Mail-Adresse) legt
    beim Lauf vorher die fehlenden Konten im Realm an, mit dem Identity Provider
    verknuepft.
    """
    listen = dict(listen or {})
    alte = (
        kennungen_in_postgres(verbindung)
        | kennungen_in_qdrant(qdrant, collection)
        | {k for werte in listen.values() for k in werte if _person(k)}
    )
    zuordnung = realm.kennungen_zuordnen(identity_provider, sorted(alte))
    fehlend = sorted(k for k in (anzulegen or {}) if k in alte and k not in zuordnung)
    vergeben: List[str] = []
    if ausfuehren and fehlend:
        angelegt = realm.konten_verknuepft_anlegen(
            identity_provider, {k: anzulegen[k] for k in fehlend}
        )
        zuordnung.update(angelegt.angelegt)
        vergeben = list(angelegt.vergeben)
        fehlend = []
    # Vor jedem Schreiben, auch fuer die Listen.
    zuordnung_pruefen(zuordnung)
    return Umstellung(
        ausgefuehrt=ausfuehren,
        zuordnung=zuordnung,
        postgres=postgres_umschreiben(verbindung, zuordnung, ausfuehren),
        qdrant={
            collection: qdrant_umschreiben(qdrant, collection, zuordnung, ausfuehren)
        },
        listen={name: liste_umschreiben(w, zuordnung) for name, w in listen.items()},
        ohne_konto=sorted(alte - set(zuordnung)),
        anzulegen=fehlend,
        vergeben=vergeben,
    )
