-- Sperren mit Sperrgrund, Sperrnachricht und Widerspruch (#448)
--
-- Wer einen Beitrag sperrt, gibt einen Sperrgrund aus der Liste und eine
-- Begruendung an; beides steht hier je Sperre, zusammen mit der Kennung des
-- Autors, dem die Sperrnachricht gilt, und einem Widerspruch samt dem Ergebnis
-- der erneuten Pruefung. Je Beitrag gibt es hoechstens eine Sperre, die nicht
-- aufgehoben ist. Aufgehobene Sperren loescht der taegliche Lauf nach 180 Tagen
-- (services/loeschfristen_service.py, docs/LOESCHKONZEPT.md).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle beim
-- Start an, auch in bestehenden Datenbanken, vor dem Einspielen der Migrationen.
-- Das Skript dokumentiert das Schema und laeuft dann ohne Wirkung durch.
-- Vorhandene Daten gibt es keine: Bisherige Sperren stehen nur im Suchindex und
-- haben keinen Grund; sie bekommen keine Zeile.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS sperren (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    content_id UUID NOT NULL,
    sperrgrund VARCHAR(40) NOT NULL,
    begruendung TEXT NOT NULL,
    gesperrt_von VARCHAR(255),
    gesperrt_am TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    autor VARCHAR(255),
    aufgehoben_am TIMESTAMP WITH TIME ZONE,
    widerspruch TEXT,
    widerspruch_am TIMESTAMP WITH TIME ZONE,
    pruefung VARCHAR(20),
    pruefung_begruendung TEXT,
    geprueft_von VARCHAR(255),
    geprueft_am TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sperren_aktiv_je_beitrag
    ON sperren(content_id) WHERE aufgehoben_am IS NULL;
CREATE INDEX IF NOT EXISTS idx_sperren_autor ON sperren(autor);
CREATE INDEX IF NOT EXISTS idx_sperren_aufgehoben_am ON sperren(aufgehoben_am);

COMMIT;
