-- Suchen ohne Treffer: Mindestanzahl zaehlt Personen statt Suchen (#243)
--
-- Neben der Zahl der Suchen zaehlt die Tabelle jetzt, wie viele verschiedene
-- Personen (Tagespseudonyme) je Aussage und Woche ohne Treffer gesucht haben.
-- Admins sehen eine Aussage erst ab zwei Personen. Die Pseudonyme selbst
-- landen nicht in der Tabelle; welche Person eine Aussage heute schon gezaehlt
-- hat, haelt der Dienst nur im Speicher (services/suchen_ohne_treffer_service.py).
--
-- Bestehende Zeilen bekommen personen = 0: Wer dort gesucht hat, laesst sich
-- nicht mehr feststellen. Die Aussagen erscheinen wieder, sobald neue Suchen
-- die Schwelle erreichen; alte Wochen fallen ohnehin nach acht Wochen weg.
--
-- Anders als die Tabelle selbst legt SQLAlchemy die Spalte in bestehenden
-- Datenbanken NICHT an (create_all ergaenzt keine Spalten). Das Skript muss
-- daher vor dem Start des neuen Dienstes laufen, sonst scheitert das Zaehlen.
--
-- Anwenden:
--   docker exec -i gutgesagt-app-postgres psql -U app_user -d gutgesagt_app \
--     < mvp/backend/postgres-app/migrations/2026-10-26-suchen-ohne-treffer-personen.sql

BEGIN;

ALTER TABLE suchen_ohne_treffer
    ADD COLUMN IF NOT EXISTS personen INTEGER NOT NULL DEFAULT 0;

COMMIT;
