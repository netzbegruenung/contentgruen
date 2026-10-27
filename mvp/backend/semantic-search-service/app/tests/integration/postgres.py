"""
Gemeinsame Hilfen fuer Integrationstests gegen ein echtes PostgreSQL.

Die Datenbank kommt aus ``POSTGRES_TEST_DATABASE_URL`` oder, ohne die Variable,
aus einem Wegwerf-Container: dasselbe Basis-Image wie ``mvp/backend/postgres-app``,
nur an 127.0.0.1 auf einem freien Port, nach dem Lauf entfernt. Ohne Variable und
ohne Docker werden die Tests uebersprungen, ausser in der CI (``CI`` gesetzt): Dort
waere ein Ueberspringen ein falsches Gruen. Die Fixtures dazu stehen in
``conftest.py`` (``postgres_url``, ``wegwerf_schema``).

Jeder Test arbeitet in einem eigenen Schema (``search_path``) und raeumt es wieder
ab; die Daten der Datenbank bleiben unberuehrt. Das gilt auch, wenn die Variable
auf den Dev-Stack zeigt.
"""

import re
import secrets
import shutil
import subprocess
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

URL_VARIABLE = "POSTGRES_TEST_DATABASE_URL"
REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
POSTGRES_APP = REPO_WURZEL / "mvp" / "backend" / "postgres-app"
MIGRATIONEN = POSTGRES_APP / "migrations"
INIT_SKRIPT = POSTGRES_APP / "init.sql"


# Der Default von search_events.timestamp vor #256: die volle Uhrzeit statt
# Mitternacht UTC. Damit stellen Tests eine Datenbank vor der Migration her.
SUCHEREIGNIS_DEFAULT_VOR_256 = (
    "ALTER TABLE search_events ALTER COLUMN timestamp SET DEFAULT now()"
)


def migrationen() -> list:
    """
    Die Migrationen in der Reihenfolge der README: nach dem Namen ohne Endung,
    damit "...-suchen-ohne-treffer" vor "...-suchen-ohne-treffer-personen" laeuft.
    Mit Endung (sorted, ls) kaeme "-personen.sql" zuerst, vor der Tabelle.
    """
    return sorted(MIGRATIONEN.glob("*.sql"), key=lambda s: s.stem)


# Benutzer und Datenbank wie in docker-compose.dev.yml, das Passwort nur fuer diesen Lauf.
_BENUTZER = "app_user"
_DATENBANK = "gutgesagt_app"


def basis_image() -> str:
    """Das Image aus ``FROM`` im Dockerfile von postgres-app, damit die Version mitzieht."""
    dockerfile = (POSTGRES_APP / "Dockerfile").read_text(encoding="utf-8")
    return re.search(r"^FROM\s+(\S+)", dockerfile, re.MULTILINE).group(1)


def erreichbar(url: str, timeout: int = 2) -> bool:
    engine = create_engine(
        url, poolclass=NullPool, connect_args={"connect_timeout": timeout}
    )
    try:
        with engine.connect():
            return True
    except OperationalError:
        return False
    finally:
        engine.dispose()


def _docker(*argumente: str, timeout: int = 30) -> str:
    return subprocess.run(
        ["docker", *argumente],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    ).stdout.strip()


def docker_verfuegbar() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        _docker("info", "--format", "{{.ServerVersion}}")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


@contextmanager
def wegwerf_container(warten_s: int = 60) -> Iterator[str]:
    """PostgreSQL in einem Container starten, die URL liefern, danach entfernen."""
    name = f"gutgesagt-itest-postgres-{uuid.uuid4().hex[:8]}"
    passwort = secrets.token_hex(16)
    # Schon der Start steht im try: Laeuft "docker run" in den Timeout, kann der
    # Container trotzdem angelegt sein. Reste eines harten Abbruchs findet
    # "docker ps --filter label=gutgesagt-itest".
    try:
        _docker(
            "run",
            "--detach",
            "--rm",
            "--name",
            name,
            "--label",
            "gutgesagt-itest",
            "--env",
            f"POSTGRES_USER={_BENUTZER}",
            "--env",
            f"POSTGRES_PASSWORD={passwort}",
            "--env",
            f"POSTGRES_DB={_DATENBANK}",
            "--publish",
            "127.0.0.1::5432",
            basis_image(),
            # Der erste Lauf laedt das Image.
            timeout=300,
        )
        # "127.0.0.1:49153"; bei mehreren Zeilen (IPv4/IPv6) gilt die erste.
        adresse = _docker("port", name, "5432/tcp").splitlines()[0]
        url = f"postgresql+psycopg2://{_BENUTZER}:{passwort}@{adresse}/{_DATENBANK}"
        # Waehrend initdb lauscht der Server nur am Unix-Socket; TCP antwortet erst
        # der endgueltige Server.
        frist = time.monotonic() + warten_s
        while not erreichbar(url, timeout=1):
            if time.monotonic() > frist:
                raise RuntimeError(f"PostgreSQL im Container {name} startet nicht")
            time.sleep(0.5)
        yield url
    finally:
        subprocess.run(
            ["docker", "rm", "--force", name], capture_output=True, timeout=60
        )


