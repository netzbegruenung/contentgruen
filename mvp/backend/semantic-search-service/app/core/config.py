import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import AliasChoices, Field
from typing import Optional
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


class Settings(BaseSettings):

    # Qdrant configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "content_collection"

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
    # Formular vorgeschlagen (0,885, Frontend VORSCHLAG_MIN_AEHNLICHKEIT).
    statement_similarity_threshold: float = 0.98
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
    default_search_limit: int = 10
    max_reply_suggestions: int = 50
    statement_search_limit: int = 5
    min_reply_suggestions_for_search: int = 1

    # OpenAI vision API (suggested Unterschrift in the image form)
    # Accepts bare OPENAI_API_KEY (SDK default) or the prefixed SEMANTIC_SEARCH_OPENAI_API_KEY.
    #
    # PRIVACY WARNING -- setting this key enables a transfer to a third country.
    # The key is the only switch: with it set, POST /api/v1/image/suggestCaption sends the
    # image URL to OpenAI in the USA when a person asks for a suggested Unterschrift.
    # Nothing is sent without that click; there is no background description (#281).
    # The privacy policy assumes this transfer does not take place. Before setting the key
    # anywhere it must be extended with a section on third-country transfer (Art. 44 ff.
    # GDPR), which also requires a data processing agreement and Art. 46 safeguards.
    openai_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "OPENAI_API_KEY", "SEMANTIC_SEARCH_OPENAI_API_KEY"
        ),
    )
    openai_vision_model: str = "gpt-4o-mini"

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

    # Usage tracking and cleanup configuration
    enable_usage_cleanup: bool = True
    usage_retention_days: int = 90
    # Frist der Suchereignisse (#289). Aeltere Tage verdichtet der Bereinigungsjob
    # zu Tageszaehlern ohne Pseudonym. 90 wie bei den Nutzungsereignissen: deckt die
    # laengste Auswertung ueber Einzelzeilen (searches-per-user, hoechstens 90 Tage).
    # Darum auch die Untergrenze: Kuerzer zaehlte searches-per-user still zu wenig,
    # und ein negativer Wert verdichtete den laufenden Tag (Personen doppelt).
    # Laeuft im selben Job: enable_usage_cleanup=false schaltet auch diese Frist ab,
    # ebenso das Mischen abgeschlossener Tage (#337).
    search_event_retention_days: int = Field(default=90, ge=90)
    cleanup_hour: int = 2  # 2 AM
    cleanup_minute: int = 0

    # Polarity filtering configuration
    enable_polarity_filtering: bool = (
        True  # Enable negation detection and polarity filtering
    )

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
