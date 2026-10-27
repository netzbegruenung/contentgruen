-- Feedback an das Team (#343)
--
-- Der Knopf "Feedback" im Kopf der App speichert einen Freitext und optional eine
-- Kontaktangabe; Admins lesen beides im Admin-Dashboard. Die Zeile traegt keine
-- Kennung und keine Sitzung und statt eines Zeitpunkts nur den Tag. Nach 180
-- Tagen loescht der taegliche Aufraeumlauf des Dienstes die Zeile ganz
-- (services/feedback_service.py, docs/LOESCHKONZEPT.md).
--
-- Neue Datenbanken brauchen dieses Skript nicht: die Tabelle wird beim Start
-- von SQLAlchemy angelegt (infrastructure/database/connection.py), und
-- create_all legt fehlende Tabellen auch in bestehenden Datenbanken an, vor dem
-- Einspielen der Migrationen beim Start. Das Skript dokumentiert das Schema und
-- laeuft dann ohne Wirkung durch. Vorhandene Daten gibt es keine.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS feedback (
    id UUID NOT NULL,
    text TEXT NOT NULL,
    kontakt TEXT,
    eingegangen_am DATE NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_feedback_eingegangen_am ON feedback(eingegangen_am);

COMMIT;
