-- Entdoppelte Nutzung und Muster-Hinweise (#352, ADR 0004)
--
-- Fuer Punkte und "Diese Woche oft genutzt" zaehlt eine Nutzung hoechstens einmal
-- je Person (Besucher: Sitzung), Beitrag und Tag; der Zaehler an der Karte zaehlt
-- weiter jede. Fuenf Aenderungen:
--
--   usage_tracking.nutzung_entdoppelt  die entdoppelte Nutzung je Beitrag, wie
--                                      usage_count ueber die Frist der
--                                      usage_events hinaus.
--   usage_events.entdoppelt            ob das Ereignis die erste Nutzung dieser
--                                      Person an diesem Beitrag und Tag war.
--   nutzung_heute                      Pruefwerte (HMAC) des laufenden Tages,
--                                      verworfen nach Tagesende.
--   muster_pruefwerte                  Paar-Pruefwerte (HMAC) fuer die
--                                      Muster-Hinweise, 7 Tage.
--   muster_hinweise                    Kontenpaare, die sich gegenseitig nutzen,
--                                      fuer Admins; 8 Wochen nach dem letzten Tag
--                                      geloescht.
--
-- Neue Datenbanken brauchen das Skript nicht: create_all legt die Tabellen an,
-- init.sql hat die Spalten. Bestehende brauchen es fuer die Spalten.
--
-- Nachtragen: aus den vorhandenen usage_events, so gut es geht entdoppelt: je
-- Sitzung, Beitrag und UTC-Tag zaehlt das erste Ereignis, Ereignisse ohne
-- Sitzung zaehlen nicht. nutzung_entdoppelt ist die Zahl dieser Ereignisse. Nutzung
-- von vor der Frist der usage_events (90 Tage) ist nicht mehr zu entdoppeln und
-- zaehlt nicht; usage_count, der Zaehler an der Karte, bleibt. Nachgetragen wird
-- nur, wo die Spalte noch leer ist; ein zweiter Lauf aendert nichts.
-- ANNAHME (#352): Nutzung durch Startkonten von vor dem Einspielen ist darin nicht
-- zu erkennen (usage_events traegt keine Kennung) und zaehlt mit.
--
-- Sperren: usage_events und usage_tracking schreibt jede Kopie; das Skript wartet
-- deshalb hoechstens 5 s auf sie.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;
SET LOCAL lock_timeout = '5s';

ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS entdoppelt BOOLEAN;
UPDATE usage_events AS e SET entdoppelt = (x.id = x.erste_id)
FROM (
    SELECT id, first_value(id) OVER (
        PARTITION BY session_id, content_id,
            date(timestamp AT TIME ZONE 'UTC')
        ORDER BY timestamp, id
    ) AS erste_id
    FROM usage_events
) AS x
WHERE e.id = x.id AND e.entdoppelt IS NULL AND e.session_id IS NOT NULL;
UPDATE usage_events SET entdoppelt = false WHERE entdoppelt IS NULL;
ALTER TABLE usage_events ALTER COLUMN entdoppelt SET DEFAULT false;
ALTER TABLE usage_events ALTER COLUMN entdoppelt SET NOT NULL;

ALTER TABLE usage_tracking ADD COLUMN IF NOT EXISTS nutzung_entdoppelt INTEGER;
UPDATE usage_tracking AS t SET nutzung_entdoppelt = (
    SELECT count(*) FROM usage_events AS e
    WHERE e.content_id = t.content_id AND e.entdoppelt
)
WHERE t.nutzung_entdoppelt IS NULL;
ALTER TABLE usage_tracking ALTER COLUMN nutzung_entdoppelt SET DEFAULT 0;
ALTER TABLE usage_tracking ALTER COLUMN nutzung_entdoppelt SET NOT NULL;

CREATE TABLE IF NOT EXISTS nutzung_heute (
    pruefwert VARCHAR(64) PRIMARY KEY,
    tag DATE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nutzung_heute_tag ON nutzung_heute (tag);

CREATE TABLE IF NOT EXISTS muster_pruefwerte (
    pruefwert VARCHAR(64) PRIMARY KEY,
    tag DATE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_muster_pruefwerte_tag ON muster_pruefwerte (tag);

CREATE TABLE IF NOT EXISTS muster_hinweise (
    konto_a VARCHAR(255) NOT NULL,
    konto_b VARCHAR(255) NOT NULL,
    tage INTEGER NOT NULL,
    erster_tag DATE NOT NULL,
    letzter_tag DATE NOT NULL,
    PRIMARY KEY (konto_a, konto_b)
);
CREATE INDEX IF NOT EXISTS idx_muster_hinweise_letzter_tag
    ON muster_hinweise (letzter_tag);
CREATE INDEX IF NOT EXISTS idx_muster_hinweise_konto_b ON muster_hinweise (konto_b);

COMMIT;
