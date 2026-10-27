"""
Die SQL-Migrationen aus mvp/backend/postgres-app/migrations beim Start einspielen.

Der Dienst ruft ``einspielen`` nach ``create_all`` auf, bevor er Anfragen annimmt
(main.py). Das ist die Reihenfolge, die die Kettentests in
tests/integration/test_migrationen.py pruefen: Bestandsdatenbank, dann create_all,
dann die Skripte nach dem Namen ohne ``.sql``.

Jede Datei laeuft genau einmal; was gelaufen ist, steht in ``migrationsprotokoll``
(Modell MigrationsprotokollZeile). Neue Dateien laufen ohne Codeaenderung mit, denn
die Konvention verlangt, dass sie wiederholbar sind (README dort). Fuer die zwei
alten, die das nicht sind, steht unten in NICHT_WIEDERHOLBAR, woran man ihre Wirkung
erkennt: Sind sie schon (von Hand) eingespielt, vermerkt der Lauf sie als ``erkannt``
und startet sie nicht.

Der Protokolleintrag wird in der Transaktion des Skripts geschrieben, unmittelbar vor
dessen ``COMMIT``: Skript und Eintrag gelten zusammen oder gar nicht. Was nach dem
``COMMIT`` steht (``VACUUM FULL``), laeuft danach einzeln. Scheitert es, bleibt die
Migration festgeschrieben und als ``nachlauf_offen`` vermerkt; der naechste Start
holt nur diesen Teil nach, nicht das ganze Skript.

Scheitert die Transaktion (etwa an einer belegten Sperre), rollt sie zurueck, der
Fehler wird als ``fehlgeschlagen`` vermerkt und ``MigrationFehlgeschlagen``
geworfen. Andere Fehler (ein Skript, das sich nicht zerlegen laesst, eine
verlorene Verbindung) werfen ohne Eintrag, mit derselben Folge: Der Dienst startet nicht, Docker startet ihn neu, und der naechste Lauf
versucht das Skript wieder. Spaetere Skripte laufen bis dahin nicht, sie koennen auf
dem gescheiterten aufbauen.

Zerlegt wird wie im Konventionstest (tests/unit/test_migrationskonvention.py), ohne
SQL-Parser: Kommentare beginnen bei ``--``, Anweisungen enden an ``;``. Einzeln, weil
PostgreSQL ``VACUUM`` in einem Aufruf mit mehreren Anweisungen ablehnt.
"""

import logging
from pathlib import Path
from typing import Optional, Union

from sqlalchemy.engine import Engine

from infrastructure.database.models import MigrationsprotokollZeile

logger = logging.getLogger(__name__)

ANGEWENDET = "angewendet"
ERKANNT = "erkannt"
FEHLGESCHLAGEN = "fehlgeschlagen"
NACHLAUF_OFFEN = "nachlauf_offen"

# Schluessel der Advisory-Sperre: Zwei gleichzeitig startende Dienste spielen nicht
# beide dasselbe Skript ein, der zweite wartet und findet es dann im Protokoll.
SPERRE = 293_208_001
# Wie lange ein Start auf einen anderen wartet, der gerade einspielt; danach bricht
# er ab und Docker startet ihn neu.
WARTEN_AUF_ANDEREN_START = "10min"
# Wie lange das VACUUM FULL nach dem COMMIT auf seine Sperre wartet. Es sperrt die
# Tabelle exklusiv; ohne Grenze stuende der Start, solange jemand sie liest.
WARTEN_IM_NACHLAUF = "30s"

_SPALTE_VORHANDEN = """
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = '{tabelle}' AND column_name = '{spalte}'
    )
"""

# Die zwei Skripte, die nicht erneut laufen duerfen (README, "Erneut anwenden"), und
# je eine Abfrage, die wahr ist, wenn ihre Wirkung schon in der Datenbank steckt. Auf
# einer neuen Datenbank (init.sql, create_all) ist sie das immer.
NICHT_WIEDERHOLBAR = {
    # Ein zweiter Lauf leert search_events; actor_hash legt erst dieses Skript an.
    "2026-08-19-search-events-pseudonymisieren.sql": _SPALTE_VORHANDEN.format(
        tabelle="search_events", spalte="actor_hash"
    ),
    # Ein zweiter Lauf bricht an RENAME COLUMN ab, weil user_agent dann fehlt.
    "2026-08-25-usage-events-datensparsamkeit.sql": "SELECT NOT ("
    + _SPALTE_VORHANDEN.format(tabelle="usage_events", spalte="user_agent")
    + ")",
}

