"""
Optimized logging configuration following clean code principles.

Separates concerns, uses dependency injection, and maintains testability.
"""

import hashlib
import logging
import sys
import io
import traceback
from typing import Optional, Protocol
from dataclasses import dataclass


@dataclass
class LoggingConfig:
    """Centralized logging configuration."""

    level: str = "INFO"
    file_path: Optional[str] = None
    format_string: str = "%(asctime)s | %(levelname)-8s | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    enable_console_utf8: bool = True
    show_logger_name: bool = False  # Hide verbose logger names by default


class EmojiTranslator:
    """Handles emoji to text translation (Single Responsibility)."""

    EMOJI_MAP = {
        "🚀": "[START]",
        "✅": "[OK]",
        "❌": "[ERROR]",
        "⚠️": "[WARN]",
        "🛑": "[STOP]",
        "🌱": "[SEED]",
        "📊": "[DATA]",
        "🔍": "[SEARCH]",
        "📥": "[LOAD]",
        "🔧": "[CONFIG]",
        "💾": "[SAVE]",
        "🧹": "[CLEAN]",
        "📝": "[DOC]",
        "👤": "[USER]",
        "📚": "[IMPORT]",
        "📁": "[DIR]",
        "💬": "[MSG]",
        "🎯": "[TARGET]",
    }

    @classmethod
    def translate(cls, message: str) -> str:
        """Convert emojis to safe text alternatives."""
        for emoji, replacement in cls.EMOJI_MAP.items():
            message = message.replace(emoji, replacement)
        return message


def ausnahme_ohne_meldung(ausnahme: BaseException) -> str:
    """
    Traceback einer Ausnahme samt verketteten Ausnahmen, aber ohne deren Meldungen.

    Die Meldung traegt oft, was hereinkam: eine Validierungsmeldung den abgelehnten
    Wert, ein Datenbankfehler die Parameter der Abfrage (#422). Typ und Stelle reichen,
    um den Fehler zu finden; den Wert gibt es im Log nicht.
    """
    teile: list[str] = []
    gesehen: set[int] = set()

    def anhaengen(fehler: BaseException) -> None:
        if id(fehler) in gesehen:
            return
        gesehen.add(id(fehler))
        if fehler.__cause__ is not None:
            anhaengen(fehler.__cause__)
            teile.append(
                "\nThe above exception was the direct cause of the following exception:\n\n"
            )
        elif fehler.__context__ is not None and not fehler.__suppress_context__:
            anhaengen(fehler.__context__)
            teile.append(
                "\nDuring handling of the above exception, another exception occurred:\n\n"
            )
        if fehler.__traceback__ is not None:
            teile.append("Traceback (most recent call last):\n")
            teile.extend(traceback.format_tb(fehler.__traceback__))
        art = type(fehler)
        name = art.__qualname__
        if art.__module__ not in ("builtins", "__main__"):
            name = f"{art.__module__}.{name}"
        teile.append(f"{name} (Meldung nicht protokolliert)\n")
        if isinstance(fehler, BaseExceptionGroup):
            for nummer, teil in enumerate(fehler.exceptions, start=1):
                teile.append(f"\n+---------------- {nummer} ----------------\n")
                anhaengen(teil)

    anhaengen(ausnahme)
    return "".join(teile).rstrip("\n")


class SafeFormatter(logging.Formatter):
    """Logging formatter with emoji safety (Single Responsibility).

    Schreibt Ausnahmen ohne ihre Meldung (ausnahme_ohne_meldung).
    """

    def __init__(self, fmt: str, datefmt: str):
        super().__init__(fmt, datefmt)

    def formatException(self, ei) -> str:
        ausnahme = ei[1]
        if ausnahme is None:
            return super().formatException(ei)
        return ausnahme_ohne_meldung(ausnahme)

    def format(self, record: logging.LogRecord) -> str:
        # Hat ein anderer Handler den Datensatz schon formatiert, steht dessen Text
        # samt Meldung in exc_text und logging.Formatter uebernaehme ihn unbesehen.
        record.exc_text = None
        try:
            return super().format(record)
        except UnicodeEncodeError:
            # Translate emojis and retry
            original_msg = record.getMessage()
            record.msg = EmojiTranslator.translate(original_msg)
            record.args = ()
            return super().format(record)


