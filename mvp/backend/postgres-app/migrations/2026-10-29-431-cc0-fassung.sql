-- Kennung des CC0-Hinweises an Einwurf und Satz (#431)
--
-- Jedes Formular, das etwas fuer andere sichtbar speichert, zeigt den CC0-Hinweis
-- und schickt die Kennung des gezeigten Wortlauts mit (domain/cc0_hinweis.py im
-- Semantic-Service, Wortlaute in docs/CC0_HINWEIS_WORTLAUTE.md). So bleibt
-- nachvollziehbar, welchem Wortlaut jemand zugestimmt hat. Beitraege liegen in
-- Qdrant und tragen die Kennung dort im Payload; hier bekommen die beiden Tabellen
-- in PostgreSQL je eine Spalte: raw_inputs (Einwurf) und raw_input_drafts (Satz,
-- bei jedem Speichern ueberschrieben).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabellen mit
-- der Spalte an. Bestehende brauchen es, weil create_all keine Spalten ergaenzt.
--
-- Vorhandene Zeilen behalten NULL: Welchem Wortlaut sie zugestimmt haben, laesst
-- sich nicht mehr feststellen.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

ALTER TABLE raw_inputs ADD COLUMN IF NOT EXISTS cc0_wortlaut VARCHAR(64);
ALTER TABLE raw_input_drafts ADD COLUMN IF NOT EXISTS cc0_wortlaut VARCHAR(64);

COMMIT;
