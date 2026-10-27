-- search_events: zufaellige Kennung statt fortlaufender Nummer (#275)
--
-- Die Kennung kam aus einer Sequenz und gab damit die Reihenfolge der Suchen
-- eines Tages wieder. Eine Suche kann eine neue Aussage anlegen, deren
-- Anlagezeitpunkt sekundengenau in Qdrant steht; an ruhigen Tagen passte die
-- Reihenfolge der Suchereignisse zu der der neuen Aussagen und ordnete jeder
-- Aussage ein Tagespseudonym zu. Ab jetzt ist die Kennung eine zufaellige UUID,
-- die Sequenz entfaellt mit der alten Spalte.
--
-- Neue Datenbanken brauchen das Skript nicht: create_all legt die Tabelle mit der
-- UUID an (infrastructure/database/models.py, SearchEvent). Bestehende brauchen
-- es vor dem Start des neuen Dienstes: Er liest die Kennung nicht und schreibt sie
-- nicht selbst, mit dem alten Schema liefe er also weiter, vergaebe aber weiter
-- fortlaufende Nummern.
--
-- Vorhandene Suchereignisse bleiben erhalten und bekommen eine zufaellige
-- Kennung; die alten Nummern verwirft das Skript. Das Hinzufuegen der Spalte mit
-- zufaelligem Default schreibt die Tabelle neu, und dabei setzt PostgreSQL die
-- eben geloeschte Spalte auf NULL: Die alten Nummern stehen danach nicht mehr in
-- der Tabellendatei, ein VACUUM FULL ist nicht noetig.
--
-- Wiederholbar: Ein zweiter Lauf wuerfelt die Kennungen neu, sonst aendert sich
-- nichts. Kein Schreiber oder Leser haengt an ihnen.
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

ALTER TABLE search_events DROP COLUMN IF EXISTS id;

ALTER TABLE search_events
    ADD COLUMN id UUID NOT NULL DEFAULT gen_random_uuid();

ALTER TABLE search_events ADD CONSTRAINT search_events_pkey PRIMARY KEY (id);

COMMIT;
