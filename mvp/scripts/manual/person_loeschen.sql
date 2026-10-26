-- Loeschkommando, PostgreSQL-Teil: Schritt 1 und 2 aus docs/LOESCHKONZEPT.md.
--
-- Die Kennung kommt als psql-Variable, das Skript per stdin:
--   docker exec -i gutgesagt-app-postgres psql -U app_user -d gutgesagt_app \
--     -v ON_ERROR_STOP=1 -v uid="$UID" < mvp/scripts/manual/person_loeschen.sql
--
-- Wiederholbar: Ein zweiter Lauf findet nichts mehr, was die Kennung traegt.
-- Getestet in tests/integration/test_loeschkommando.py.

-- Schritt 1: Sitzungskennungen sichern. VOR jedem DELETE.
CREATE TEMP TABLE loeschung_sessions AS
SELECT DISTINCT reported_by_session_id AS session_id FROM content_reports
WHERE reported_by_user_id = :'uid' AND reported_by_session_id IS NOT NULL;
SELECT * FROM loeschung_sessions;

-- Schritt 2
BEGIN;
DELETE FROM usage_events WHERE session_id IN (SELECT session_id FROM loeschung_sessions);
DELETE FROM votes            WHERE user_id             = :'uid';
DELETE FROM content_reports  WHERE reported_by_user_id = :'uid';
UPDATE content_reports         SET reviewed_by = NULL WHERE reviewed_by = :'uid';
UPDATE raw_input_content_links SET created_by  = NULL WHERE created_by  = :'uid';
DELETE FROM raw_inputs       WHERE submitted_by        = :'uid';
-- Saetze an fremden Einwuerfen bleiben, die Kennung wird ersetzt: je Satz ein
-- eigener Platzhalter, weil der eindeutige Index (raw_input_id, user_id) keinen
-- gemeinsamen zulaesst und so auch nichts die Saetze untereinander verbindet.
-- Der Fangkorb zeigt dazu den Anzeigenamen "ehemalige Person".
CREATE TEMP TABLE loeschung_saetze AS
SELECT id, raw_input_id, 'ehemalige-person-' || gen_random_uuid() AS ersatz
FROM raw_input_drafts WHERE user_id = :'uid';
UPDATE raw_input_drafts AS d SET user_id = s.ersatz
FROM loeschung_saetze AS s WHERE d.id = s.id;
INSERT INTO users (user_id, anzeigename)
SELECT ersatz, 'ehemalige Person' FROM loeschung_saetze;
-- Destillierer: der Platzhalter des eigenen Satzes; wer den ersten Satz spaeter
-- geleert hat, bekommt einen eigenen.
UPDATE raw_inputs AS r SET destilled_by = s.ersatz
FROM loeschung_saetze AS s WHERE r.id = s.raw_input_id AND r.destilled_by = :'uid';
UPDATE raw_inputs SET destilled_by = 'ehemalige-person-' || gen_random_uuid()
WHERE destilled_by = :'uid';
DELETE FROM users           WHERE user_id             = :'uid';
COMMIT;
