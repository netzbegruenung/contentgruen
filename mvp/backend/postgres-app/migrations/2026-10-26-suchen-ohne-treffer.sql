-- Suchen ohne Treffer: Zaehler je Aussage und Kalenderwoche
--
-- Findet eine Suche keinen Beitrag, zaehlt der Semantic-Service das an der
-- Aussage, die zur Suchanfrage ohnehin angelegt wird. Admins sehen daraus die
-- haeufigsten Suchanfragen ohne Treffer der letzten Wochen.
--
-- Die Tabelle traegt kein Pseudonym und keinen Zeitpunkt, nur den Montag der
-- Woche: Ein genauer Zeitpunkt liesse sich mit search_events verbinden. Wochen,
-- die aelter als acht Wochen sind, loescht der taegliche Aufraeumlauf des Dienstes.
--
-- Neue Datenbanken brauchen dieses Skript nicht: die Tabelle wird beim Start
-- von SQLAlchemy angelegt (infrastructure/database/connection.py:48), und
-- create_all legt fehlende Tabellen auch in bestehenden Datenbanken an. Das
-- Skript dokumentiert das Schema und dient Umgebungen, in denen die Tabelle vor
-- dem ersten Start des neuen Dienstes existieren soll.
--
-- Anwenden:
--   docker exec -i gutgesagt-app-postgres psql -U app_user -d gutgesagt_app \
--     < mvp/backend/postgres-app/migrations/2026-10-26-suchen-ohne-treffer.sql

BEGIN;

CREATE TABLE IF NOT EXISTS suchen_ohne_treffer (
    statement_id UUID NOT NULL,
    woche DATE NOT NULL,
    anzahl INTEGER NOT NULL,
    PRIMARY KEY (statement_id, woche)
);

CREATE INDEX IF NOT EXISTS idx_suchen_ohne_treffer_woche ON suchen_ohne_treffer(woche);

COMMIT;
