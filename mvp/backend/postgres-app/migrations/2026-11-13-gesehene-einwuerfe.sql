-- Gesehene Einwuerfe: Stand fuer "Seit deinem letzten Besuch" auf der Startseite
--
-- Neben der Nutzung haelt gesehene_nutzung je Kennung fest, wie viele Einwuerfe
-- anderer es beim letzten Besuch gab; die Startseite nennt die Differenz als "neue
-- Einwuerfe im Fangkorb". Ein Zaehlerstand, kein Zeitpunkt: Wann jemand die App
-- oeffnet, wird weiterhin nicht gespeichert.
--
-- Nachtragen: nichts. NULL heisst "noch nie gezaehlt"; der naechste Besuch setzt den
-- Stand und nennt nichts als neu.
--
-- Loeschen: mit der Zeile, docs/LOESCHKONZEPT.md, Schritt 2.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

ALTER TABLE gesehene_nutzung ADD COLUMN IF NOT EXISTS einwuerfe INTEGER;

COMMIT;
