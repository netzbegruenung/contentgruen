import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import AliasChoices, Field
from typing import Literal, Optional
from dotenv import load_dotenv

# Set up logger for module
logger = logging.getLogger(__name__)

# Load .env file if it exists (for local development)
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
    logger.debug(f"Loaded environment from {env_file}")

# Das Einbettungsmodell. Die Aehnlichkeitsschwellen in Settings sind dafuer gemessen;
# das Dockerfile laedt es beim Bauen vor und muss mitgezogen werden.
EMBEDDING_MODELL = "intfloat/multilingual-e5-base"
# Name seines Vektors in der Qdrant-Collection (Named Vector, #395): weitere Modelle
# bekommen daneben einen eigenen Namen, statt die Collection zu ersetzen.
EMBEDDING_VEKTOR = "e5_base"
# Das NLI-Modell der NLI-Stufe (#387, services/dieselbe_behauptung): mehrsprachiger
# Cross-Encoder mit XNLI-Training, MIT-Lizenz, nur fp32. Die Schwellen nli_* in Settings
# sind dafuer gemessen (tests/regression/MESSSET.md); das Dockerfile laedt es vor.
NLI_MODELL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
# Der Bestaetiger (nli_bestaetiger in Settings): zweites NLI-Modell, MIT-Lizenz (Model
# Card), fp32, rund 2,2 GB RAM. Tokenizer aus dem Basismodell (gleiches Vokabular, aber
# als schneller Tokenizer, ohne sentencepiece). Das Dockerfile laedt beide vor.
NLI_BESTAETIGER_MODELL = "joeddav/xlm-roberta-large-xnli"
NLI_BESTAETIGER_TOKENIZER = "FacebookAI/xlm-roberta-large"
# aus: nur die Einbettung entscheidet (Regel vor #387). schatten: Die Einbettung
# entscheidet, die NLI-Stufe urteilt im Hintergrund mit und wird nur gezaehlt.
# an: Die NLI-Stufe entscheidet ueber dieselbe Aussage.
NliModus = Literal["aus", "schatten", "an"]

# Wie der Mailversand mit dem SMTP-Server spricht (infrastructure/mail/versand.py).
# Nur verschluesselt: Adresse und Text der Mail gehen nie lesbar ueber das Netz.
SmtpVerschluesselung = Literal["starttls", "ssl"]


