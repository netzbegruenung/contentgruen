-- Rueckmeldung "Ja, gepostet" nach dem Kopieren (#643)
--
-- gepostet_pruefwerte: je Person, die in der laufenden Kalenderwoche gemeldet hat,
-- ein Pruefwert (HMAC ueber die Kennung mit einem Wochenschluessel nur im Speicher,
-- mvp/backend/semantic-search-service/app/services/gepostet_service.py) und der
-- Montag der Woche. Keine Kennung, kein Beitrag.
-- gepostet_wochen: je vergangener Woche nur die Zahl der Personen. Die Pruefwerte
-- einer Woche werden nach ihrem Ende dorthin verdichtet und geloescht
-- (docs/LOESCHKONZEPT.md).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabellen beim
-- Start an, auch in bestehenden Datenbanken, vor dem Einspielen der Migrationen.
-- Das Skript dokumentiert das Schema und laeuft dann ohne Wirkung durch.
-- Vorhandene Daten gibt es keine.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS gepostet_pruefwerte (
    pruefwert VARCHAR(64) NOT NULL,
    woche DATE NOT NULL,
    PRIMARY KEY (pruefwert)
);
CREATE INDEX IF NOT EXISTS idx_gepostet_pruefwerte_woche
    ON gepostet_pruefwerte (woche);

CREATE TABLE IF NOT EXISTS gepostet_wochen (
    woche DATE NOT NULL,
    personen INTEGER NOT NULL,
    PRIMARY KEY (woche)
);

COMMIT;
