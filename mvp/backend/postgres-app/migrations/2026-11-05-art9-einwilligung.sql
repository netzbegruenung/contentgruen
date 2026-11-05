-- Art.-9-Einwilligung (#489)
--
-- Je Einwilligung eine Zeile: wann die Person eingewilligt hat, die Kennung des
-- Wortlauts (mvp/backend/semantic-search-service/app/domain/art9_einwilligung.py)
-- und wann sie widerrufen hat. Es gilt die juengste Zeile einer Kennung; eine
-- erneute Einwilligung ist eine neue Zeile. Geloescht werden alle mit dem Konto
-- (docs/LOESCHKONZEPT.md, Schritt 2).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle beim
-- Start an, auch in bestehenden Datenbanken, vor dem Einspielen der Migrationen.
-- Das Skript dokumentiert das Schema und laeuft dann ohne Wirkung durch.
-- Vorhandene Daten gibt es keine.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS art9_einwilligungen (
    id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    wortlaut VARCHAR(64) NOT NULL,
    eingewilligt_am TIMESTAMP WITH TIME ZONE NOT NULL,
    widerrufen_am TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_art9_einwilligungen_user
    ON art9_einwilligungen (user_id, eingewilligt_am);

COMMIT;
