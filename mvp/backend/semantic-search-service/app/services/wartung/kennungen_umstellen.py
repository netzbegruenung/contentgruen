"""
Kennungen auf den Realm von Gut gesagt umstellen (#487), einmalig vor dem Umstellen
der BFF (docs/KEYCLOAK_REALM.md, "Reihenfolge beim Umstellen").

Mitglieder der Netzbegruenung bekommen im eigenen Realm ein neues Konto und damit
eine neue Kennung. Die Zuordnung alt -> neu kommt aus dem Realm: Das neue Konto ist
mit dem Identity Provider ``netzbegruenung`` verknuepft, und die Kennung dort ist die
alte (infrastructure/keycloak_konten.py, ``kennungen_zuordnen``).

Beta-Zugaenge aus managed-users.json (#488) ziehen im selben Lauf um: Ihr Konto im
Realm ist das mit ihrer Mail-Adresse; fehlt es, legt der Lauf eins mit Passwort an,
und Keycloak schickt "Passwort festlegen".

Umgeschrieben wird ueberall, wo eine Kennung steht: die Spalten in PostgreSQL
(``SPALTEN``, dieselben wie im Loeschkommando mvp/scripts/manual/person_loeschen.sql),
die vier Felder an Beitraegen in Qdrant und Listen aus der Konfiguration (Admins), deren
neue Werte der Lauf ausgibt; die Loeschliste bekommt die neuen Kennungen dazu.

Ohne ausfuehren=True wird nur gezaehlt (Trockenlauf). Idempotent: Nach einem Lauf
steht keine alte Kennung mit Konto im Realm mehr da, ein zweiter zaehlt null; nur Saetze,
die wegen eines Satzes der neuen Kennung am selben Einwurf stehen bleiben, nennt er
wieder. Bricht ein Lauf zwischen PostgreSQL und Qdrant ab, holt ein zweiter den Rest
nach. Laeuft die App waehrenddessen, kann eine Aenderung an einem Beitrag zwischen
Lesen und Schreiben verloren gehen; deshalb in einer ruhigen Zeit laufen lassen.

Aufruf: mvp/scripts/manual/kennungen_umstellen.py
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, NamedTuple, Optional, Set

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

from domain.interfaces.konten_im_realm import BetaZugang, IKennungenImRealm
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
    "art9_einwilligungen": ("user_id",),
    # Zustimmung zur Sichtbarkeit der Abzeichen (#351): geht mit der Person mit.
    "abzeichen_sichtbarkeit": ("user_id",),
    # Loeschauftraege nach dem Widerruf (DSFA R9b): Ein offener muss die Kennung
    # treffen, unter der Beitraege und Einwuerfe dann stehen.
    "loeschauftraege": ("user_id",),
    "votes": ("user_id",),
    "raw_inputs": ("submitted_by", "destilled_by"),
    "raw_input_drafts": ("user_id",),
    "raw_input_content_links": ("created_by",),
    "content_reports": ("reported_by_user_id", "reviewed_by"),
    "sperren": ("autor", "gesperrt_von", "geprueft_von"),
}

# Spalten mit einer Kennung, die der Lauf bewusst stehen laesst. Muster-Hinweise
# (#352) entstehen nur mit eingeschalteten Punkten, und die kommen erst nach dem
# Umstellen (docs/DSFA.md); beim Lauf ist die Tabelle leer. Stuende doch ein
# Hinweis darin, zeigte er die alte Kennung ohne Anzeigenamen und ginge nach acht
# Wochen (docs/LOESCHKONZEPT.md).
NICHT_UMGESCHRIEBEN = {"muster_hinweise": ("konto_a", "konto_b")}

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
    """Admins: zugeordnete Kennungen ersetzt, Reihenfolge wie vorher."""
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
# weitere Spalten des Schluessels)
_ZEILE_DER_NEUEN_GEWINNT = {
    ("users", "user_id"): (),
    ("gesehene_nutzung", "user_id"): (),
    ("votes", "user_id"): ("content_id",),
}


# Ein Satz, der mit alter Kennung stehen bleibt: Die neue hat am selben Einwurf schon
# einen. Solange es ihn gibt, bleibt auch die Zeile der alten Kennung in users, sonst
# verloere er seinen Anzeigenamen.
_SATZ_BLEIBT = (
    "EXISTS (SELECT 1 FROM raw_input_drafts AS d"
    " JOIN raw_input_drafts AS dn ON dn.raw_input_id = d.raw_input_id"
    " WHERE d.user_id = z.alt AND dn.user_id = z.neu)"
)


def _gleicher_schluessel(spalten: Iterable[str]) -> str:
    return "".join(f" AND n.{s} = t.{s}" for s in spalten)


def postgres_umschreiben(
    verbindung: Connection, zuordnung: Zuordnung, ausfuehren: bool = False
) -> PostgresBericht:
    """
    Alles in einer Transaktion; der Trockenlauf fuehrt dieselben Anweisungen aus und
    rollt zurueck, die Zahlen sind also dieselben wie beim echten Lauf mit derselben
    Zuordnung.
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
    bedingung = ""
    if schluessel is not None:
        neue_hat_zeile = (
            f"EXISTS (SELECT 1 FROM {tabelle} AS n"
            f" WHERE n.{spalte} = z.neu{_gleicher_schluessel(schluessel)})"
        )
        bleibt = f" AND NOT {_SATZ_BLEIBT}" if tabelle == "users" else ""
        anzahl += verbindung.execute(
            text(
                f"DELETE FROM {tabelle} AS t USING kennungen_zuordnung AS z"
                f" WHERE t.{spalte} = z.alt AND {neue_hat_zeile}{bleibt}"
            )
        ).rowcount
        if tabelle == "users":
            # Was hier noch steht, obwohl die neue eine Zeile hat, bleibt (Satz).
            bedingung = f" AND NOT {neue_hat_zeile}"
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


