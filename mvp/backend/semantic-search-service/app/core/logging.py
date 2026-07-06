"""
Optimized logging configuration following clean code principles.

Separates concerns, uses dependency injection, and maintains testability.
"""

import logging
import sys
import io
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


class SafeFormatter(logging.Formatter):
    """Logging formatter with emoji safety (Single Responsibility)."""

    def __init__(self, fmt: str, datefmt: str):
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
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

        self._setup_complete = True

    def _configure_third_party_loggers(self) -> None:
        """Reduce noise from third-party libraries."""
        noisy_loggers = ["uvicorn.access", "transformers", "torch"]
        for logger_name in noisy_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

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
