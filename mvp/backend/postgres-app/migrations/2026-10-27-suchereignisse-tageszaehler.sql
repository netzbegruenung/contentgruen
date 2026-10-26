-- Suchereignisse: Tageszaehler nach Ablauf der Frist (#289)
--
-- Suchereignisse bleiben 90 Tage als Einzelzeilen mit Tagespseudonym
-- (Einstellung SEMANTIC_SEARCH_SEARCH_EVENT_RETENTION_DAYS). Aeltere Tage
-- verdichtet der taegliche Bereinigungsjob des Dienstes zu einer Zeile je Tag:
-- Zahl der Suchen und Zahl der Personen (verschiedene Tagespseudonyme), ohne
-- Pseudonym. Die Einzelzeilen loescht er dabei.
--
-- Neue Datenbanken brauchen dieses Skript nicht: die Tabelle wird beim Start
-- von SQLAlchemy angelegt (infrastructure/database/connection.py), und
-- create_all legt fehlende Tabellen auch in bestehenden Datenbanken an. Das
-- Skript dokumentiert das Schema und dient Umgebungen, in denen die Tabelle vor
-- dem ersten Start des neuen Dienstes existieren soll.
--
-- Vorhandene Daten: nichts nachzutragen. Suchereignisse, die schon aelter als
-- die Frist sind, verdichtet der erste Lauf des Jobs beim Start des Dienstes.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS suchen_je_tag (
    tag DATE NOT NULL,
    suchen INTEGER NOT NULL,
    personen INTEGER NOT NULL,
    PRIMARY KEY (tag)
);

COMMIT;
