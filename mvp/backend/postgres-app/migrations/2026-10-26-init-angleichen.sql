-- usage_tracking, usage_events: Schema aus init.sql an das Modell angleichen
--
-- Test- und Produktionsdatenbanken entstanden aus init.sql, das bis #285 vom
-- Modell (infrastructure/database/models.py) abwich, gegen das Code und Tests
-- pruefen. Es gilt das Modell, nur die Server-Defaults kommen aus init.sql:
--
-- - usage_events.id wird BIGINT wie im Modell, samt Sequenz. Das schreibt die
--   Tabelle samt Indizes neu; sie haelt nur die Nutzungen der letzten Tage
--   (standardmaessig 90, usage_retention_days).
-- - idx_usage_events_timestamp aufsteigend statt absteigend. Fuer einen Index auf
--   einer Spalte ist die Richtung gleichwertig, beide Abfragen filtern nur nach
--   Bereich (Trending, Aufraeumen). Das Skript baut ihn bei jedem Lauf neu.
-- - idx_usage_events_content_timestamp und idx_usage_tracking_usage_count
--   entfallen: Keine Abfrage sortiert nach diesen Spalten oder filtert nach
--   content_id und Zeit zugleich. idx_usage_tracking_last_used entfaellt auch;
--   die Kennzahlen filtern zwar nach einem Bereich von last_used, aber
--   usage_tracking hat nur eine Zeile je Beitrag, dafuer reicht ein Scan.
-- - Der Trigger update_usage_tracking_updated_at und seine Funktion
--   update_updated_at_column entfallen: updated_at setzt das Modell (onupdate),
--   alle Aenderungen an usage_tracking laufen ueber das ORM.
-- - Die Server-Defaults von usage_events.event_type ('copy') und
--   usage_tracking.usage_count (0) stehen jetzt auch im Modell; das Skript setzt
--   sie fuer Datenbanken, die create_all ohne init.sql angelegt hat.
--
-- Sperren: Das Skript sperrt beide Tabellen gleich zu Beginn und bis zum Ende
-- exklusiv, auch fuer Lesezugriffe (Nutzungszahlen in der Suche, Kennzahlen,
-- Kopier-Zaehlungen warten). Bekommt es die Sperre nicht binnen 5 Sekunden,
-- bricht es ohne Aenderung ab; dann spaeter erneut starten.
--
-- Neue Datenbanken brauchen das Skript nicht: init.sql und create_all legen das
-- Schema schon so an. Es muss nicht vor dem Start des neuen Dienstes laufen; der
-- Code liest und schreibt beide Tabellen davor und danach gleich. Daten aendern
-- sich nicht. Wiederholbar; nach dem Einspielen einer Sicherung von vor dem
-- Skript erneut anwenden.
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

SET LOCAL lock_timeout = '5s';
LOCK TABLE usage_tracking, usage_events IN ACCESS EXCLUSIVE MODE;

ALTER TABLE usage_events ALTER COLUMN id TYPE BIGINT;
ALTER SEQUENCE usage_events_id_seq AS BIGINT;

DROP TRIGGER IF EXISTS update_usage_tracking_updated_at ON usage_tracking;
DROP FUNCTION IF EXISTS update_updated_at_column();

DROP INDEX IF EXISTS idx_usage_events_content_timestamp;
DROP INDEX IF EXISTS idx_usage_tracking_usage_count;
DROP INDEX IF EXISTS idx_usage_tracking_last_used;

DROP INDEX IF EXISTS idx_usage_events_timestamp;
CREATE INDEX idx_usage_events_timestamp ON usage_events (timestamp);

ALTER TABLE usage_events ALTER COLUMN event_type SET DEFAULT 'copy';
ALTER TABLE usage_tracking ALTER COLUMN usage_count SET DEFAULT 0;

COMMIT;
