-- Loeschkommando, PostgreSQL-Teil: Schritt 1 und 2 aus docs/LOESCHKONZEPT.md.
--
-- Die Kennung kommt als psql-Variable uid, das Skript per stdin; der Aufruf steht
-- in docs/LOESCHKONZEPT.md unter "Kommandos".
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
-- Sperren an Beitraegen der Person bleiben, solange der Beitrag gesperrt ist; ihr
-- Widerspruch geht mit der Kennung, ohne Autor sieht niemand die Sperrnachricht.
UPDATE sperren SET autor = NULL, widerspruch = NULL WHERE autor = :'uid';
UPDATE sperren SET gesperrt_von = NULL WHERE gesperrt_von = :'uid';
UPDATE sperren SET geprueft_von = NULL WHERE geprueft_von = :'uid';
DELETE FROM raw_inputs       WHERE submitted_by        = :'uid';
-- Saetze an fremden Einwuerfen bleiben, die Kennung wird ersetzt: je Satz ein
-- eigener Platzhalter, weil der eindeutige Index (raw_input_id, user_id) keinen
-- gemeinsamen zulaesst und so auch nichts die Saetze untereinander verbindet.
-- Der Fangkorb zeigt dazu den Anzeigenamen "ehemalige Person" (derselbe wie
-- EHEMALIGE_PERSON_NAME in services/anzeigename_service.py fuer Beitraege).
CREATE TEMP TABLE loeschung_saetze AS
SELECT id, raw_input_id, 'ehemalige-person-' || gen_random_uuid() AS ersatz
FROM raw_input_drafts WHERE user_id = :'uid';
UPDATE raw_input_drafts AS d SET user_id = s.ersatz
FROM loeschung_saetze AS s WHERE d.id = s.id;
INSERT INTO users (user_id, anzeigename)
SELECT ersatz, 'ehemalige Person' FROM loeschung_saetze;
-- Destillierer: der Platzhalter des eigenen Satzes; wer den ersten Satz spaeter
-- geleert hat, bekommt einen eigenen. Der braucht keine Zeile in users: Kein
-- Codepfad zeigt einen Namen zu destilled_by.
UPDATE raw_inputs AS r SET destilled_by = s.ersatz
FROM loeschung_saetze AS s WHERE r.id = s.raw_input_id AND r.destilled_by = :'uid';
UPDATE raw_inputs SET destilled_by = 'ehemalige-person-' || gen_random_uuid()
WHERE destilled_by = :'uid';
-- Platzhalter ohne Satz: Saetze anderer Geloeschter an den eben geloeschten
-- Einwuerfen der Person.
DELETE FROM users AS u WHERE u.user_id LIKE 'ehemalige-person-%'
AND NOT EXISTS (SELECT 1 FROM raw_input_drafts AS d WHERE d.user_id = u.user_id);
DELETE FROM users           WHERE user_id             = :'uid';
DELETE FROM gesehene_nutzung WHERE user_id            = :'uid';
-- Muster-Hinweise (#352) nennen die Person neben einer anderen; der Hinweis geht
-- ganz, ohne die Person ist er keiner mehr.
DELETE FROM muster_hinweise WHERE konto_a = :'uid' OR konto_b = :'uid';
COMMIT;
