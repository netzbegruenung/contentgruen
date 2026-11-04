-- Feedback als erledigt markieren (#425)
--
-- Admins markieren Feedback im Admin-Dashboard als erledigt und nehmen das
-- zurueck; die Liste filtert nach offen und erledigt. Die Spalte ist nur ein
-- Merker, ohne Zeitpunkt und ohne wer. Die Frist von 180 Tagen gilt unveraendert
-- fuer offenes wie erledigtes Feedback (docs/LOESCHKONZEPT.md).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle
-- mit der Spalte an (infrastructure/database/connection.py), und das Skript
-- laeuft dann ohne Wirkung durch. Bestehende Datenbanken brauchen es, denn
-- create_all ergaenzt keine Spalten. Vorhandenes Feedback gilt als offen.
-- Wiederholbar.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

ALTER TABLE feedback ADD COLUMN IF NOT EXISTS erledigt BOOLEAN NOT NULL DEFAULT false;

COMMIT;
