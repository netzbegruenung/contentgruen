-- search_events: nur noch den Tag speichern, keine Uhrzeit
--
-- Eine Suche kann eine neue Aussage anlegen (Herkunft SEARCH_QUERY), deren
-- Anlagezeitpunkt in Qdrant sekundengenau steht. Ein ebenso genauer Zeitpunkt am
-- Suchereignis liess sich damit verbinden und ordnete die Aussage dem
-- Tagespseudonym (actor_hash) der suchenden Person zu. Ab jetzt traegt jedes
-- Suchereignis nur Mitternacht UTC seines Tages. Alle Auswertungen zaehlen ohnehin
-- ganze Tage (Daily Active Users, Searches per User).
--
-- Neue Datenbanken brauchen das Skript nicht: SQLAlchemy legt die Tabelle mit
-- demselben Default an (infrastructure/database/models.py, SearchEvent). Der
-- neue Dienst setzt den Tag ohnehin selbst
-- (repositories/search_tracking_repository.py); das Skript muss also nicht vor
-- seinem Start laufen. Es setzt den Default fuer jeden anderen Schreiber und
-- schneidet die Uhrzeit vom Altbestand ab.
--
-- Wiederholbar. Das VACUUM FULL steht nach dem COMMIT, weil es nicht in einer
-- Transaktion laufen darf: UPDATE schreibt in PostgreSQL neue Zeilenversionen,
-- die alten Uhrzeiten blieben bis zu einem Table-Rewrite auf der Platte stehen.
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

ALTER TABLE search_events
    ALTER COLUMN timestamp
    SET DEFAULT (date_trunc('day', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC');

UPDATE search_events
SET timestamp = date_trunc('day', timestamp AT TIME ZONE 'UTC') AT TIME ZONE 'UTC'
WHERE timestamp <> date_trunc('day', timestamp AT TIME ZONE 'UTC') AT TIME ZONE 'UTC';

COMMIT;

VACUUM FULL search_events;
