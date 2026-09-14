/**
 * Was der Fangkorb annimmt, in einem Satz. Steht auf der Startseiten-Kachel;
 * die lange Beschreibung baut darauf auf, damit beide nicht auseinanderlaufen.
 */
export const FANGKORB_KURZ = 'Ein Link, ein Hinweis oder beides – roh, ohne Ausarbeiten.';

/**
 * Was der Fangkorb annimmt und was danach passiert. Steht auf der Beitragen-Seite,
 * im Einwurf-Formular und in der Fangkorb-Liste; hier gepflegt, damit die Stellen
 * nicht wieder auseinanderlaufen. Er beschreibt das Formular: Link und Hinweis.
 */
export const FANGKORB_BESCHREIBUNG = `${FANGKORB_KURZ} Jemand macht später einen Beitrag daraus.`;

/**
 * Die Icons entlang der Kette, an jeder Stelle gleich: Startseite, Beitragen-Seite,
 * Einwurf-Formular, Fangkorb-Kopf, Header und Menue. `verfassen` steht auch fuer
 * Ausformulieren. Die Beitragstypen behalten ihre Icons.
 */
export const KETTEN_ICONS = {
  einwerfen: '📥',
  fangkorb: '🧺',
  destillieren: '⚗️',
  verfassen: '🖋️',
} as const;

/**
 * Fuer Angemeldete, solange die Plattform jung ist: Wer jetzt etwas eintraegt,
 * setzt die Massstaebe mit. Steht unter dem Fangkorb-Kopf und ueber der
 * Typ-Auswahl auf der Beitragen-Seite.
 */
export const ERSTNUTZER_SATZ =
  'Gut gesagt ist neu. Alles, was du hier einträgst, prägt mit, was hier Standard wird. Also: kein Scheiß.';
