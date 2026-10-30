-- Tageszaehler der Suchen: Suchen ohne Treffer (#467)
--
-- Die Bilanz (#417) zeigt je Woche den Anteil der Suchen ohne Treffer. Nach der
-- Frist der Suchereignisse (90 Tage) bleibt von einem Tag nur der Tageszaehler in
-- suchen_je_tag. Die neue Spalte ohne_treffer zaehlt dort die Suchen des Tages
-- ohne Treffer, damit der Anteil die Frist ueberlebt. Wie die anderen Spalten
-- nur eine Zahl je Tag, kein Pseudonym.
--
-- Neue Datenbanken brauchen das Skript nicht: create_all legt die Tabelle mit
-- der Spalte an. Bestehende brauchen es, create_all ergaenzt keine Spalten.
--
-- Nachtragen: nichts. Tage, die schon verdichtet sind, behalten ohne_treffer
-- leer (NULL): Der Wert ist nicht mehr bekannt und wird nicht geschaetzt; die
-- Bilanz zeigt fuer solche Wochen keinen Anteil.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

ALTER TABLE suchen_je_tag ADD COLUMN IF NOT EXISTS ohne_treffer INTEGER;

COMMIT;
