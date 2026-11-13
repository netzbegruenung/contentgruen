"""
SQLAlchemy models for application-specific data.
These models are separate from the Qdrant vector database.
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    String,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    BigInteger,
    func,
    Index,
    UUID as SQLUUID,
    Text,
    CheckConstraint,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from domain.models.meldung import MELDER_EMAIL_MAX, MELDER_NAME_MAX

Base = declarative_base()


class UsageTracking(Base):
    """Track usage statistics for each content item."""

    __tablename__ = "usage_tracking"

    content_id = Column(SQLUUID(as_uuid=True), primary_key=True)
    # server_default hier und bei UsageEvent.event_type wie in postgres-app/init.sql,
    # das beide Tabellen auch anlegt und genau diesem Modell entsprechen muss
    # (tests/integration/test_migrationen.py). default bleibt, damit das ORM den Wert
    # nach dem Flush kennt, ohne die Zeile neu zu laden.
    usage_count = Column(Integer, default=0, server_default="0", nullable=False)
    # Entdoppelte Nutzung (#352): hoechstens eine je Person (Besucher: Besuchermerkmal),
    # Beitrag und Tag. Traegt die Punkte fuer Nutzung und ueberdauert wie usage_count
    # die Frist der usage_events; usage_count bleibt der Zaehler an der Karte.
    nutzung_entdoppelt = Column(Integer, default=0, server_default="0", nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=True)
    first_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship to usage events
    events = relationship(
        "UsageEvent", back_populates="tracking", cascade="all, delete-orphan"
    )

    def increment_usage(
        self, timestamp: Optional[datetime] = None, entdoppelt: bool = False
    ):
        """Increment the usage count and update timestamps."""
        if self.usage_count is None:
            self.usage_count = 0
        self.usage_count += 1
        if entdoppelt:
            self.nutzung_entdoppelt = (self.nutzung_entdoppelt or 0) + 1
        now = timestamp or datetime.utcnow()
        self.last_used = now
        if self.first_used is None:
            self.first_used = now


class NutzungJeFassung(Base):
    """
    Wie oft jede Fassung eines Kommentars genutzt wurde (#355): je Beitrag und
    Fassung ein Zaehler, so wie usage_tracking je Beitrag.

    Ein eigener Zaehler und keine Abfrage ueber usage_events, weil deren Frist
    (cleanup_old_events) die Ereignisse nach 90 Tagen loescht; die Summe je Fassung
    soll wie die Nutzung insgesamt bleiben. Nutzung von vor #355 hat keine Fassung
    und steht nur in usage_tracking.

    Neue Tabelle: create_all legt sie beim Start an. Das Skript
    postgres-app/migrations/2026-10-29-355-nutzung-je-fassung.sql dokumentiert das
    Schema und ergaenzt usage_events.fassung.
    """

    __tablename__ = "nutzung_je_fassung"

    content_id = Column(
        SQLUUID(as_uuid=True),
        ForeignKey("usage_tracking.content_id", ondelete="CASCADE"),
        primary_key=True,
    )
    fassung = Column(String(10), primary_key=True)
    nutzung = Column(Integer, nullable=False)


class UsageEvent(Base):
    """Track individual usage events for analytics.

    Die Spalten user_id, ip_hash und user_agent sind entfallen. Keine davon
    wurde je von einer Abfrage gelesen:

    - user_id kam ueber den Live-Pfad nie an. Die Dependency las den Header
      X-User-Id, das BFF setzt X-User -- die Spalte blieb leer.
    - ip_hash war ein ungesalzener SHA-256 ueber die IP (sogar zweimal
      angewandt) und damit ueber den IPv4-Raum zurueckrechenbar.
    - user_agent stand als Rohwert mit bis zu 500 Zeichen darin; an seine Stelle
      tritt device_category mit "mobile", "tablet", "desktop" oder "unknown"
      (siehe utils/device_category.py).

    Was bleibt, traegt die Nutzungszaehlung: welcher Inhalt, welche Art
    Ereignis und wann. Die Sitzungskennung schreibt seit #446 niemand mehr.
    """

    __tablename__ = "usage_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    content_id = Column(
        SQLUUID(as_uuid=True),
        ForeignKey("usage_tracking.content_id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(
        String(50), default="copy", server_default="copy", nullable=False
    )
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Seit #446 nicht mehr geschrieben: Es gibt keine Sitzungskennung im Browser
    # mehr. Aeltere Zeilen tragen sie noch, bis sie nach ihrer Frist geloescht
    # sind; bis dahin braucht sie scripts/manual/person_loeschen.sql.
    session_id = Column(String(255), nullable=True)
    device_category = Column(String(20), nullable=True)
    # Welche Fassung eines Kommentars kopiert wurde ("kurz", "mittel", "lang",
    # #355); leer bei anderen Beitragstypen und bei Nutzung von vor #355. Traegt den
    # Zuwachs der letzten 7 Tage je Fassung; die Summe steht in nutzung_je_fassung.
    fassung = Column(String(10), nullable=True)
    # Die erste Nutzung dieser Person (Besucher: Besuchermerkmal) an diesem Beitrag und Tag
    # (#352). Nur sie zaehlt fuer "Diese Woche oft genutzt"; wer sie war, steht
    # nirgends (services/entdoppelung.py).
    entdoppelt = Column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )

    # Relationship to tracking
    tracking = relationship("UsageTracking", back_populates="events")

    # Indexes for performance
    __table_args__ = (
        Index("idx_usage_events_content_id", "content_id"),
        Index("idx_usage_events_timestamp", "timestamp"),
    )


class NutzungHeute(Base):
    """
    Pruefwerte der Nutzungen des laufenden Tages fuer die Entdoppelung (#352).

    Je Person (Besucher: Besuchermerkmal) und Beitrag ein HMAC mit einem Schluessel
    nur im Speicher (services/entdoppelung.py). Ohne ihn verraet ein Wert weder Person
    noch Beitrag. Ein eigener Task verwirft alle Zeilen vergangener Tage
    (pruefwerte_verwerfen_im_takt in services/entdoppelung.py); gespeichert bleibt nicht, wer wessen
    Beitrag genutzt hat (DSFA zu #374, Massnahme M2).
    """

    __tablename__ = "nutzung_heute"

    pruefwert = Column(String(64), primary_key=True)
    tag = Column(Date, nullable=False)

    __table_args__ = (Index("idx_nutzung_heute_tag", "tag"),)


class MusterPruefwert(Base):
    """
    Paar-Pruefwerte fuer die Muster-Hinweise (#352): je Richtung "Konto A hat einen
    Beitrag von Konto B genutzt" ein HMAC ueber beide Kennungen mit dem Fensterschluessel
    (nur im Speicher), mit dem letzten Tag dieser Richtung (services/entdoppelung.py). Welcher Beitrag, steht nirgends. Der
    taegliche Lauf verwirft Werte, die aelter als das Fenster von sieben Tagen sind
    (services/muster_hinweise_service.py).
    """

    __tablename__ = "muster_pruefwerte"

    pruefwert = Column(String(64), primary_key=True)
    tag = Column(Date, nullable=False)

    __table_args__ = (Index("idx_muster_pruefwerte_tag", "tag"),)


class GepostetPruefwert(Base):
    """
    Wer in der laufenden Kalenderwoche "Ja, gepostet" gemeldet hat (#643), als
    Pruefwert: ein HMAC ueber die Kennung mit einem Wochenschluessel nur im Speicher
    (services/gepostet_service.py). Ohne ihn verraet ein Wert die Person nicht, auch
    nicht mit Datenbank und Konfiguration. Zeilen vergangener Wochen werden zur Zahl
    in ``gepostet_wochen`` verdichtet und geloescht; welcher Beitrag kopiert wurde,
    steht nirgends.
    """

    __tablename__ = "gepostet_pruefwerte"

    pruefwert = Column(String(64), primary_key=True)
    # Der Montag der Kalenderwoche (UTC).
    woche = Column(Date, nullable=False)

    __table_args__ = (Index("idx_gepostet_pruefwerte_woche", "woche"),)


class GepostetWoche(Base):
    """
    Je vergangener Kalenderwoche die Zahl der verschiedenen Personen, die "Ja,
    gepostet" gemeldet haben (#643, der Nordstern in docs/VISION.md). Nur eine Zahl,
    keine Kennung, kein Pruefwert.
    """

    __tablename__ = "gepostet_wochen"

    woche = Column(Date, primary_key=True)
    personen = Column(Integer, nullable=False)


class MusterHinweisZeile(Base):
    """
    Ein auffaelliges Muster fuer Admins (ADR 0004, #352): zwei Konten, die innerhalb
    von sieben Tagen jeweils einen Beitrag des anderen genutzt haben. Ein Hinweis,
    keine Automatik; niemand verliert dadurch Punkte.

    konto_a ist die kleinere Kennung, konto_b die groessere. tage zaehlt die Tage, an
    denen eine Nutzung auf eine der Gegenrichtung im Fenster traf. Nach MUSTER_FRIST_TAGE ohne neuen Tag loescht der taegliche
    Lauf die Zeile (services/muster_hinweise_service.py, docs/LOESCHKONZEPT.md).
    """

    __tablename__ = "muster_hinweise"

    konto_a = Column(String(255), primary_key=True)
    konto_b = Column(String(255), primary_key=True)
    tage = Column(Integer, nullable=False)
    erster_tag = Column(Date, nullable=False)
    letzter_tag = Column(Date, nullable=False)

    __table_args__ = (
        Index("idx_muster_hinweise_letzter_tag", "letzter_tag"),
        Index("idx_muster_hinweise_konto_b", "konto_b"),
    )


class SearchEvent(Base):
    """Track search events for analytics and metrics.

    Holds no personally identifiable data. The columns query_text, user_id,
    session_id and ip_hash were dropped: query_text and ip_hash were written but
    never read by any query, and user_id/session_id are replaced by actor_hash.

    actor_hash is a keyed SHA-256 over the user or session id plus the UTC date,
    so it cannot be resolved back to a person and cannot be correlated across day
    boundaries. See SearchTrackingService._derive_actor_hash.

    timestamp holds only the UTC day (midnight UTC), never the time of day: an
    exact time could be matched against the creation time of the statement the
    same search created, and so tie the statement to the daily pseudonym.

    id is a random UUID, not a sequence: a running number would give the order of
    the searches of a day, which lines up with the order of the statements they
    created (#275). xmin and the physical row order still give that order for the
    running day; closed days have no rows here at all since #495.

    Rows live only for the running UTC day: once a day is closed, the
    Loeschfristen task compacts them into SuchenJeTagZeile and deletes them with
    their pseudonym (#495, SearchTrackingRepository.verdichten_vor).
    """

    __tablename__ = "search_events"

    id = Column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    actor_hash = Column(String(64), nullable=True)
    results_count = Column(Integer, default=0, nullable=False)
    timestamp = Column(
        DateTime(timezone=True),
        server_default=text(
            "(date_trunc('day', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC')"
        ),
        nullable=False,
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_search_events_actor_hash", "actor_hash"),
        Index("idx_search_events_timestamp", "timestamp"),
    )


class SuchenJeTagZeile(Base):
    """Tageszaehler der Suchen: was von Suchereignissen eines abgeschlossenen Tages bleibt.

    Der Task der Loeschfristen verdichtet die Suchereignisse jedes abgeschlossenen
    UTC-Tages zu einer Zeile und loescht die Einzelzeilen (#289; bis #495 erst nach
    90 Tagen). suchen zaehlt die Suchereignisse des Tages, personen die
    verschiedenen Tagespseudonyme; die Pseudonyme selbst stehen nicht hier. Siehe
    SearchTrackingRepository.verdichten_vor.

    ohne_treffer zaehlt die Suchen des Tages ohne Treffer, fuer den Anteil in der
    Bilanz (#467). Leer bei Tagen, die vor #467 verdichtet wurden: Der Wert ist
    dort nicht mehr bekannt und wird nicht geschaetzt.
    """

    __tablename__ = "suchen_je_tag"

    tag = Column(Date, primary_key=True)
    suchen = Column(Integer, nullable=False)
    personen = Column(Integer, nullable=False)
    ohne_treffer = Column(Integer, nullable=True)


class SucheOhneTrefferZeile(Base):
    """Suchen ohne Treffer, gezaehlt je Aussage und Kalenderwoche.

    anzahl zaehlt Suchen, personen verschiedene Tagespseudonyme; die Pseudonyme
    selbst stehen nicht hier.

    Traegt bewusst weder Pseudonym noch Zeitpunkt: woche ist der Montag der Woche,
    damit sich eine Zeile nicht ueber den Zeitpunkt mit search_events (und dessen
    actor_hash) verbinden laesst. Der Suchtext steht an der Aussage in Qdrant,
    hier nur deren ID. Siehe services/suchen_ohne_treffer_service.py.
    """

    __tablename__ = "suchen_ohne_treffer"

    statement_id = Column(SQLUUID(as_uuid=True), primary_key=True)
    woche = Column(Date, primary_key=True)
    anzahl = Column(Integer, nullable=False)
    personen = Column(Integer, nullable=False, server_default=text("0"))

    __table_args__ = (Index("idx_suchen_ohne_treffer_woche", "woche"),)


class FeedbackZeile(Base):
    """Feedback an das Team: Freitext und optional eine Kontaktangabe.

    Traegt bewusst keine Kennung und keine Sitzung, auch wenn die Person angemeldet
    ist, und statt eines Zeitpunkts nur den Tag. Wer eine Antwort will, schreibt
    selbst einen Kontakt dazu. Nach der Frist loescht der Dienst die Zeile ganz
    (services/feedback_service.py), erledigt oder nicht; ein Admin kann sie auch
    vorher einzeln loeschen (#425).
    """

    __tablename__ = "feedback"

    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(Text, nullable=False)
    kontakt = Column(Text, nullable=True)
    eingegangen_am = Column(Date, nullable=False)
    # Von Admins gesetzt, wenn das Feedback erledigt ist (#425); nur ein Merker,
    # ohne Zeitpunkt und ohne wer.
    erledigt = Column(Boolean, nullable=False, default=False, server_default="false")

    __table_args__ = (Index("idx_feedback_eingegangen_am", "eingegangen_am"),)


class EinladungZeile(Base):
    """Eine Einladung (#429): Wer den Code hat, legt damit ein Konto an.

    Haelt nur den Zaehler der Einloesungen, keine Mail-Adresse und keine
    Kennung: Am Konto steht nicht, ueber welche Einladung es entstand, und hier
    nicht, wer sie genutzt hat (services/einladung_service.py).
    """

    __tablename__ = "einladungen"

    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(64), nullable=False, unique=True)
    notiz = Column(Text, nullable=False)
    erlaubte_einloesungen = Column(Integer, nullable=False)
    einloesungen = Column(Integer, nullable=False, server_default=text("0"))
    # Letzter Tag (UTC), an dem die Einladung gilt.
    gueltig_bis = Column(Date, nullable=False)
    abgeschaltet = Column(Boolean, nullable=False, server_default=text("false"))
    angelegt_am = Column(Date, nullable=False)


class VarianteZeile(Base):
    """Die Verknuepfung "beruht auf" (Glossar "Variante", #356).

    Eine Zeile je Variante: Jemand hat das Original als Vorlage genommen und einen
    eigenen Beitrag gespeichert. Variante und Original sind Beitraege desselben Typs
    im Suchindex; hier stehen nur ihre IDs, keine Kennung und kein Zeitpunkt. Wer die
    Variante gespeichert hat, steht an ihr selbst (``original_author``).

    Loescht der Autor die Variante, geht die Zeile mit (api/v1/content.py), damit
    "N Varianten" am Original nur zaehlt, was es noch gibt.
    """

    __tablename__ = "varianten"

    variante_id = Column(SQLUUID(as_uuid=True), primary_key=True)
    original_id = Column(SQLUUID(as_uuid=True), nullable=False)

    __table_args__ = (Index("idx_varianten_original_id", "original_id"),)


class AussageThemaZeile(Base):
    """Ein Thema an einer Aussage, aus der festen Liste (domain/themen.py).

    Je Aussage hoechstens zwei Zeilen; das prueft AussageThemenService, nicht die
    Tabelle. zuordnungsart unterscheidet die Zuordnung von Hand von der einer spaeteren
    Automatik. Traegt bewusst weder Kennung noch Zeitpunkt: Die Zuordnungen von
    Hand sind das Testset fuer Themenvorschlaege und sollen ohne Personendaten
    exportierbar sein (services/aussage_themen_service.py).
    """

    __tablename__ = "aussage_themen"

    statement_id = Column(SQLUUID(as_uuid=True), primary_key=True)
    thema = Column(String(40), primary_key=True)
    zuordnungsart = Column(
        String(20), nullable=False, server_default=text("'von_hand'")
    )


class ContentReport(Base):
    """Track user reports of inappropriate or problematic content."""

    __tablename__ = "content_reports"

    id = Column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    content_id = Column(SQLUUID(as_uuid=True), nullable=False)
    content_type = Column(String(50), nullable=False)
    reported_by_user_id = Column(String(255), nullable=True)
    reported_by_session_id = Column(String(255), nullable=True)
    reason = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), server_default="pending", nullable=False)
    created = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    # Angaben nach Art. 16 Abs. 2 DSA (#438): Name und E-Mail-Adresse freiwillig,
    # die Erklaerung guten Glaubens Pflicht. NULL bei Meldungen von vor #438.
    # Der DSA gilt fuer Gut gesagt (entschieden in #438).
    melder_name = Column(String(MELDER_NAME_MAX), nullable=True)
    melder_email = Column(String(MELDER_EMAIL_MAX), nullable=True)
    guter_glaube = Column(Boolean, nullable=True)

    # Indexes and constraints
    __table_args__ = (
        Index("idx_content_reports_content_id", "content_id"),
        Index("idx_content_reports_status", "status"),
        Index("idx_content_reports_created", "created"),
        CheckConstraint(
            "(reported_by_user_id IS NOT NULL OR reported_by_session_id IS NOT NULL)",
            name="check_reporter_exists",
        ),
    )


class Sperre(Base):
    """Eine Sperre eines Beitrags: Sperrgrund, Begruendung und Widerspruch (#448).

    Je Beitrag hoechstens eine Sperre ohne aufgehoben_am. ``autor`` ist die Kennung
    der Person, die den Beitrag eingestellt hat, zum Zeitpunkt der Sperre; nur sie
    sieht die Sperrnachricht und darf widersprechen. Ohne ``autor`` gibt es niemanden,
    dem die Nachricht gezeigt werden kann (Glossar „Sperrnachricht“). Aufgehobene
    Sperren loescht der taegliche Lauf nach ihrer Frist
    (services/loeschfristen_service.py).
    """

    __tablename__ = "sperren"

    id = Column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    content_id = Column(SQLUUID(as_uuid=True), nullable=False)
    sperrgrund = Column(String(40), nullable=False)
    begruendung = Column(Text, nullable=False)
    gesperrt_von = Column(String(255), nullable=True)
    gesperrt_am = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    autor = Column(String(255), nullable=True)
    aufgehoben_am = Column(DateTime(timezone=True), nullable=True)
    widerspruch = Column(Text, nullable=True)
    widerspruch_am = Column(DateTime(timezone=True), nullable=True)
    # Ergebnis der erneuten Pruefung nach einem Widerspruch: "sperre_bleibt" oder
    # "entsperrt"; leer, solange der Widerspruch offen ist oder keiner vorliegt.
    pruefergebnis = Column(String(20), nullable=True)
    pruefung_begruendung = Column(Text, nullable=True)
    geprueft_von = Column(String(255), nullable=True)
    geprueft_am = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "idx_sperren_aktiv_je_beitrag",
            "content_id",
            unique=True,
            postgresql_where=text("aufgehoben_am IS NULL"),
        ),
        Index("idx_sperren_autor", "autor"),
        Index("idx_sperren_aufgehoben_am", "aufgehoben_am"),
    )


class Einwurf(Base):
    """
    Ein Einwurf in den Fangkorb: Link, Screenshot-URL oder ein Satz, roh, wie
    eingeworfen.

    Bewusst eine eigene Tabelle und kein Qdrant-Inhalt (siehe docs/archiv/ROHINPUT.md):
    Ein Einwurf wird nie gesucht oder kopiert, aber sein Zustand aendert sich - und
    eine spaetere Zuweisung ("ich nehm das") ist ein Wettlauf zweier Nutzer um
    dieselbe Zeile, den nur eine Transaktion entscheidet.

    submitted_by ist absichtlich nullable: der geplante Instagram-Share-Eingang
    kommt ohne Browser-Session an. Heute schreibt der Web-Eingang immer eine
    Nutzerkennung.
    """

    __tablename__ = "raw_inputs"

    id = Column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    content = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    submitted_by = Column(String(255), nullable=True)
    source_channel = Column(String(50), server_default="web", nullable=False)
    status = Column(String(20), server_default="open", nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Wer als Erste/r einen Satz gespeichert hat. Weitere Saetze anderer Personen
    # aendern das nicht; wer den Einwurf mit einem Beitrag verknuepft hat (der
    # Ausformulierer), steht an der Verknuepfung (raw_input_content_links.created_by).
    destilled_by = Column(String(255), nullable=True)
    # Kennung des CC0-Hinweises beim Einwerfen (#431, domain/cc0_hinweis.py);
    # NULL bei Einwuerfen von davor und aus Kanaelen ohne Formular.
    cc0_wortlaut = Column(String(64), nullable=True)

    __table_args__ = (
        Index("idx_raw_inputs_status", "status"),
        Index("idx_raw_inputs_created_at", "created_at"),
        Index("idx_raw_inputs_submitted_by", "submitted_by"),
        # Ein leerer Einwurf ist kein Einwurf. Es ist die einzige inhaltliche
        # Pflicht, die der Fangkorb vertraegt - alles Weitere waere schon
        # Destillieren.
        CheckConstraint(
            "(content IS NOT NULL OR url IS NOT NULL OR image_url IS NOT NULL)",
            name="check_raw_input_not_empty",
        ),
    )


class AusformuliertIn(Base):
    """
    Ausformuliert in (Glossar): die Verknuepfung zwischen einem Einwurf und dem Beitrag, mit dem er ausformuliert
    wurde: einem neu gespeicherten oder, bei einer Dublette, dem vorhandenen.

    Geschrieben wird sie, wenn der Destillier-Ablauf den Einwurf mit dem Beitrag
    verknuepft (``PATCH /rawinput/{id}/status``). Sie existiert von Anfang an, weil die
    Beziehung n:m ist: ein Einwurf kann mit einem Kommentar *und* einer
    Hintergrundinfo verknuepft sein, und ein Beitrag mit mehreren Einwuerfen. Ein Feld
    ``resulting_content_id`` auf ``raw_inputs`` waere billiger und genau die
    Blockade, die spaeter teuer wird (docs/archiv/ROHINPUT.md, Abschnitt 6).

    ``content_id`` zeigt auf einen Qdrant-Punkt und ist deshalb kein Fremdschluessel;
    ``raw_input_id`` ist einer, mit ON DELETE CASCADE, damit ein Loeschen aus
    Datenschutzgruenden oder nach der Loeschfrist (services/loeschfristen_service.py)
    keine Verweise auf Nichts hinterlaesst.

    ``created_by`` haelt fest, *wer* verknuepft hat: den Ausformulierer. Das ist die
    Rolle, die ``last_modified_by`` am Beitrag nicht bewahrt, und die Voraussetzung
    dafuer, spaeter Autor und Ausformulierer getrennt anzuerkennen: Bei einem
    vorhandenen Beitrag wird der Ausformulierer nicht dessen Autor.
    """

    __tablename__ = "raw_input_content_links"

    id = Column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    raw_input_id = Column(
        SQLUUID(as_uuid=True),
        ForeignKey("raw_inputs.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_id = Column(SQLUUID(as_uuid=True), nullable=False)
    created_by = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Welcher Satz ausformuliert wurde. SET NULL, weil ein geleerter Satz seine
    # Zeile loescht - die Verknuepfung mit dem Beitrag bleibt trotzdem bestehen.
    draft_id = Column(
        SQLUUID(as_uuid=True),
        ForeignKey("raw_input_drafts.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Typ des Beitrags (ContentType-Wert); die Fangkorb-Karte nimmt dessen Farbe an.
    # NULL bei Verknuepfungen aus der Zeit vor Fangkorb v2.
    content_type = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_raw_input_links_raw_input_id", "raw_input_id"),
        Index("idx_raw_input_links_content_id", "content_id"),
        Index("idx_raw_input_links_draft_id", "draft_id"),
        # Dieselbe Paarung nur einmal - zweimal verknuepft zaehlt spaeter sonst
        # doppelt.
        Index(
            "idx_raw_input_links_unique",
            "raw_input_id",
            "content_id",
            unique=True,
        ),
    )


class Satz(Base):
    """
    Der Satz einer Person zu einem Einwurf ("Was ist der Punkt? Ein Satz.").

    Gehoert zu (Einwurf, Person) und nicht zum Einwurf allein: mehrere Leute
    duerfen denselben Einwurf gleichzeitig destillieren, jede Person mit ihrem
    eigenen Satz. Aus dem Satz wird spaeter der Titel des Beitrags; das Limit
    (120 Zeichen, wie der Titel) prueft das DTO, nicht die Datenbank.

    Gespeichert wird per Upsert auf den eindeutigen Index (raw_input_id, user_id).
    Ein leerer Satz wird nicht abgelegt: dann wird die Zeile geloescht statt ""
    abzulegen, damit "hat einen eigenen Satz" genau eine Bedeutung hat.
    """

    __tablename__ = "raw_input_drafts"

    id = Column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    raw_input_id = Column(
        SQLUUID(as_uuid=True),
        ForeignKey("raw_inputs.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(String(255), nullable=False)
    sentence = Column(Text, nullable=False)
    # Kennung des CC0-Hinweises beim letzten Speichern des Satzes (#431); NULL bei
    # Saetzen von davor.
    cc0_wortlaut = Column(String(64), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_raw_input_drafts_user_id", "user_id"),
        # Genau ein Satz je Person und Einwurf - der Upsert haengt daran.
        Index(
            "idx_raw_input_drafts_unique",
            "raw_input_id",
            "user_id",
            unique=True,
        ),
    )


class User(Base):
    """
    Der Anzeigename einer Person, wie Karten ihn beim Autor und Einwerfer zeigen.

    Einzige Stelle, an der ein Name gespeichert wird: Beitraege in Qdrant und
    Einwuerfe tragen nur die Kennung, der Name wird beim Ausliefern dazugelesen.
    Abgeleitet wird er im BFF aus den Claims ("Anna B.") und kommt im Header
    X-User-Display-Name an; hier wird er nur abgelegt
    (services/anzeigename_service.py). Eine Person ohne Zeile hat keinen Namen,
    die Karte zeigt dann "Mitglied".

    Neue Tabelle: create_all legt sie beim Start an. Das Skript
    postgres-app/migrations/2026-10-11-anzeigenamen.sql dokumentiert das Schema.
    """

    __tablename__ = "users"

    user_id = Column(String(255), primary_key=True)
    anzeigename = Column(String(100), nullable=False)
    aktualisiert_am = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GeseheneNutzung(Base):
    """
    Wie oft die Beitraege einer Person genutzt waren, als sie es zuletzt gezeigt
    bekam: der Stand fuer die Rueckmeldung beim Anmelden ("Seit deinem letzten Besuch
    wurden deine Beitraege N-mal genutzt", #349). N ist die Nutzung jetzt minus
    dieser Stand.

    Bewusst ein Zaehlerstand und kein Zeitpunkt: Die Tabelle haelt nicht fest, wann
    jemand die App geoeffnet hat, und haengt nicht an der Frist der usage_events.

    Neue Tabelle: create_all legt sie beim Start an. Das Skript
    postgres-app/migrations/2026-10-27-gesehene-nutzung.sql dokumentiert das Schema.
    Loeschen: docs/LOESCHKONZEPT.md, Schritt 2.
    """

    __tablename__ = "gesehene_nutzung"

    user_id = Column(String(255), primary_key=True)
    nutzung = Column(Integer, nullable=False)


class Art9EinwilligungZeile(Base):
    """
    Eine Art.-9-Einwilligung einer Person (#489): wann sie eingewilligt hat, welchem
    Wortlaut (Kennung aus domain/art9_einwilligung.py) und wann sie widerrufen hat.
    Es gilt die juengste Zeile der Kennung; ohne Zeile, oder ist die juengste
    widerrufen, hat die Person nicht eingewilligt.

    Ein Widerruf setzt ``widerrufen_am``, eine erneute Einwilligung ist eine neue
    Zeile. So bleibt fuer jeden Zeitraum belegt, ob die Verarbeitung auf einer
    Einwilligung beruhte (Art. 7 Abs. 1 DSGVO).

    Neue Tabelle: create_all legt sie beim Start an. Das Skript
    postgres-app/migrations/2026-11-05-art9-einwilligung.sql dokumentiert das Schema.
    Loeschen: docs/LOESCHKONZEPT.md, Schritt 2.
    """

    __tablename__ = "art9_einwilligungen"

    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False)
    wortlaut = Column(String(64), nullable=False)
    eingewilligt_am = Column(DateTime(timezone=True), nullable=False)
    widerrufen_am = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_art9_einwilligungen_user", "user_id", "eingewilligt_am"),
    )


class Art9OhneEinwilligungZeile(Base):
    """
    Die Person ist nach der Anmeldung bewusst ohne Art.-9-Einwilligung weitergegangen
    (UX-Review B2, Entscheidung Maintainer 13.11.2026): je Kennung hoechstens eine Zeile,
    mit dem Wortlaut, der da galt, und dem Zeitpunkt. Damit fuehrt die App nicht bei
    jedem Start wieder auf /einwilligung. Am Konto statt im Browser, bis Paragraf 25
    TDDDG fuer Browser-Eintraege geprueft ist.

    Eine Einwilligung loescht die Zeile, ein Widerruf laesst sie stehen (dann gilt
    ohnehin "widerrufen"). Neue Tabelle: create_all legt sie an; das Skript
    postgres-app/migrations/2026-11-13-art9-ohne-einwilligung.sql dokumentiert das
    Schema. Loeschen: mit dem Konto (docs/LOESCHKONZEPT.md, Schritt 2).
    """

    __tablename__ = "art9_ohne_einwilligung"

    user_id = Column(String(255), primary_key=True)
    wortlaut = Column(String(64), nullable=False)
    entschieden_am = Column(DateTime(timezone=True), nullable=False)


class AbzeichenSichtbarkeitZeile(Base):
    """
    Eine Antwort auf die Frage, ob andere Angemeldete die Meilenstein-Abzeichen der
    Person an ihrem Anzeigenamen sehen (#351, GLOSSARY.md "Zustimmung zur
    Sichtbarkeit"). Es gilt die juengste Zeile der Kennung; ``zeigen`` ist die
    Antwort, ``wortlaut`` die Kennung der Frage (domain/abzeichen_sichtbarkeit.py).

    Auch ein Nein ist eine Zeile, damit die App nicht erneut fragt. Jede Aenderung ist
    eine neue Zeile: So bleibt belegt, wann die Person zugestimmt und wann sie
    zurueckgenommen hat (Art. 7 Abs. 1 DSGVO).

    Neue Tabelle: create_all legt sie beim Start an. Das Skript
    postgres-app/migrations/2026-11-09-351-abzeichen-sichtbarkeit.sql dokumentiert
    das Schema. Loeschen: docs/LOESCHKONZEPT.md, Schritt 2.
    """

    __tablename__ = "abzeichen_sichtbarkeit"

    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False)
    zeigen = Column(Boolean, nullable=False)
    wortlaut = Column(String(64), nullable=False)
    beantwortet_am = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_abzeichen_sichtbarkeit_user", "user_id", "beantwortet_am"),
    )


class LoeschauftragZeile(Base):
    """
    Ein Loeschauftrag nach dem Widerruf der Art.-9-Einwilligung (GLOSSARY.md
    "Loeschauftrag"): wessen Mitwirkung den Personenbezug verliert, seit wann, bis
    wann (``frist``, sieben Tage nach dem Anlegen) und wann ein Admin den Loeschablauf
    ausgefuehrt hat (services/loeschauftrag_service.py).

    Je Person hoechstens ein offener Auftrag (Index ``idx_loeschauftraege_offen``):
    Ein zweiter Widerruf legt keinen zweiten an. Erledigte gehen nach ihrer Frist
    (services/loeschfristen_service.py), offene bleiben, bis ein Admin sie ausfuehrt.

    Neue Tabelle: create_all legt sie beim Start an. Das Skript
    postgres-app/migrations/2026-11-13-loeschauftraege.sql dokumentiert das Schema.
    Loeschen: docs/LOESCHKONZEPT.md, Schritt 2 und "Fristen".
    """

    __tablename__ = "loeschauftraege"

    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False)
    angelegt_am = Column(DateTime(timezone=True), nullable=False)
    frist = Column(DateTime(timezone=True), nullable=False)
    erledigt_am = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "idx_loeschauftraege_offen",
            "user_id",
            unique=True,
            postgresql_where=text("erledigt_am IS NULL"),
        ),
        Index("idx_loeschauftraege_erledigt_am", "erledigt_am"),
    )


class MigrationsprotokollZeile(Base):
    """
    Welche Migration aus postgres-app/migrations eingespielt ist, eine Zeile je Datei.

    Schreibt nur infrastructure/database/migrationen.py beim Start des Dienstes.
    status ist "eingespielt", "erkannt" (Wirkung schon vorhanden, von Hand
    eingespielt), "fehlgeschlagen" (laeuft beim naechsten Start erneut) oder
    "nachlauf_offen" (festgeschrieben, nur das VACUUM danach fehlt noch). fehler
    haelt nur die erste Zeile der Fehlermeldung, ohne die DETAIL-Zeile mit Werten.

    Kein Skript in migrations/: Die Tabelle muss vor dem ersten Skript da sein,
    eine eigene Datei liefe erst nach allen aelteren. create_all legt sie an.
    """

    __tablename__ = "migrationsprotokoll"

    name = Column(String(200), primary_key=True)
    status = Column(String(20), nullable=False)
    zeitpunkt = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fehler = Column(Text, nullable=True)
