-- search_events: nur noch den Tag speichern, keine Uhrzeit
--
-- Eine Suche kann eine neue Aussage anlegen (Herkunft SEARCH_QUERY), deren
-- Anlagezeitpunkt in Qdrant sekundengenau steht. Ein ebenso genauer Zeitpunkt am
-- Suchereignis liess sich damit verbinden und ordnete die Aussage dem
-- Tagespseudonym (actor_hash) der suchenden Person zu. Ab jetzt traegt jedes
-- Suchereignis nur Mitternacht UTC seines Tages. Alle Auswertungen zaehlen ohnehin
-- ganze Tage (Daily Active Users, Searches per User).
--
-- Der Dienst setzt den Tag selbst (repositories/search_tracking_repository.py);
-- der Default unten gilt fuer jeden anderen Schreiber. Neue Datenbanken bekommen
-- ihn von SQLAlchemy (infrastructure/database/models.py, SearchEvent).
--
-- Anwenden (wiederholbar):
--   docker exec -i gutgesagt-app-postgres psql -U app_user -d gutgesagt_app -v ON_ERROR_STOP=1 \
--     < mvp/backend/postgres-app/migrations/2026-10-26-search-events-nur-tag.sql
--
-- Danach, ausserhalb einer Transaktion: UPDATE schreibt in PostgreSQL neue
-- Zeilenversionen, die alten Uhrzeiten bleiben bis zu einem Table-Rewrite auf der
-- Platte stehen.
--   docker exec -i gutgesagt-app-postgres psql -U app_user -d gutgesagt_app \
--     -c 'VACUUM FULL search_events;'

BEGIN;

ALTER TABLE search_events
    ALTER COLUMN timestamp
    SET DEFAULT (date_trunc('day', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC');

UPDATE search_events
SET timestamp = date_trunc('day', timestamp AT TIME ZONE 'UTC') AT TIME ZONE 'UTC'
WHERE timestamp <> date_trunc('day', timestamp AT TIME ZONE 'UTC') AT TIME ZONE 'UTC';

COMMIT;
