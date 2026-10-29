-- Entdoppelte Nutzung und Muster-Hinweise (#352, ADR 0004)
--
-- Fuer Punkte und "Diese Woche oft genutzt" zaehlt eine Nutzung hoechstens einmal
-- je Person (Besucher: Sitzung), Beitrag und Tag; der Zaehler an der Karte zaehlt
-- weiter jede. Vier Aenderungen:
--
--   usage_tracking.nutzung_entdoppelt  die entdoppelte Nutzung je Beitrag, wie
--                                      usage_count ueber die Frist der
--                                      usage_events hinaus.
--   usage_events.entdoppelt            ob das Ereignis die erste Nutzung dieser
--                                      Person an diesem Beitrag und Tag war.
--   nutzung_heute                      Pruefwerte (HMAC) des laufenden Tages,
--                                      verworfen nach Tagesende.
--   muster_hinweise                    Kontenpaare, die sich gegenseitig nutzen,
--                                      fuer Admins; 8 Wochen nach dem letzten Tag
--                                      geloescht.
--
-- Neue Datenbanken brauchen das Skript nicht: create_all legt die Tabellen an,
-- init.sql hat die Spalten. Bestehende brauchen es fuer die Spalten.
--
-- Nachtragen: Bisherige Nutzung gilt als entdoppelt (nutzung_entdoppelt =
-- usage_count, entdoppelt = true). Ob sie es war, ist nicht mehr festzustellen;
-- so bleibt "Diese Woche oft genutzt" nach dem Einspielen gefuellt. Nachgetragen
-- wird nur, wo die Spalte noch leer ist; ein zweiter Lauf aendert nichts.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

ALTER TABLE usage_tracking ADD COLUMN IF NOT EXISTS nutzung_entdoppelt INTEGER;
UPDATE usage_tracking SET nutzung_entdoppelt = usage_count
    WHERE nutzung_entdoppelt IS NULL;
ALTER TABLE usage_tracking ALTER COLUMN nutzung_entdoppelt SET DEFAULT 0;
ALTER TABLE usage_tracking ALTER COLUMN nutzung_entdoppelt SET NOT NULL;

ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS entdoppelt BOOLEAN;
UPDATE usage_events SET entdoppelt = true WHERE entdoppelt IS NULL;
ALTER TABLE usage_events ALTER COLUMN entdoppelt SET DEFAULT false;
ALTER TABLE usage_events ALTER COLUMN entdoppelt SET NOT NULL;

CREATE TABLE IF NOT EXISTS nutzung_heute (
    pruefwert VARCHAR(64) PRIMARY KEY,
    tag DATE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nutzung_heute_tag ON nutzung_heute (tag);

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
