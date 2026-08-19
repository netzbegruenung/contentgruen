-- search_events: personenbeziehbare Spalten entfernen
--
-- Bis hierher speicherte jedes Suchereignis den Suchtext im Volltext sowie
-- user_id, session_id und ip_hash. query_text und ip_hash wurden geschrieben,
-- aber von keiner einzigen Abfrage gelesen. user_id und session_id trugen die
-- Kennzahlen "Daily Active Users" und "Searches per User"; beide laufen jetzt
-- ueber actor_hash, ein taeglich rotierendes Pseudonym (HMAC-SHA256 ueber
-- Nutzer-/Session-Kennung + UTC-Datum, verschluesselt mit
-- SEMANTIC_SEARCH_ACTOR_HASH_SECRET).
--
-- Neue Datenbanken brauchen dieses Skript nicht: die Tabelle wird beim Start
-- von SQLAlchemy angelegt (infrastructure/database/connection.py:48) und hat
-- dann direkt das neue Schema. Nur bereits laufende Umgebungen migrieren.
--
-- Anwenden:
--   docker exec -i contentgruen-app-postgres psql -U app_user -d contentgruen_app \
--     < mvp/backend/postgres-app/migrations/2026-08-19-search-events-pseudonymisieren.sql

BEGIN;

-- Bestandsdaten verwerfen. DROP COLUMN markiert die Spalte in PostgreSQL nur als
-- geloescht; die alten Werte blieben bis zu einem Table-Rewrite physisch auf der
-- Platte stehen. Da es noch keine Nutzer gibt, ist die Historie wertlos, und ein
-- leerer Table ist die einzige Variante ohne Datenreste.
TRUNCATE TABLE search_events;

DROP INDEX IF EXISTS idx_search_events_user_id;
DROP INDEX IF EXISTS idx_search_events_session_id;

ALTER TABLE search_events DROP COLUMN IF EXISTS query_text;
ALTER TABLE search_events DROP COLUMN IF EXISTS ip_hash;
ALTER TABLE search_events DROP COLUMN IF EXISTS user_id;
ALTER TABLE search_events DROP COLUMN IF EXISTS session_id;

ALTER TABLE search_events ADD COLUMN IF NOT EXISTS actor_hash VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_search_events_actor_hash ON search_events(actor_hash);

COMMIT;

-- Ausserhalb der Transaktion: Speicher der geloeschten Spalten zurueckgeben.
VACUUM FULL search_events;
