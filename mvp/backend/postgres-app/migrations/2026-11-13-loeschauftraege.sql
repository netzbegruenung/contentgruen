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
-- Vorhandene Daten: Wer vor diesem Stand irgendwann widerrufen hat, auch wer danach
-- neu eingewilligt hat, bekommt einen offenen Auftrag, angelegt zum Zeitpunkt des
-- juengsten Widerrufs, mit Frist sieben Tage ab dem Einspielen (sonst waere er sofort
-- ueberfaellig); ausser es gibt schon einen offenen oder einen seit diesem Widerruf.
-- Was nach einer neuen Einwilligung entstand, erfasst der Auftrag nicht (Obergrenze,
-- repositories/loeschauftrag_repository.py; Entscheidung Maintainer, 13.11.2026).
-- Ein zweiter Lauf legt nichts an.
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
SELECT gen_random_uuid(), w.user_id, w.widerrufen_am, now() + interval '7 days'
FROM (
    SELECT user_id, max(widerrufen_am) AS widerrufen_am
    FROM art9_einwilligungen
    WHERE widerrufen_am IS NOT NULL
    GROUP BY user_id
) AS w
WHERE NOT EXISTS (
    SELECT 1 FROM loeschauftraege AS a
    WHERE a.user_id = w.user_id
      AND (a.erledigt_am IS NULL OR a.angelegt_am >= w.widerrufen_am)
);

COMMIT;