class Settings(BaseSettings):

    # Qdrant configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "content_collection"

    # Threads, die Torch fuer Einbettungen nutzt (#480). Ohne Angabe so viele wie
    # Kerne sichtbar sind. Auf einem ausgelasteten Host bremsen sich viele Threads
    # gegenseitig aus; in #478 dauerte eine kurze Einbettung mit 8 Threads Sekunden,
    # mit 2 Zehntelsekunden. Gilt fuer den ganzen Prozess.
    embedding_threads: Optional[int] = Field(default=None, ge=1)

    # Application database configuration (PostgreSQL for usage tracking, votes, etc.)
    app_database_url: str = (
        "postgresql+psycopg2://app_user:changeme@localhost:5433/gutgesagt_app"
    )

    def _get_project_root(self) -> str:
        """Get the project root directory path."""
        config_file_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up from core -> app -> semantic-search-service -> backend -> mvp
        return os.path.abspath(os.path.join(config_file_dir, "..", "..", "..", ".."))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Trim any whitespace from the qdrant_url
        if self.qdrant_url:
            self.qdrant_url = self.qdrant_url.strip()

        # Set up paths based on environment (Docker vs Local)
        if os.getenv("DOCKER_CONTAINER") == "true":
            # Running in Docker - paths MUST be provided via environment variables
            if not self.data_path:
                self.data_path = os.getenv(
                    "SEMANTIC_SEARCH_DATA_PATH", "/data/seed/v1.0"
                )
            if not self.metadata_path:
                self.metadata_path = os.getenv(
                    "SEMANTIC_SEARCH_METADATA_PATH", "/metadata"
                )
            if not self.migrations_path:
                self.migrations_path = "/migrations"
        else:
            # Running locally - use relative paths from project root
            project_root = self._get_project_root()
            if not self.data_path:
                self.data_path = os.path.join(project_root, "data", "seed", "v1.0")
            if not self.metadata_path:
                self.metadata_path = os.path.join(project_root, "temp_data", "metadata")
            if not self.migrations_path:
                self.migrations_path = os.path.join(
                    project_root, "backend", "postgres-app", "migrations"
                )

        # Legacy compatibility - will be removed in future version
        self.initial_data_path = self.data_path
        self.index_initial_data_path = os.path.join(self.data_path, "index_data")

        # Validate paths at startup
        self._validate_paths()

        # Log configuration
        logger = logging.getLogger(__name__)
        logger.debug(f"Data path: {self.data_path}")
        logger.debug(f"Metadata path: {self.metadata_path}")

    initial_data_author: str = "Gut gesagt Team"

    # Logging configuration
    log_level: str = "INFO"
    log_file: Optional[str] = None

    def get_logging_config(self):
        """Get logging configuration object."""
        from core.logging import LoggingConfig
        import os

        # Show logger names only if explicitly requested
        show_names = (
            os.getenv("SEMANTIC_SEARCH_SHOW_LOGGER_NAMES", "").lower() == "true"
        )

        return LoggingConfig(
            level=self.log_level, file_path=self.log_file, show_logger_name=show_names
        )

    # Business logic configuration

    # Dublettenpruefung. Die Schwellen gelten nur fuer EMBEDDING_MODELL - bei einem
    # Modellwechsel neu messen (tests/regression/test_aehnlichkeit_messset.py).
    # Normalisiert gleicher Text zaehlt immer als dasselbe, unabhaengig vom Score
    # (utils/text_normalisierung.py).
    #
    # Aussage still wiederverwenden: query/query-Einbettung, >= Schwelle.
    # Modell: intfloat/multilingual-e5-base. Gesetzt an 77 Paaren (hoechster
    # D-Wert 0,969), in Stufe 2 mit echten Formularentscheidungen ueberpruefen.
    # Das Messset mit Paar-Labels (tests/regression/MESSSET.md) zeigt: Verneinungen,
    # Gegenteile und Fragen liegen auch ueber 0,98 - das faengt erst #387 ab.
    # Inhaltlich aehnliche Aussagen werden nicht still uebernommen, sondern im
    # Formular vorgeschlagen (aussage_vorschlag_schwelle).
    statement_similarity_threshold: float = 0.98
    # NLI-Stufe (#387): zweite Stufe der Pruefung auf dieselbe Aussage. Gilt in
    # StatementService fuer alle Wege (Formular, Suche, Seeding). Ohne verfuegbares
    # Modell gilt die Schwelle oben. Gemessen am Messset (tests/regression/MESSSET.md,
    # Abschnitt NLI-Stufe): tau und kappa am Train-Teil, Ergebnis am Test-Teil.
    dieselbe_aussage_nli: NliModus = "schatten"
    # Kandidaten: Vektortreffer ab dieser query/query-Aehnlichkeit, hoechstens so viele.
    # Das niedrigste gleich-Paar der Aussagen liegt bei 0,887.
    nli_kandidaten_ab: float = Field(default=0.85, ge=0.0, le=1.0)
    nli_kandidaten_hoechstens: int = Field(default=5, ge=1, le=10)
    # tau: beide Richtungen folgern mindestens so sicher. kappa: keine Richtung
    # widerspricht mit dieser Wahrscheinlichkeit oder mehr.
    nli_folgerung_ab: float = Field(default=0.95, ge=0.0, le=1.0)
    nli_widerspruch_unter: float = Field(default=0.05, ge=0.0, le=1.0)
    # Bestaetiger: Ein Kandidat wird auch dann dieselbe Aussage, wenn das zweite Modell
    # (NLI_BESTAETIGER_MODELL) mit tau und kappa dieselbe Behauptung sieht und das erste
    # nicht widerspricht (kappa) und beidseitig mindestens nli_bestaetiger_veto_ab
    # folgert (regel.bestaetigt). Gerechnet wird nur in diesem Band. Aus, solange die
    # Ziel-VM die rund 2,2 GB zusaetzlich nicht nachweislich hat; wirkt nur, wenn die
    # NLI-Stufe nicht aus ist. Gemessen in tests/regression/MESSSET.md und SUCHTESTSET.md.
    nli_bestaetiger: bool = False
    nli_bestaetiger_veto_ab: float = Field(default=0.1, ge=0.0, le=1.0)
    # CPU-Threads: wie die Einbettung (embedding_threads); torch.set_num_threads gilt
    # prozessweit, ein eigener Wert fuer das NLI-Modell braeche die Einbettung.
    # Kommentar-Dublette: passage/passage-Einbettung, >= Schwelle.
    # Modell: intfloat/multilingual-e5-base. Umformulierungen hoechstens 0,972,
    # trivial abweichende Kopien und Kopien mit angehaengter Herkunft ab 0,996, andere
    # Kommentare zur selben Aussage hoechstens 0,899. Nur klein geschrieben erreicht
    # 0,955 - das faengt die Normalform. Der Abstand der Umformulierungen zur Schwelle
    # (0,003) ist kleiner als die Toleranz des Messsets in tests/regression (0,005):
    # Wer Schwelle oder Modell aendert, misst die Kommentar-Paare neu.
    commentary_similarity_threshold: float = 0.975
    # Hintergrundinfo-Dublette: dieselbe Einbettung und Schwelle wie beim Kommentar.
    # Gemessen an Hintergrundinfo-Paaren (Zahlen in tests/regression/MESSSET.md):
    # Derselbe Text mit anderer Zahl liegt darueber und gilt als Dublette,
    # Umformulierungen zum Teil darunter. Die Schwelle trennt das nicht; siehe #387.
    generic_text_similarity_threshold: float = 0.975
    # Vorschlaege im Feld "Antwort auf" (#387, frueher Konstante im Frontend):
    # Aussagen ab dieser query/query-Aehnlichkeit. Gemessen fuer EMBEDDING_MODELL
    # (passende Aussagen 0,892-0,940). Widerspricht eine Aussage dem Getippten in einer
    # Richtung mindestens so wahrscheinlich, schlaegt das Feld sie nicht vor. Der Filter
    # wirkt schon im Schattenbetrieb (#387: zuerst als Filter der Vorschlaege), nur bei
    # dieselbe_aussage_nli = aus nicht.
    aussage_vorschlag_schwelle: float = Field(default=0.885, ge=0.0, le=1.0)
    aussage_vorschlag_widerspruch_ab: float = Field(default=0.5, ge=0.0, le=1.0)
    default_search_limit: int = 10
    max_reply_suggestions: int = 50
    statement_search_limit: int = 5
    min_reply_suggestions_for_search: int = 1

    # Konten im Realm von Gut gesagt anlegen, wenn jemand eine Einladung einloest (#429).
    # Ohne URL, Client und Secret lassen sich Einladungen nur verwalten, nicht einloesen.
    # Einrichten: docs/KEYCLOAK_REALM.md. keycloak_url ist die Basis ohne /realms/...
    keycloak_url: Optional[str] = None
    keycloak_realm: str = "gutgesagt"
    keycloak_admin_client_id: Optional[str] = None
    keycloak_admin_client_secret: Optional[str] = None
    # Wohin der Link in der Mail "Passwort festlegen" danach fuehrt: Client der App und
    # ihre Adresse. Ohne beide endet er auf der Kontoseite von Keycloak.
    keycloak_app_client_id: Optional[str] = None
    app_url: Optional[str] = None

    # Mailversand an meldende Personen (#493): Eingangsbestaetigung und Entscheidung
    # nach Art. 16 Abs. 4 und 5 DSA (infrastructure/mail/versand.py). Ohne Host und
    # Absender geht keine Mail hinaus; die Entscheidung teilt dann ein Admin per Hand
    # mit. Einrichten: docs/DEPLOYMENT.md, "Mail".
    smtp_host: Optional[str] = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_benutzer: Optional[str] = None
    smtp_passwort: Optional[str] = None
    # starttls (Port 587) oder ssl (Port 465); unverschluesselt verschickt der Dienst nicht
    smtp_verschluesselung: SmtpVerschluesselung = "starttls"
    mail_absender: Optional[str] = None
    # Wohin Antworten gehen; ohne Angabe an den Absender. Die Mail der Entscheidung
    # nennt die Antwort als Weg, gegen sie vorzugehen: keine Adresse, die nichts annimmt.
    mail_antwort_an: Optional[str] = None

    # Admin users (comma-separated list)
    admin_users: str = ""

    def is_admin_user(self, user_id: Optional[str]) -> bool:
        """Check if a user is an admin.

        Args:
            user_id: User identifier to check

        Returns:
            True if user is admin, False otherwise
        """
        if not user_id or not self.admin_users:
            return False
        admin_list = [u.strip() for u in self.admin_users.split(",") if u.strip()]
        return user_id in admin_list

    # Startkonten (GLOSSARY.md "Startkonto", #352): Kennungen von Beta-Zugaengen,
    # unter denen das Gruendungsteam den Startbestand schreibt, kommagetrennt wie
    # admin_users. Ein Startkonto vergibt keine Nutzung und keine Stimmen, die andere
    # sehen oder die Punkte bringen, und sammelt selbst keine Punkte. Nutzung durch ein
    # Startkonto wird gar nicht erst gezaehlt; Nutzung von davor ist nicht mehr
    # zuzuordnen (usage_events traegt keine Kennung).
    startkonten: str = ""

    def startkonto_kennungen(self) -> frozenset:
        return frozenset(u.strip() for u in self.startkonten.split(",") if u.strip())

    def ist_startkonto(self, user_id: Optional[str]) -> bool:
        return bool(user_id) and user_id in self.startkonto_kennungen()

    # Punkte (ADR 0004, #352). Standard aus.
    # ANNAHME (#352): Rechtsgrundlage ist die Einwilligung beim ersten Login, die
    # Punkte als Zweck nennt (DSFA zu #374); bis sie steht und die
    # Datenschutzerklaerung den Abschnitt hat (#222), bleibt der Schalter aus. Er
    # schaltet die Punkte (/api/v1/usage/users/me/punkte) und die Muster-Hinweise
    # fuer Admins; Entdoppelung und Startkonten wirken immer.
    punkte_aktiv: bool = False
    # Gewichte und Deckel der drei Stufen (domain/punkte.py): Tun klein und je Tag
    # gedeckelt, Quests mehr, Wirkung bei anderen am meisten.
    punkte_nutzung: int = Field(default=10, ge=0)
    punkte_zustimmung: int = Field(default=5, ge=0)
    punkte_beitrag: int = Field(default=1, ge=0)
    punkte_einwurf_ausformuliert: int = Field(default=1, ge=0)
    punkte_deckel_tun_je_tag: int = Field(default=3, ge=0)
    punkte_quest: int = Field(default=4, ge=0)
    punkte_deckel_quests_je_tag: int = Field(default=8, ge=0)

    # Guete eines Beitrags (#427, domain/guete.py): Stimmen anderer zaehlen erst ab
    # so vielen verschiedenen Stimmenden (DSFA, Massnahme M5), ihr Gewicht waechst mit
    # ihrer Zahl bis hoechstens zum Anteil ``guete_stimmen_gewicht_max``; beim
    # Halbwert ist die Haelfte davon erreicht. Der Rest kommt aus dem Gegenlesen.
    guete_stimmen_ab: int = Field(default=3, ge=1)
    guete_stimmen_gewicht_max: float = Field(default=0.6, ge=0, le=1)
    guete_stimmen_halbwert: int = Field(default=5, ge=1)

    # Rate-Limit am Zaehl-Endpunkt (POST /usage/content/{id}/usage, #352): so viele
    # Kopien je Person (Besucher: je Adresse) im Fenster. Die Entdoppelung schuetzt
    # Punkte und "oft genutzt", nicht den Zaehler der Karte, der jede Kopie zaehlt.
    # 60 in 10 Minuten liegt weit ueber dem, was eine Person kopiert, und laesst
    # Raum fuer mehrere Besucher hinter einer Adresse.
    nutzung_rate_limit_anfragen: int = Field(default=60, ge=1)
    nutzung_rate_limit_minuten: int = Field(default=10, ge=1)

    # Secret key for the daily search-actor pseudonym (see SearchTrackingService).
    # Set SEMANTIC_SEARCH_ACTOR_HASH_SECRET in production so the daily-active-user
    # count stays correct across service restarts. If it is left unset a random
    # secret is generated per process: privacy-safe, but every restart starts a new
    # pseudonym space and inflates the DAU count for that day.
    actor_hash_secret: Optional[str] = None

    # Der taegliche Bereinigungsjob (services/cleanup/bereinigungsjob.py) mit den
    # Fristen der Nutzungs- und der Suchereignisse und dem Mischen abgeschlossener
    # Tage; ein Schalter fuer alles. Der fruehere Name ENABLE_USAGE_CLEANUP gilt
    # weiter, damit ein abgeschalteter Job nach dem Umbenennen nicht still wieder
    # loescht; der neue Name geht vor.
    enable_bereinigungsjob: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "SEMANTIC_SEARCH_ENABLE_BEREINIGUNGSJOB",
            "SEMANTIC_SEARCH_ENABLE_USAGE_CLEANUP",
        ),
    )
    usage_retention_days: int = 90
    # Frist der Suchereignisse (#289). Aeltere Tage verdichtet der Bereinigungsjob
    # zu Tageszaehlern ohne Pseudonym. 90 wie bei den Nutzungsereignissen: deckt die
    # laengste Auswertung ueber Einzelzeilen (searches-per-user, hoechstens 90 Tage).
    # Darum auch die Untergrenze: Kuerzer zaehlte searches-per-user still zu wenig,
    # und ein negativer Wert verdichtete den laufenden Tag (Personen doppelt).
    # Laeuft im selben Job: enable_bereinigungsjob=false schaltet auch diese Frist ab,
    # ebenso das Mischen abgeschlossener Tage (#337).
    search_event_retention_days: int = Field(default=90, ge=90)
    cleanup_hour: int = 2  # 2 AM
    cleanup_minute: int = 0

    # Polarity filtering configuration
    enable_polarity_filtering: bool = (
        True  # Enable negation detection and polarity filtering
    )
    # Polaritaetsstrafe der Suche mit dem NLI-Modell statt der Wortlisten (#574,
    # services/search/polaritaet_nli.py). aus: Wortlisten. schatten: Wortlisten
    # entscheiden, das Modell urteilt im Hintergrund mit und wird gezaehlt. an: Das Modell
    # straft Aussagen, die der Suchanfrage in beiden Richtungen mit mindestens
    # suche_polaritaet_widerspruch_ab widersprechen, und laesst ihre Antworten auch
    # direkt nicht zu; Fragen, Schlagwoerter und ohne Modell: die Wortlisten.
    # Dasselbe Modell wie die NLI-Stufe (NLI_MODELL), kein zweites im Speicher.
    # Gemessen in tests/regression/SUCHTESTSET.md (Abschnitt Polaritaet mit NLI).
    suche_polaritaet_nli: NliModus = "schatten"
    suche_polaritaet_widerspruch_ab: float = Field(default=0.9, ge=0.0, le=1.0)

    # Keyword overlap boosting configuration
    enable_keyword_overlap_boost: bool = (
        True  # Enable keyword overlap boosting for search results
    )
    keyword_overlap_boost_strength: float = (
        0.15  # Strength of keyword overlap boost/penalty (0.0-1.0)
    )

    # Path configuration
    # Override with SEMANTIC_SEARCH_DATA_PATH and SEMANTIC_SEARCH_METADATA_PATH env vars
    data_path: str = ""  # Path to seed data (e.g., /data/seed/v1.0)
    metadata_path: str = ""  # Path to persistent metadata storage
    # SQL-Migrationen, die der Dienst beim Start einspielt
    # (infrastructure/database/migrationen.py). Im Image /migrations.
    migrations_path: str = ""

    # Legacy fields - deprecated, use data_path instead
    initial_data_path: str = ""  # Deprecated: use data_path
    index_initial_data_path: str = ""  # Deprecated: for backward compatibility only

    class Config:
        # Loads all env variables starting with the prefix
        env_prefix = "SEMANTIC_SEARCH_"
        # Also load standard environment variables for logging
        env_ignore_empty = True
        # Felder mit validation_alias (enable_bereinigungsjob) auch per Feldname
        # setzbar, etwa Settings(enable_bereinigungsjob=False); aus der Umgebung
        # gelten nur die Aliase mit Praefix.
        populate_by_name = True

    def _validate_paths(self):
        """Validate that required paths exist or can be created."""
        logger = logging.getLogger(__name__)

        # Data path validation
        if not os.path.exists(self.data_path):
            if os.getenv("DOCKER_CONTAINER") == "true":
                # In Docker, missing data path is critical
                raise ValueError(
                    f"Data path does not exist: {self.data_path}\n"
                    f"Please ensure the data volume is mounted correctly in docker-compose.yml"
                )
            else:
                # For local development, warn but continue
                logger.warning(
                    f"Data path not found at {self.data_path}. "
                    f"Seeding will not be available until path exists."
                )
        else:
            # Verify expected structure exists
            expected_dirs = [
                "statements_with_commentaries",
                "statements_with_generictexts",
            ]
            missing_dirs = [
                d
                for d in expected_dirs
                if not os.path.exists(os.path.join(self.data_path, d))
            ]
            if missing_dirs and os.listdir(
                self.data_path
            ):  # Only warn if directory is not empty
                logger.debug(
                    f"Expected directories not found in {self.data_path}: {missing_dirs}"
                )

        # Create metadata directory if it doesn't exist
        os.makedirs(self.metadata_path, exist_ok=True)
        logger.debug(f"Metadata directory ensured at: {self.metadata_path}")


# Create global settings instance
settings = Settings()
