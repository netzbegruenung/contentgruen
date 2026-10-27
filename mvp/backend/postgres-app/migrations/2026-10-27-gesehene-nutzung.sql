-- Gesehene Nutzung: der Stand fuer die Rueckmeldung beim Anmelden (#349)
--
-- Beim Anmelden sieht eine Person, wie oft ihre Beitraege seit ihrem letzten
-- Besuch genutzt wurden. Dafuer haelt diese Tabelle je Kennung fest, wie viele
-- Nutzungen sie zuletzt gezeigt bekam; die Rueckmeldung zeigt die Differenz. Ein
-- Zaehlerstand, kein Zeitpunkt: Wann jemand die App oeffnet, wird nicht gespeichert.
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle
-- beim Start an, auch in bestehenden Datenbanken. Das Skript dokumentiert das
-- Schema; der Dienst spielt es beim Start mit ein.
--
-- Nachtragen: nichts. Ohne Zeile gilt der Stand 0; die erste Rueckmeldung nennt die
-- ganze bisherige Nutzung.
--
-- Loeschen: docs/LOESCHKONZEPT.md, Schritt 2.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS gesehene_nutzung (
    user_id VARCHAR(255) PRIMARY KEY,
    nutzung INTEGER NOT NULL
);

COMMIT;
