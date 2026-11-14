-- Einwilligung "Punkte und Meilensteine" (#351)
--
-- Eine eigene, freiwillige Einwilligung nach Art. 9 Abs. 2 lit. a DSGVO, getrennt von
-- der Art.-9-Einwilligung zur Mitwirkung
-- (mvp/backend/semantic-search-service/app/domain/punkte_einwilligung.py). Je Antwort
-- eine Zeile: ja oder nein (eingewilligt), die Kennung des Wortlauts und wann. Es gilt
-- die juengste Zeile einer Kennung; ein Widerruf ist eine neue Zeile mit nein.
-- Geloescht werden alle mit dem Konto (docs/LOESCHKONZEPT.md, Schritt 2).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle beim
-- Start an, auch in bestehenden Datenbanken, vor dem Einspielen der Migrationen.
-- Das Skript dokumentiert das Schema und laeuft dann ohne Wirkung durch.
-- Vorhandene Daten gibt es keine.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS punkte_einwilligung (
    id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    eingewilligt BOOLEAN NOT NULL,
    wortlaut VARCHAR(64) NOT NULL,
    beantwortet_am TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_punkte_einwilligung_user
    ON punkte_einwilligung (user_id, beantwortet_am);

COMMIT;
