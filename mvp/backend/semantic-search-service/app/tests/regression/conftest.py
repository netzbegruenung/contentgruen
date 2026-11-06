"""
Nach einem Lauf von test_aehnlichkeit_messset.py die Auswertung je Paar-Label ins Log,
wie `python -m tests.regression.aehnlichkeit_messen` sie ausgibt: Im naechtlichen Lauf
(#391) steht die Tabelle dann neben den roten Tests, ohne das Modell ein zweites Mal zu
laden. Ohne berechnete Scores (Test abgewaehlt) gibt es keine Tabelle.
"""


def pytest_terminal_summary(terminalreporter):
    from core.config import Settings
    from tests.regression.aehnlichkeit_messen import (
        auswertung,
        messungen_jetzt,
        scores,
    )

    if not scores.cache_info().currsize:
        return
    settings = Settings()
    terminalreporter.section("Messset je Paar-Label")
    terminalreporter.write_line(auswertung(messungen_jetzt(settings), settings))
