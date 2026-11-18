-- Schalter mit Obergrenze und Admin-Wert (#708)
--
-- Je Schalter (punkte, abzeichen_sichtbar, gepostet) der Admin-Wert, den ein Admin auf
-- der Admin-Seite "Schalter" setzt, mit Zeitpunkt und Kennung des Admins; dazu ein
-- Verlauf jeder Aenderung. Wirksam ist ein Schalter nur, wenn die Obergrenze aus der
-- Umgebung (SEMANTIC_SEARCH_..._AKTIV) und der Admin-Wert an sind
-- (mvp/backend/semantic-search-service/app/services/schalter_service.py).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabellen beim
-- Start an, auch in bestehenden Datenbanken, vor dem Einspielen der Migrationen.
--
-- Vorhandene Daten: keine. Ohne Zeile gilt der Admin-Wert als aus; ein bisher per
-- Umgebung eingeschalteter Schalter ist danach aus, bis ein Admin ihn einschaltet
-- (docs/DEPLOYMENT.md). Ein zweiter Lauf aendert nichts. Die Kennung des Admins
-- (geaendert_von) darf leer sein: Das Loeschkommando leert sie mit dem Konto. Den
-- Verlauf loescht der Task der Loeschfristen nach einem Jahr (docs/LOESCHKONZEPT.md).
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS schalter (
    name VARCHAR(64) NOT NULL,
    an BOOLEAN NOT NULL,
    geaendert_am TIMESTAMP WITH TIME ZONE NOT NULL,
    geaendert_von VARCHAR(255),
    PRIMARY KEY (name)
);

CREATE TABLE IF NOT EXISTS schalter_verlauf (
    id UUID NOT NULL,
    name VARCHAR(64) NOT NULL,
    an BOOLEAN NOT NULL,
    geaendert_am TIMESTAMP WITH TIME ZONE NOT NULL,
    geaendert_von VARCHAR(255),
    PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_schalter_verlauf_geaendert_am
    ON schalter_verlauf (geaendert_am);

COMMIT;
