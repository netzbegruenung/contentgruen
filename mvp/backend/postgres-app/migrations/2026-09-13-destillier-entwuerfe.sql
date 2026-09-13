-- Destillier-Ablauf: Entwurfssaetze je Einwurf und Person
--
-- Beim Destillieren formuliert man zuerst in einem Satz, was der Punkt eines
-- Einwurfs ist. Dieser Satz wird serverseitig zwischengespeichert, weil der
-- Ablauf am Handy unterbrechbar sein muss. Er gehoert zu (Einwurf, Person) und
-- nicht zum Einwurf allein: es gibt keine Sperre, mehrere Leute duerfen denselben
-- Einwurf gleichzeitig destillieren.
--
-- raw_input_content_links bleibt unveraendert: created_by/created_at halten fest,
-- wer wann verarbeitet hat (in der API: processed_by/processed_at).
--
-- Neue Datenbanken brauchen dieses Skript nicht: die Tabelle wird beim Start
-- von SQLAlchemy angelegt (infrastructure/database/connection.py:48), und
-- create_all legt fehlende Tabellen auch in bestehenden Datenbanken an. Das
-- Skript dokumentiert das Schema und dient Umgebungen, in denen die Tabelle vor
-- dem ersten Start des neuen Dienstes existieren soll.
--
-- Anwenden:
--   docker exec -i contentgruen-app-postgres psql -U app_user -d contentgruen_app \
--     < mvp/backend/postgres-app/migrations/2026-09-13-destillier-entwuerfe.sql

BEGIN;

CREATE TABLE IF NOT EXISTS raw_input_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_input_id UUID NOT NULL REFERENCES raw_inputs(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    sentence TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_raw_input_drafts_user_id
    ON raw_input_drafts(user_id);
-- Genau ein Entwurf je Person und Einwurf. Der Upsert (ON CONFLICT) haengt daran.
CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_input_drafts_unique
    ON raw_input_drafts(raw_input_id, user_id);

COMMIT;
