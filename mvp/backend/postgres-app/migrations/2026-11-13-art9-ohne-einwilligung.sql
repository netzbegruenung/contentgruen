-- "Ohne Einwilligung weiter" am Konto (UX-Review B2, PR #670)
--
-- Je Kennung hoechstens eine Zeile: zu welchem Wortlaut der Art.-9-Einwilligung
-- (mvp/backend/semantic-search-service/app/domain/art9_einwilligung.py) die Person
-- bewusst ohne Einwilligung weitergegangen ist, und wann. Eine Einwilligung loescht
-- die Zeile; geloescht wird sie auch mit dem Konto (docs/LOESCHKONZEPT.md, Schritt 2).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle beim
-- Start an, auch in bestehenden Datenbanken, vor dem Einspielen der Migrationen.
-- Das Skript dokumentiert das Schema und laeuft dann ohne Wirkung durch.
-- Vorhandene Daten gibt es keine.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS art9_ohne_einwilligung (
    user_id VARCHAR(255) NOT NULL,
    wortlaut VARCHAR(64) NOT NULL,
    entschieden_am TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (user_id)
);

COMMIT;
