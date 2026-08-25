-- usage_events: personenbeziehbare Spalten entfernen
--
-- Drei Spalten fallen weg, keine davon wurde je von einer Abfrage gelesen
-- (gesucht mit grep ueber api/, services/, repositories/ nach den Spaltennamen,
-- jeder Treffer bis zum Aufrufer verfolgt):
--
--   user_id     kam ueber den regulaeren Weg Frontend -> BFF -> Backend nie an.
--               Die Dependency get_current_user_optional las den Header
--               X-User-Id, das BFF setzt X-User. Die Spalte blieb leer.
--   ip_hash     war ein ungesalzener SHA-256 ueber die IP-Adresse, sogar zweimal
--               angewandt. Ueber den IPv4-Raum ist so ein Hash durchrechenbar,
--               die Spalte also nicht anonym.
--   user_agent  stand als Rohwert mit bis zu 500 Zeichen darin. An seine Stelle
--               tritt device_category mit "mobile", "tablet", "desktop" oder
--               "unknown", abgeleitet in app/utils/device_category.py.
--
-- Die View user_usage_statistics gruppierte nach user_id und faellt deshalb
-- mit. Anwendungscode hat sie nie benutzt: die Nutzerstatistik hinter
-- /api/v1/usage/users/{id}/usage-stats liest Qdrant (original_author) und
-- usage_tracking, nicht diese View.
--
-- Bestandswerte von user_agent werden verworfen statt nachtraeglich in
-- Kategorien umgerechnet. Sie umzurechnen hiesse, den Rohwert noch einmal zu
-- verarbeiten -- genau das, was diese Aenderung abstellt.
--
-- Neue Datenbanken brauchen dieses Skript nicht: die Tabelle wird beim Start
-- von SQLAlchemy angelegt (infrastructure/database/connection.py:48) bzw. bei
-- leerem Volume aus init.sql, und hat dann direkt das neue Schema. Nur bereits
-- laufende Umgebungen migrieren.
--
-- Anwenden:
--   docker exec -i contentgruen-app-postgres psql -U app_user -d contentgruen_app \
--     < mvp/backend/postgres-app/migrations/2026-08-25-usage-events-datensparsamkeit.sql

BEGIN;

DROP VIEW IF EXISTS user_usage_statistics;

DROP INDEX IF EXISTS idx_usage_events_user_id;

ALTER TABLE usage_events DROP COLUMN IF EXISTS user_id;
ALTER TABLE usage_events DROP COLUMN IF EXISTS ip_hash;

-- Umbenennen statt neu anlegen, damit die Spaltenreihenfolge erhalten bleibt.
-- Der USING-Ausdruck verwirft die Rohwerte; ohne ihn scheiterte die
-- Typaenderung an User-Agent-Strings, die laenger als 20 Zeichen sind.
ALTER TABLE usage_events RENAME COLUMN user_agent TO device_category;
ALTER TABLE usage_events
    ALTER COLUMN device_category TYPE VARCHAR(20) USING NULL;

COMMIT;

-- Ausserhalb der Transaktion: Speicher der geloeschten Spalten zurueckgeben.
-- DROP COLUMN markiert in PostgreSQL nur; die alten Nutzerkennungen, IP-Hashes
-- und User-Agent-Strings blieben bis zu einem Table-Rewrite physisch auf der
-- Platte stehen.
VACUUM FULL usage_events;