_VERMERKEN = """
    INSERT INTO migrationsprotokoll (name, status, zeitpunkt, fehler)
    VALUES (%s, %s, now(), %s)
    ON CONFLICT (name) DO UPDATE
    SET status = EXCLUDED.status, zeitpunkt = EXCLUDED.zeitpunkt,
        fehler = EXCLUDED.fehler
"""


class MigrationFehlgeschlagen(RuntimeError):
    """Eine Migration ist zurueckgerollt; der Dienst soll so nicht starten."""


def dateien(verzeichnis: Path) -> list[Path]:
    """
    Die Migrationen in der Reihenfolge der README: nach dem Namen ohne Endung,
    damit "...-suchen-ohne-treffer" vor "...-suchen-ohne-treffer-personen" laeuft.
    """
    return sorted(Path(verzeichnis).glob("*.sql"), key=lambda s: s.stem)


def zerlegen(skript: str) -> tuple[list[str], list[str]]:
    """
    Ein Skript in die Anweisungen bis vor ``COMMIT`` (mit ``BEGIN``) und die danach.

    Traegt, solange kein String ``--`` oder ``;`` enthaelt; $$-Bloecke weist es ab.
    Beides haelt die Konvention ein, die der Unit-Test prueft.
    """
    ohne_kommentare = "\n".join(
        zeile.split("--", 1)[0] for zeile in skript.splitlines()
    )
    if "$$" in ohne_kommentare:
        raise ValueError("$$-Bloecke kann die Zerlegung nicht")
    anweisungen = [a.strip() for a in ohne_kommentare.split(";") if a.strip()]
    gross = [a.upper() for a in anweisungen]
    if "COMMIT" not in gross:
        raise ValueError("kein COMMIT;")
    ende = gross.index("COMMIT")
    return anweisungen[:ende], anweisungen[ende + 1 :]


def protokoll(engine: Engine) -> dict[str, str]:
    """Status je eingespielter Datei, leer ohne Protokolltabelle."""
    roh = _eigene_verbindung(engine)
    try:
        with roh.cursor() as cur:
            cur.execute("SELECT to_regclass('migrationsprotokoll') IS NOT NULL")
            if not cur.fetchone()[0]:
                return {}
            cur.execute("SELECT name, status FROM migrationsprotokoll")
            return dict(cur.fetchall())
    finally:
        roh.close()


def einspielen(engine: Engine, verzeichnis: Union[Path, str]) -> list[str]:
    """
    Alle noch nicht eingespielten Migrationen aus ``verzeichnis`` anwenden.

    Liefert die Namen der Skripte, deren Transaktion dieser Lauf festgeschrieben hat.
    Wirft MigrationFehlgeschlagen, wenn eine zurueckrollt.
    """
    skripte = dateien(verzeichnis)
    if not skripte:
        raise FileNotFoundError(f"Keine Migrationen in {verzeichnis}")
    MigrationsprotokollZeile.__table__.create(engine, checkfirst=True)

    roh = _eigene_verbindung(engine)
    roh.dbapi_connection.autocommit = True
    eingespielt = []
    try:
        with roh.dbapi_connection.cursor() as cur:
            cur.execute(f"SET lock_timeout = '{WARTEN_AUF_ANDEREN_START}'")
            cur.execute("SELECT pg_advisory_lock(%s)", (SPERRE,))
            cur.execute("RESET lock_timeout")
            # Erst unter der Sperre lesen: Ein anderer Dienst kann gerade fertig sein.
            cur.execute("SELECT name, status FROM migrationsprotokoll")
            stand = dict(cur.fetchall())
            for skript in skripte:
                status = stand.get(skript.name)
                if status in (ANGEWENDET, ERKANNT):
                    continue
                transaktion, nachlauf = zerlegen(skript.read_text(encoding="utf-8"))
                if status != NACHLAUF_OFFEN:
                    if _wirkung_vorhanden(cur, skript.name):
                        cur.execute(_VERMERKEN, (skript.name, ERKANNT, None))
                        logger.info("Migration %s schon eingespielt", skript.name)
                        continue
                    _transaktion(cur, skript.name, transaktion, bool(nachlauf))
                    eingespielt.append(skript.name)
                if nachlauf:
                    _nachlauf(cur, skript.name, nachlauf)
    finally:
        # Schliesst die Verbindung wirklich und gibt damit auch die Sperre frei.
        roh.close()
    return eingespielt


