-- Art.-9-Einwilligung (#489)
--
-- Je Person eine Zeile: wann sie eingewilligt hat und die Kennung des Wortlauts, dem
-- sie zugestimmt hat (mvp/backend/semantic-search-service/app/domain/art9_einwilligung.py).
-- Nach einem Widerruf bleibt die Zeile mit dem Zeitpunkt des Widerrufs. Geloescht
-- wird sie mit dem Konto (docs/LOESCHKONZEPT.md, Schritt 2).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle beim
-- Start an, auch in bestehenden Datenbanken, vor dem Einspielen der Migrationen.
-- Das Skript dokumentiert das Schema und laeuft dann ohne Wirkung durch.
-- Vorhandene Daten gibt es keine.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS art9_einwilligungen (
    user_id VARCHAR(255) NOT NULL,
    wortlaut VARCHAR(64) NOT NULL,
    eingewilligt_am TIMESTAMP WITH TIME ZONE NOT NULL,
    widerrufen_am TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (user_id)
);

COMMIT;
