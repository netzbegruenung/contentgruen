-- Zustimmung zur Sichtbarkeit der Meilenstein-Abzeichen (#351)
--
-- Je Antwort eine Zeile: ob andere Angemeldete die Abzeichen der Person an ihrem
-- Anzeigenamen sehen (zeigen), die Kennung der Frage
-- (mvp/backend/semantic-search-service/app/domain/abzeichen_sichtbarkeit.py) und wann
-- sie geantwortet hat. Es gilt die juengste Zeile einer Kennung; jede Aenderung ist
-- eine neue Zeile. Geloescht werden alle mit dem Konto (docs/LOESCHKONZEPT.md,
-- Schritt 2).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle beim
-- Start an, auch in bestehenden Datenbanken, vor dem Einspielen der Migrationen.
-- Das Skript dokumentiert das Schema und laeuft dann ohne Wirkung durch.
-- Vorhandene Daten gibt es keine.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS abzeichen_sichtbarkeit (
    id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    zeigen BOOLEAN NOT NULL,
    wortlaut VARCHAR(64) NOT NULL,
    beantwortet_am TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_abzeichen_sichtbarkeit_user
    ON abzeichen_sichtbarkeit (user_id, beantwortet_am);

COMMIT;
