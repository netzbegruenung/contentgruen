-- Loeschauftraege nach dem Widerruf der Art.-9-Einwilligung (DSFA R9b)
--
-- Je Widerruf ein Auftrag: Kennung der Person, wann er angelegt ist, bis wann ein
-- Admin den Loeschablauf ausfuehren soll (sieben Tage) und wann er es getan hat
-- (mvp/backend/semantic-search-service/app/services/loeschauftrag_service.py). Je
-- Person hoechstens ein offener Auftrag. Erledigte gehen nach ihrer Frist, alle mit
-- dem Konto (docs/LOESCHKONZEPT.md).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle beim
-- Start an, auch in bestehenden Datenbanken, vor dem Einspielen der Migrationen.
--
-- Vorhandene Daten: Wer vor diesem Stand widerrufen und seither nicht neu
-- eingewilligt hat, bekommt einen offenen Auftrag mit Frist ab dem Einspielen, ausser
-- es gibt schon einen seit diesem Widerruf. Ein zweiter Lauf legt deshalb nichts an.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS loeschauftraege (
    id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    angelegt_am TIMESTAMP WITH TIME ZONE NOT NULL,
    frist TIMESTAMP WITH TIME ZONE NOT NULL,
    erledigt_am TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_loeschauftraege_offen
    ON loeschauftraege (user_id) WHERE erledigt_am IS NULL;
CREATE INDEX IF NOT EXISTS idx_loeschauftraege_erledigt_am
    ON loeschauftraege (erledigt_am);

INSERT INTO loeschauftraege (id, user_id, angelegt_am, frist)
SELECT gen_random_uuid(), j.user_id, now(), now() + interval '7 days'
FROM (
    SELECT DISTINCT ON (user_id) user_id, widerrufen_am
    FROM art9_einwilligungen
    ORDER BY user_id, eingewilligt_am DESC
) AS j
WHERE j.widerrufen_am IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM loeschauftraege AS a
    WHERE a.user_id = j.user_id
      AND (a.erledigt_am IS NULL OR a.angelegt_am >= j.widerrufen_am)
  );

COMMIT;
