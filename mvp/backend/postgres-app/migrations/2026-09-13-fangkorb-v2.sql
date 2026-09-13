-- Fangkorb v2: drei Stufen (Einwerfen -> Destillieren -> Ausformulieren)
--
-- raw_inputs.destilled_by haelt fest, wer als Erste/r einen Satz zu einem
-- Einwurf gespeichert hat. Der erste Satz setzt zugleich den Status von open auf
-- in_progress ("Destilliert"); wird der letzte Satz wieder geloescht, faellt der
-- Einwurf auf open zurueck. Beides erledigt der Dienst beim Speichern des Satzes.
--
-- raw_input_content_links bekommt zwei Spalten:
--   draft_id      welcher Satz ausformuliert wurde. ON DELETE SET NULL, weil ein
--                 geleerter Satz seine Zeile loescht - die Verknuepfung mit dem
--                 Beitrag muss das ueberleben.
--   content_type  Typ des entstandenen Beitrags (ContentType-Wert, etwa
--                 "commentary" oder "generic_text"). Die Fangkorb-Karte nimmt
--                 dessen Farbe an. content_id zeigt auf Qdrant und verraet den Typ
--                 nicht.
--
-- WICHTIG: Anders als bei 2026-09-13-destillier-entwuerfe.sql legt SQLAlchemy
-- diese Spalten in bestehenden Datenbanken NICHT an (create_all legt nur fehlende
-- Tabellen an, keine fehlenden Spalten). Das Skript muss vor dem Start des neuen
-- Dienstes laufen, sonst scheitert jeder Fangkorb-Aufruf. Neue Datenbanken
-- brauchen es nicht. Es ist idempotent und darf mehrfach laufen.
--
-- Nachtrag fuer vorhandene Daten, nach bestem Wissen:
--   - destilled_by: die Person mit dem am fruehesten zuletzt geaenderten Satz.
--     Wer wirklich zuerst gespeichert hat, ist nicht mehr feststellbar
--     (raw_input_drafts kennt nur updated_at).
--   - offene Einwuerfe mit mindestens einem Satz werden in_progress.
--   - draft_id: der Satz der Person, die verknuepft hat, falls es ihn noch gibt.
--   - content_type bleibt fuer alte Verknuepfungen NULL.
--
-- Anwenden:
--   docker exec -i contentgruen-app-postgres psql -U app_user -d contentgruen_app \
--     < mvp/backend/postgres-app/migrations/2026-09-13-fangkorb-v2.sql

BEGIN;

ALTER TABLE raw_inputs
    ADD COLUMN IF NOT EXISTS destilled_by VARCHAR(255);

ALTER TABLE raw_input_content_links
    ADD COLUMN IF NOT EXISTS draft_id UUID
        REFERENCES raw_input_drafts(id) ON DELETE SET NULL;

ALTER TABLE raw_input_content_links
    ADD COLUMN IF NOT EXISTS content_type VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_raw_input_links_draft_id
    ON raw_input_content_links(draft_id);

UPDATE raw_inputs AS r
SET destilled_by = erster.user_id
FROM (
    SELECT DISTINCT ON (raw_input_id) raw_input_id, user_id
    FROM raw_input_drafts
    ORDER BY raw_input_id, updated_at
) AS erster
WHERE r.id = erster.raw_input_id
  AND r.destilled_by IS NULL;

UPDATE raw_inputs AS r
SET status = 'in_progress'
WHERE r.status = 'open'
  AND EXISTS (SELECT 1 FROM raw_input_drafts d WHERE d.raw_input_id = r.id);

UPDATE raw_input_content_links AS l
SET draft_id = d.id
FROM raw_input_drafts AS d
WHERE l.draft_id IS NULL
  AND d.raw_input_id = l.raw_input_id
  AND d.user_id = l.created_by;

COMMIT;