def _eigene_verbindung(engine: Engine):
    """
    Eine Verbindung, die beim Schliessen nicht in einen Pool zurueckgeht: Sie
    traegt Autocommit und die Advisory-Sperre, beides soll keine spaetere Sitzung
    erben.
    """
    roh = engine.raw_connection()
    roh.detach()
    return roh


def _wirkung_vorhanden(cur, name: str) -> bool:
    abfrage = NICHT_WIEDERHOLBAR.get(name)
    if abfrage is None:
        return False
    cur.execute(abfrage)
    return bool(cur.fetchone()[0])


def _transaktion(cur, name: str, anweisungen: list[str], mit_nachlauf: bool) -> None:
    """Das Skript bis zum COMMIT, den Protokolleintrag in derselben Transaktion."""
    logger.info("Migration %s wird eingespielt", name)
    try:
        for anweisung in anweisungen:
            cur.execute(anweisung)
        cur.execute(
            _VERMERKEN, (name, NACHLAUF_OFFEN if mit_nachlauf else ANGEWENDET, None)
        )
        cur.execute("COMMIT")
    except Exception as fehler:
        logger.error("Migration %s fehlgeschlagen: %s", name, _erste_zeile(fehler))
        _vermerken_trotz_fehler(cur, name, FEHLGESCHLAGEN, fehler, "ROLLBACK")
        raise MigrationFehlgeschlagen(
            f"Migration {name} fehlgeschlagen, zurueckgerollt: {_erste_zeile(fehler)}"
        ) from fehler
    logger.info("Migration %s eingespielt", name)


def _nachlauf(cur, name: str, anweisungen: list[str]) -> None:
    """
    Was nach dem COMMIT steht. Ein Fehler haelt den Start nicht auf: Das Schema
    stimmt schon, es fehlt nur der zurueckgegebene Platz. Der naechste Start
    versucht es erneut.
    """
    try:
        cur.execute(f"SET lock_timeout = '{WARTEN_IM_NACHLAUF}'")
        for anweisung in anweisungen:
            cur.execute(anweisung)
        cur.execute("RESET lock_timeout")
    except Exception as fehler:
        logger.error(
            "Nachlauf von Migration %s fehlgeschlagen, folgt beim naechsten Start: %s",
            name,
            _erste_zeile(fehler),
        )
        _vermerken_trotz_fehler(cur, name, NACHLAUF_OFFEN, fehler, "RESET lock_timeout")
        return
    cur.execute(_VERMERKEN, (name, ANGEWENDET, None))


def _vermerken_trotz_fehler(
    cur, name: str, status: str, fehler: Exception, aufraeumen: str
) -> None:
    """
    Nach einem Fehler aufraeumen und ihn vermerken. Geht auch das schief (etwa
    weil die Verbindung weg ist), bleibt der urspruengliche Fehler der, den das
    Log und der Aufrufer sehen; der Eintrag fehlt dann, das Skript laeuft beim
    naechsten Start trotzdem wieder.
    """
    try:
        cur.execute(aufraeumen)
        cur.execute(_VERMERKEN, (name, status, _erste_zeile(fehler)))
    except Exception:
        logger.exception("Migration %s: Fehler nicht im Protokoll vermerkt", name)


def _erste_zeile(fehler: Exception) -> Optional[str]:
    """
    Nur die erste Zeile: Die DETAIL-Zeile von PostgreSQL nennt Werte, etwa eine
    Kennung bei einer verletzten Eindeutigkeit.
    """
    zeilen = str(fehler).strip().splitlines()
    return zeilen[0][:500] if zeilen else type(fehler).__name__