def _zugeordnet(wert: Any, zuordnung: Zuordnung) -> bool:
    # Nur Zeichenketten: Ein Objekt oder eine Liste im Feld liesse sich nicht
    # nachschlagen (unhashable) und ist ohnehin keine Kennung.
    return isinstance(wert, str) and wert in zuordnung


def _traegt(eintrag: Any, schluessel: str, zuordnung: Zuordnung) -> bool:
    # Eintraege, die kein Objekt sind, ueberspringt auch _felder.
    return isinstance(eintrag, dict) and _zugeordnet(eintrag.get(schluessel), zuordnung)


def felder_ersetzt(payload: Dict[str, Any], zuordnung: Zuordnung) -> Dict[str, Any]:
    """Nur die Felder, in denen eine zugeordnete Kennung vorkommt, mit der neuen."""
    neu: Dict[str, Any] = {
        feld: zuordnung[payload[feld]]
        for feld in KENNUNGSFELDER
        if _zugeordnet(payload.get(feld), zuordnung)
    }
    for feld, schluessel in KENNUNGSLISTEN:
        eintraege = payload.get(feld) or []
        if any(_traegt(e, schluessel, zuordnung) for e in eintraege):
            neu[feld] = [
                (
                    {**e, schluessel: zuordnung[e[schluessel]]}
                    if _traegt(e, schluessel, zuordnung)
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


@dataclass
class Umstellung:
    ausgefuehrt: bool
    # alte Kennung -> Kennung im Realm, fuer alle, die umgeschrieben werden
    zuordnung: Dict[str, str]
    postgres: PostgresBericht
    # Collection -> Beitraege mit einer alten Kennung
    qdrant: Dict[str, int]
    # Name der Liste -> neue Werte (Admins)
    listen: Dict[str, List[str]]
    # Loeschliste mit den neuen Kennungen dazu (die alten bleiben)
    loeschliste: List[str]
    # Kennungen ohne verknuepftes Konto im Realm: bleiben, wie sie sind (Konten aus
    # Einladungen, Mitglieder, fuer die noch kein Konto angelegt ist). Ohne Geloeschte
    # (fuer sie wird kein Konto angelegt) und ohne Beta-Zugaenge (eigene Felder unten).
    ohne_konto: List[str]
    # Mit Mail-Adresse genannt und ohne Konto: wird beim Lauf angelegt (Trockenlauf).
    # Der Trockenlauf zaehlt ihre Zeilen und Beitraege noch nicht mit.
    anzulegen: List[str] = field(default_factory=list)
    # Konto sollte angelegt werden, die Adresse hat im Realm aber schon eins
    vergeben: List[str] = field(default_factory=list)
    # Beta-Zugaenge ohne Konto im Realm: wird beim Lauf angelegt (Trockenlauf)
    beta_anzulegen: List[str] = field(default_factory=list)
    # Beta-Zugaenge, deren Mail "Passwort festlegen" beim Lauf nicht hinausging
    beta_ohne_mail: List[str] = field(default_factory=list)
    # Beta-Zugaenge, deren Konto Keycloak beim Lauf abwies (etwa ungueltige Adresse)
    beta_abgewiesen: List[str] = field(default_factory=list)
    # Neue Kennungen der Beta-Zugaenge mit isAdmin: in die Admin-Listen eintragen
    beta_admins: List[str] = field(default_factory=list)
    # Beta-Zugaenge, die bleiben: Ihre Adresse gehoert im Realm schon zu einer anderen
    # alten Kennung (Mitglied, zweiter Beta-Zugang) oder ist dort sonst vergeben.
    # Zusammenlegen entscheidet ein Admin.
    beta_vergeben: List[str] = field(default_factory=list)


def umstellen(
    verbindung: Connection,
    qdrant: QdrantClient,
    collection: str,
    realm: IKennungenImRealm,
    identity_provider: str,
    listen: Optional[Mapping[str, List[str]]] = None,
    loeschliste: Optional[List[str]] = None,
    anzulegen: Optional[Mapping[str, str]] = None,
    beta_zugaenge: Optional[Mapping[str, BetaZugang]] = None,
    ausfuehren: bool = False,
) -> Umstellung:
    """
    Sucht alle Kennungen in PostgreSQL, Qdrant und den Listen, ordnet sie ueber den
    Realm zu und schreibt sie um. ``anzulegen`` (alte Kennung -> Mail-Adresse) legt
    beim Lauf vorher die fehlenden Konten im Realm an, mit dem Identity Provider
    verknuepft.

    Die Loeschliste wird ergaenzt, nicht umgeschrieben: Ein Cookie mit der alten
    Kennung gilt bis zu 14 Tage weiter (docs/LOESCHKONZEPT.md), die BFF muss es also
    weiter abweisen. Fuer Geloeschte wird nie ein Konto angelegt.

    ``beta_zugaenge`` (alte Kennung -> Eintrag aus managed-users.json) ordnet jeden
    Beta-Zugang dem Konto mit seiner Mail-Adresse zu, auch ohne Spuren in den Daten:
    Ohne Konto im Realm koennte er sich nach dem Umstellen nicht mehr anmelden. Beim
    Lauf legt es die fehlenden Konten an.
    """
    listen = dict(listen or {})
    geloescht = [k for k in (loeschliste or []) if _person(k)]
    alte = (
        kennungen_in_postgres(verbindung)
        | kennungen_in_qdrant(qdrant, collection)
        | {k for werte in listen.values() for k in werte if _person(k)}
        | set(geloescht)
    )
    zuordnung = realm.kennungen_zuordnen(identity_provider, sorted(alte))
    # Erst pruefen, dann Konten anlegen und Mails schicken: Bricht die Pruefung erst
    # danach ab, stehen Konten im Realm und Mails sind draussen, umgeschrieben ist nichts.
    zuordnung_pruefen(zuordnung)
    fehlend = sorted(
        k
        for k in (anzulegen or {})
        if k in alte and k not in zuordnung and k not in geloescht
    )
    vergeben: List[str] = []
    if ausfuehren and fehlend:
        angelegt = realm.konten_verknuepft_anlegen(
            identity_provider, {k: anzulegen[k] for k in fehlend}
        )
        zuordnung.update(angelegt.angelegt)
        vergeben = list(angelegt.vergeben)
        fehlend = []
    beta = {
        k: z
        for k, z in (beta_zugaenge or {}).items()
        if _person(k) and k not in zuordnung and k not in geloescht
    }
    # Im Trockenlauf gibt es die Konten aus ``anzulegen`` noch nicht; der Lauf legt sie
    # vor den Beta-Zugaengen an, und deren Adressen sind dann vergeben.
    kommende = {anzulegen[k].lower() for k in fehlend} if anzulegen else set()
    beta_ergebnis = _beta_zuordnen(realm, beta, zuordnung, ausfuehren, kommende)
    # Noch einmal mit den angelegten Konten, vor jedem Schreiben, auch fuer die Listen.
    zuordnung_pruefen(zuordnung)
    return Umstellung(
        ausgefuehrt=ausfuehren,
        zuordnung=zuordnung,
        postgres=postgres_umschreiben(verbindung, zuordnung, ausfuehren),
        qdrant={
            collection: qdrant_umschreiben(qdrant, collection, zuordnung, ausfuehren)
        },
        listen={name: liste_umschreiben(w, zuordnung) for name, w in listen.items()},
        # Ohne Doppelte: Ein zweiter Lauf bekommt die schon ergaenzte Liste.
        loeschliste=list(
            dict.fromkeys(
                [
                    *(loeschliste or []),
                    *(zuordnung[k] for k in geloescht if k in zuordnung),
                ]
            )
        ),
        ohne_konto=sorted(
            alte - set(zuordnung) - set(geloescht) - set(beta_zugaenge or {})
        ),
        anzulegen=fehlend,
        vergeben=vergeben,
        beta_anzulegen=beta_ergebnis.fehlend,
        beta_ohne_mail=beta_ergebnis.ohne_mail,
        beta_abgewiesen=beta_ergebnis.abgewiesen,
        beta_vergeben=beta_ergebnis.vergeben,
        # Alle Admins der Datei, auch die schon ueber den Identity Provider zugeordneten:
        # isAdmin gibt es im Realm nicht, ohne Eintrag in den Listen waeren sie keine mehr.
        beta_admins=[
            zuordnung[k]
            for k, z in sorted((beta_zugaenge or {}).items())
            if z.admin and k in zuordnung
        ],
    )


class _BetaErgebnis(NamedTuple):
    # noch ohne Konto (Trockenlauf) bzw. ohne Zuordnung nach dem Anlegen
    fehlend: List[str]
    ohne_mail: List[str]
    abgewiesen: List[str]
    vergeben: List[str]


def _beta_zuordnen(
    realm: IKennungenImRealm,
    beta: Mapping[str, BetaZugang],
    zuordnung: Dict[str, str],
    ausfuehren: bool,
    kommende_adressen: Set[str],
) -> _BetaErgebnis:
    """
    Ergaenzt ``zuordnung``. ``kommende_adressen``: Adressen der Konten, die der Lauf
    vorher ueber ``anzulegen`` anlegt; der Trockenlauf zeigt so denselben Konflikt wie
    der Lauf. Ein Konto, das schon einer anderen alten Kennung zugeordnet ist, bekommt
    keinen Beta-Zugang dazu: Zwei alte Kennungen auf dieselbe neue weist
    zuordnung_pruefen ab, und das erst nach dem Anlegen der Konten.
    """
    if not beta:
        return _BetaErgebnis([], [], [], [])
    vergeben: List[str] = []

    def zuordnen(kennung: str, konto: str) -> None:
        if konto in zuordnung.values():
            vergeben.append(kennung)
        else:
            zuordnung[kennung] = konto

    konten = realm.konten_nach_adresse(sorted({z.email for z in beta.values()}))
    for kennung in sorted(beta):
        konto = konten.get(beta[kennung].email.lower())
        if konto:
            zuordnen(kennung, konto)
    # Je Adresse hoechstens ein Konto anlegen; der zweite Beta-Zugang ist vergeben.
    fehlend: List[str] = []
    adressen: Set[str] = set()
    for kennung in sorted(beta):
        if kennung in zuordnung or kennung in vergeben:
            continue
        adresse = beta[kennung].email.lower()
        if adresse in adressen or adresse in kommende_adressen:
            vergeben.append(kennung)
        else:
            adressen.add(adresse)
            fehlend.append(kennung)
    if not (ausfuehren and fehlend):
        return _BetaErgebnis(fehlend, [], [], sorted(vergeben))
    angelegt = realm.konten_mit_passwort_anlegen({k: beta[k] for k in fehlend})
    for kennung, konto in angelegt.angelegt.items():
        zuordnen(kennung, konto)
    vergeben.extend(angelegt.vergeben)
    return _BetaErgebnis(
        [
            k
            for k in fehlend
            if k not in zuordnung and k not in vergeben and k not in angelegt.abgewiesen
        ],
        list(angelegt.ohne_mail),
        list(angelegt.abgewiesen),
        sorted(vergeben),
    )
