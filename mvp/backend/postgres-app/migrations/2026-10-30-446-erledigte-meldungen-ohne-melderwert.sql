-- Erledigte Meldungen ohne Sitzungskennung oder Tagespseudonym (#446)
--
-- Anonyme Meldungen tragen in reported_by_session_id das Tagespseudonym des
-- Besuchers, aber nur, solange sie offen sind: Bearbeiten oder Abweisen ersetzt es
-- durch einen Zufallswert ("anon:..."), angemeldete Meldungen verlieren den Wert
-- (repositories/content_report_repository.py, docs/LOESCHKONZEPT.md).
--
-- Neue Datenbanken brauchen dieses Skript nicht; es aendert kein Schema.
-- Vorhandene Daten: Meldungen, die vor #446 erledigt wurden, tragen noch die
-- Sitzungskennung aus dem Browser. Dieses Skript behandelt sie wie eine jetzt
-- erledigte Meldung. Offene Meldungen bleiben, wie sie sind. Ein zweiter Lauf
-- findet nichts mehr.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

UPDATE content_reports
SET reported_by_session_id = NULL
WHERE status <> 'pending'
  AND reported_by_user_id IS NOT NULL
  AND reported_by_session_id IS NOT NULL;

UPDATE content_reports
SET reported_by_session_id = 'anon:' || gen_random_uuid()
WHERE status <> 'pending'
  AND reported_by_user_id IS NULL
  AND left(reported_by_session_id, 5) <> 'anon:';

COMMIT;
