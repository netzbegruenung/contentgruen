-- search_events: Bestand abgeschlossener Tage einmal gemischt neu schreiben (#337)
--
-- Jede Suche schreibt ihr Suchereignis in einer eigenen Transaktion. Die
-- Systemspalte xmin und die physische Lage der Zeilen (ctid, Reihenfolge in
-- pg_dump) ergeben damit die Reihenfolge der Suchen eines Tages. Ab jetzt
-- schreibt der taegliche Bereinigungsjob jeden abgeschlossenen Tag, dessen
-- Zeilen mehr als eine Transaktion tragen, in zufaelliger Reihenfolge und in
-- einer Transaktion neu (SearchTrackingRepository.mische_abgeschlossene_tage).
--
-- Zeilen, die schon vor 2026-10-27-suchereignisse-reihenfolge.sql da waren,
-- erkennt der Job nicht: Das Neuschreiben der Tabelle dort gab ihnen allen
-- dieselbe Transaktion, ihre physische Reihenfolge blieb aber die des
-- Einfuegens. Dieses Skript mischt deshalb einmal alle abgeschlossenen Tage.
--
-- Neue Datenbanken brauchen das Skript nicht, es findet dort keine Zeilen.
-- Vorhandene Suchereignisse bleiben mit allen Werten erhalten; nur ihre
-- Transaktion und ihre Lage in der Tabellendatei aendern sich. Die alten
-- Zeilenversionen stehen physisch weiter in der Datei, bis ein VACUUM ihren
-- Platz freigibt; lesbar sind sie bis dahin nur mit Werkzeugen, die Seiten
-- roh auslesen. Der laufende Tag bleibt, ihn mischt der Job am Folgetag.
--
-- Wiederholbar: Ein zweiter Lauf mischt dieselben Zeilen noch einmal, sonst
-- aendert sich nichts.
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

WITH weg AS (
    DELETE FROM search_events
    WHERE timestamp < (date_trunc('day', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC')
    RETURNING id, actor_hash, results_count, timestamp
)
INSERT INTO search_events (id, actor_hash, results_count, timestamp)
SELECT id, actor_hash, results_count, timestamp
FROM weg
ORDER BY random();

COMMIT;