class ConsoleSetup:
    """Handles console encoding setup (Single Responsibility)."""

    @staticmethod
    def setup_utf8_console() -> bool:
        """Setup UTF-8 console encoding on Windows."""
        if sys.platform != "win32":
            return True

        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
            return True
        except (AttributeError, OSError):
            return False


class LoggerFactory:
    """Factory for creating configured loggers (Factory Pattern)."""

    def __init__(self, config: LoggingConfig):
        self.config = config
        self._setup_complete = False

    def setup(self) -> None:
        """Setup logging system once."""
        if self._setup_complete:
            return

        # Setup console encoding if requested
        if self.config.enable_console_utf8:
            ConsoleSetup.setup_utf8_console()

        # Choose format based on configuration
        if self.config.show_logger_name:
            format_string = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
        else:
            format_string = self.config.format_string

        # Create formatter
        formatter = SafeFormatter(format_string, self.config.date_format)

        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.level.upper(), logging.INFO))

        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Add file handler if specified
        if self.config.file_path:
            file_handler = logging.FileHandler(self.config.file_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        # Configure third-party loggers
        self._configure_third_party_loggers()
        self._format_server_errors(formatter)

        self._setup_complete = True

    def _configure_third_party_loggers(self) -> None:
        """Reduce noise from third-party libraries."""
        noisy_loggers = ["uvicorn.access", "transformers", "torch"]
        for logger_name in noisy_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    @staticmethod
    def _format_server_errors(formatter: logging.Formatter) -> None:
        """uvicorn schreibt eine unbehandelte Ausnahme ("Exception in ASGI
        application") ueber eigene Handler am Logger "uvicorn", die es vor dem Import
        der Anwendung einrichtet; ohne diesen Formatter stuende dort die Meldung."""
        for logger_name in ("uvicorn", "uvicorn.error"):
            for handler in logging.getLogger(logger_name).handlers:
                handler.setFormatter(formatter)

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance."""
        return logging.getLogger(name)


# Global factory instance (controlled injection point)
_logger_factory: Optional[LoggerFactory] = None


def initialize_logging(config: LoggingConfig) -> LoggerFactory:
    """Initialize logging with dependency injection."""
    global _logger_factory
    _logger_factory = LoggerFactory(config)
    _logger_factory.setup()
    return _logger_factory


def get_logger(name: str) -> logging.Logger:
    """Get logger instance (requires initialization)."""
    if _logger_factory is None:
        raise RuntimeError("Logging not initialized. Call initialize_logging() first.")
    return _logger_factory.get_logger(name)


def log_pseudonym(user: str) -> str:
    """
    Kurzes Pseudonym fuer eine Nutzerkennung in Log-Zeilen.

    Fuer die Fehler- und Missbrauchsanalyse muss man wiederkehrende Akteure
    unterscheiden koennen, nicht wissen, wer sie sind. Acht Hex-Zeichen reichen
    dafuer und machen die Zeile fuer sich genommen nicht mehr personenbeziehbar.

    Bewusst kein Ersatz fuer die rotierenden Pseudonyme in SearchTrackingService:
    das hier ist ein ungesalzener Hash, also ueber Zeilen hinweg verkettbar und
    bei bekanntem Kennungsraum zurueckrechenbar. Fuer eine fluechtige Logzeile
    ist das der richtige Kompromiss, fuer gespeicherte Daten nicht.

    Das BFF rechnet dasselbe (BFF/Logging/LogPseudonym.cs); wer eines der beiden
    aendert, aendert das andere mit, sonst passen die Zeilen nicht mehr zusammen.
    """
    if not user or user == "anonymous":
        return "anonymous"
    return hashlib.sha256(user.encode("utf-8")).hexdigest()[:8]
