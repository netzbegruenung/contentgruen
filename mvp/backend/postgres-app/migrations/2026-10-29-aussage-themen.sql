-- Themen an Aussagen (#363)
--
-- Aussagen werden mit Themen aus einer festen, kurzen Liste geordnet
-- (domain/themen.json im Semantic-Service), hoechstens zwei je Aussage. Je
-- Zuordnung eine Zeile mit Aussage, Thema und Zuordnungsart ('von_hand', spaeter auch
-- die einer Automatik). Die Tabelle traegt weder Kennung noch Zeitpunkt: Die
-- Zuordnungen von Hand sind das Testset fuer spaetere Themenvorschlaege und
-- sollen ohne Personendaten exportierbar sein.
--
-- Neue Datenbanken brauchen dieses Skript nicht: die Tabelle wird beim Start
-- von SQLAlchemy angelegt (infrastructure/database/connection.py), und
-- create_all legt fehlende Tabellen auch in bestehenden Datenbanken an, vor dem
-- Einspielen der Migrationen beim Start. Das Skript dokumentiert das Schema und
-- laeuft dann ohne Wirkung durch. Vorhandene Daten gibt es keine.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS aussage_themen (
    statement_id UUID NOT NULL,
    thema VARCHAR(40) NOT NULL,
    zuordnungsart VARCHAR(20) DEFAULT 'von_hand' NOT NULL,
    PRIMARY KEY (statement_id, thema)
);

COMMIT;
