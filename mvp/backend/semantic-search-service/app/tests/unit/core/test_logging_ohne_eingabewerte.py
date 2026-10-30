"""
Keine Eingabewerte in Fehlerzeilen (#422).

Die Meldung einer Ausnahme traegt oft, was hereinkam: eine Validierungsmeldung den
abgelehnten Wert, ein Datenbankfehler die Parameter der Abfrage. Die Fehlerzeile
nennt deshalb Typ und Stelle der Ausnahme, nicht ihre Meldung.
"""

import logging
import logging.config

import pytest
from uvicorn.config import LOGGING_CONFIG

from core.logging import LoggingConfig, initialize_logging

EINGABE = "Waermepumpe-im-Altbau-422"


def _ausgeloest(ausnahme: BaseException) -> BaseException:
    try:
        raise ausnahme
    except BaseException as gefangen:  # noqa: BLE001 - genau diese Ausnahme zurueck
        return gefangen


@pytest.fixture
def protokoll(capsys):
    """Die Protokollierung wie im Dienst einrichten; liefert die Ausgabe auf stdout
    und stderr. Raeumt die Handler danach wieder ab."""
    vorher = {
        name: (
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).propagate,
        )
        for name in ("", "uvicorn", "uvicorn.error", "uvicorn.access")
    }
    root_level = logging.getLogger().level

    def ausgabe() -> str:
        for handler in logging.getLogger().handlers:
            handler.flush()
        gelesen = capsys.readouterr()
        return gelesen.out + gelesen.err

    yield ausgabe

    for name, (handler, propagate) in vorher.items():
        logger = logging.getLogger(name)
        logger.handlers[:] = handler
        logger.propagate = propagate
    logging.getLogger().setLevel(root_level)


class TestFehlerzeileMitAusnahme:
    def test_nennt_typ_und_stelle_aber_nicht_die_meldung(self, protokoll):
        initialize_logging(LoggingConfig(level="INFO", enable_console_utf8=False))
        fehler = _ausgeloest(ValueError(f"ungueltiger Wert: {EINGABE}"))

        logging.getLogger("services.beispiel").error(
            "Speichern fehlgeschlagen", exc_info=fehler
        )

        text = protokoll()
        assert "Speichern fehlgeschlagen" in text
        assert "ValueError" in text
        assert "_ausgeloest" in text  # die Stelle, an der es passiert ist
        assert EINGABE not in text

    def test_auch_nicht_die_meldung_einer_verketteten_ausnahme(self, protokoll):
        initialize_logging(LoggingConfig(level="INFO", enable_console_utf8=False))
        try:
            try:
                raise KeyError(EINGABE)
            except KeyError as innen:
                raise RuntimeError(f"Folgefehler zu {EINGABE}") from innen
        except RuntimeError as aussen:
            fehler = aussen

        logging.getLogger("services.beispiel").error("Fehlgeschlagen", exc_info=fehler)

        text = protokoll()
        assert "KeyError" in text
        assert "RuntimeError" in text
        assert EINGABE not in text

    def test_unbehandelte_ausnahme_im_server_ohne_meldung(self, protokoll):
        """uvicorn schreibt eine unbehandelte Ausnahme ("Exception in ASGI
        application") mit eigenen Handlern; uvicorn richtet sie ein, bevor es die
        Anwendung importiert."""
        logging.config.dictConfig(LOGGING_CONFIG)
        initialize_logging(LoggingConfig(level="INFO", enable_console_utf8=False))
        fehler = _ausgeloest(ValueError(EINGABE))

        logging.getLogger("uvicorn.error").error(
            "Exception in ASGI application", exc_info=fehler
        )

        text = protokoll()
        assert "Exception in ASGI application" in text
        assert "ValueError" in text
        assert EINGABE not in text

    def test_ausnahmegruppe_nennt_die_typen_ihrer_ausnahmen(self, protokoll):
        initialize_logging(LoggingConfig(level="INFO", enable_console_utf8=False))
        fehler = _ausgeloest(
            ExceptionGroup(
                f"Gruppe {EINGABE}",
                [_ausgeloest(KeyError(EINGABE)), _ausgeloest(TimeoutError(EINGABE))],
            )
        )

        logging.getLogger("services.beispiel").error("Fehlgeschlagen", exc_info=fehler)

        text = protokoll()
        assert "ExceptionGroup" in text
        assert "KeyError" in text
        assert "TimeoutError" in text
        assert EINGABE not in text
