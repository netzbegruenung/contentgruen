-- Einladungen (#429)
--
-- Ein Admin legt im Admin-Dashboard eine Einladung an: eine Notiz, wie oft sie sich
-- einloesen laesst, und den letzten gueltigen Tag. Wer den Link hat, legt damit ein
-- Konto im Realm von Gut gesagt an. Die Zeile zaehlt nur die Einloesungen; eine
-- Mail-Adresse oder Kennung steht hier nicht, und am Konto steht nicht,
-- ueber welche Einladung es entstand (services/einladung_service.py).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle beim
-- Start an, auch in bestehenden Datenbanken, vor dem Einspielen der Migrationen.
-- Das Skript dokumentiert das Schema und laeuft dann ohne Wirkung durch.
-- Vorhandene Daten gibt es keine.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS einladungen (
    id UUID NOT NULL,
    code VARCHAR(64) NOT NULL,
    notiz TEXT NOT NULL,
    erlaubte_einloesungen INTEGER NOT NULL,
    einloesungen INTEGER DEFAULT 0 NOT NULL,
    gueltig_bis DATE NOT NULL,
    abgeschaltet BOOLEAN DEFAULT false NOT NULL,
    angelegt_am DATE NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (code)
);

COMMIT;