class Datenbank:
    """
    Ein Schema in der Testdatenbank; ``get_session`` wie bei AppDatabase, damit
    die Repositories es statt der App-Datenbank nehmen koennen.
    """

    def __init__(self, url: str, schema: str, zeitzone: Optional[str] = None):
        self.url = url
        self.schema = schema
        optionen = f"-csearch_path={schema}"
        if zeitzone:
            optionen += f" -ctimezone={zeitzone}"
        # NullPool: jede Verbindung ist eine eigene Sitzung, wie bei psql.
        self.engine = create_engine(
            url, poolclass=NullPool, connect_args={"options": optionen}
        )
        self.sessions = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self):
        with self.sessions.begin() as session:
            yield session

    @contextmanager
    def mit_zeitzone(self, zeitzone: str) -> Iterator["Datenbank"]:
        """Dasselbe Schema, Sitzungen aber in einer anderen Zeitzone."""
        db = Datenbank(self.url, self.schema, zeitzone)
        try:
            yield db
        finally:
            db.engine.dispose()


@contextmanager
def schema(url: str, praefix: str = "itest") -> Iterator[Datenbank]:
    """Ein leeres Wegwerf-Schema anlegen und nach dem Block mit allem Inhalt loeschen."""
    name = f"{praefix}_{uuid.uuid4().hex[:8]}"
    verwaltung = create_engine(url, poolclass=NullPool, isolation_level="AUTOCOMMIT")
    try:
        with verwaltung.connect() as c:
            c.execute(text(f"CREATE SCHEMA {name}"))
        db = Datenbank(url, name)
        try:
            yield db
        finally:
            db.engine.dispose()
            with verwaltung.connect() as c:
                c.execute(text(f"DROP SCHEMA {name} CASCADE"))
    finally:
        verwaltung.dispose()


def anweisungen(skript: str) -> Iterator[str]:
    """
    Ein psql-Skript in einzelne Anweisungen zerlegen, ohne Kommentarzeilen.

    Einzeln, weil PostgreSQL ``VACUUM`` in einem Aufruf mit mehreren Anweisungen
    ablehnt. Die Zerlegung an ``;`` traegt, solange weder ein String noch ein
    Kommentar am Zeilenende ein Semikolon enthaelt (das prueft sie nicht) und es
    keine $$-Bloecke gibt (die weist sie ab).
    """
    ohne_kommentare = "\n".join(
        zeile for zeile in skript.splitlines() if not zeile.lstrip().startswith("--")
    )
    assert "$$" not in ohne_kommentare, "$$-Bloecke kann die Zerlegung nicht"
    for anweisung in ohne_kommentare.split(";"):
        if anweisung.strip():
            yield anweisung


def init_skript_anwenden(db: Datenbank, skript: Path) -> None:
    """
    Ein Init-Skript in einem Aufruf anwenden, wie es das Postgres-Image bei leerem
    Volume tut, aber ohne die GRANTs: Die gelten dem Schema public und der Rolle
    app_user, nicht dem Wegwerf-Schema, und aendern kein Schema.
    """
    ohne_grants = re.sub(
        r"^GRANT\b[^;]*;", "", skript.read_text(encoding="utf-8"), flags=re.MULTILINE
    )
    with db.engine.begin() as c:
        c.exec_driver_sql(ohne_grants)


def migration(db: Datenbank, skript: Path) -> None:
    """Eine Migration wie psql mit ON_ERROR_STOP anwenden: BEGIN/COMMIT stehen darin."""
    with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
        for anweisung in anweisungen(skript.read_text(encoding="utf-8")):
            c.exec_driver_sql(anweisung)
