-- Zustimmung zu den Nutzungsbedingungen in der App
--
-- Die App fragt die Nutzungsbedingungen kuenftig selbst, auf derselben Seite wie die
-- Art.-9-Einwilligung, mit eigenem Haekchen (Entscheidung Maintainer, 20.11.2026);
-- die Keycloak-Pflichtaktion "Terms and Conditions" entfaellt danach. Je Zustimmung
-- eine Zeile: Person, Stand der Nutzungsbedingungen (Kennung JJJJ-MM-TT,
-- mvp/backend/semantic-search-service/app/domain/nutzungsbedingungen.py) und
-- Zeitpunkt. Es gilt die juengste Zeile einer Kennung. Geloescht werden alle mit dem
-- Konto (docs/LOESCHKONZEPT.md, Schritt 2).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle beim
-- Start an, auch in bestehenden Datenbanken, vor dem Einspielen der Migrationen.
-- Das Skript dokumentiert das Schema und laeuft dann ohne Wirkung durch.
-- Vorhandene Daten gibt es keine: Bestandskonten werden einmal neu gefragt
-- (Entscheidung Maintainer, 20.11.2026), ihre Zustimmung in Keycloak wird nicht
-- uebernommen.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS nutzungsbedingungen_zustimmungen (
    id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    stand VARCHAR(64) NOT NULL,
    zugestimmt_am TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_nutzungsbedingungen_zustimmungen_user
    ON nutzungsbedingungen_zustimmungen (user_id, zugestimmt_am);

COMMIT;
