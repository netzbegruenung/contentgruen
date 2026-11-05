-- Varianten: die Verknuepfung "beruht auf" (#356)
--
-- "Als Vorlage nehmen" legt einen neuen Beitrag mit eigenem Autor an, der auf dem
-- Original beruht (GLOSSARY.md, "Variante"). Je Variante eine Zeile mit ihrer ID
-- und der des Originals; keine Kennung, kein Zeitpunkt.
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle beim
-- Start an, auch in bestehenden Datenbanken, vor dem Einspielen der Migrationen.
-- Das Skript dokumentiert das Schema und laeuft dann ohne Wirkung durch.
-- Vorhandene Daten gibt es keine.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS varianten (
    variante_id UUID NOT NULL,
    original_id UUID NOT NULL,
    PRIMARY KEY (variante_id)
);

CREATE INDEX IF NOT EXISTS idx_varianten_original_id ON varianten (original_id);

COMMIT;
