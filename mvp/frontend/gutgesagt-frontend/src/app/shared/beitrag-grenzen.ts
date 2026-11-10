/**
 * Grenzen fuer Titel und Text eines Beitrags, gleich beim Anlegen und beim Aendern
 * (#299). Eine eigene Datei, damit der Dialog zum Aendern sie ohne die Formulare
 * importiert (sonst ein Import-Zyklus ueber das Sheet).
 */

/** Titelregel: eine Behauptung in einem Satz, 3 bis 120 Zeichen (CODING_STANDARDS.md). */
export const TITEL_MAX = 120;
/** Wie in den Formularen; kuerzer ist kein Argument. */
export const TEXT_MIN = 10;
/** Wie im AddCommentaryRequest: eine Antwort, die man so posten kann. */
export const KOMMENTAR_TEXT_MAX = 500;
/** Wie im AddGenericTextRequest; laenger ist keine Hintergrundinfo mehr, sondern ein Artikel. */
export const HINTERGRUNDINFO_TEXT_MAX = 2000;
/** Fassung Kurz eines Kommentars (#355): passt auf X und Bluesky, wie im Backend (dtos/commentary.py). */
export const KURZFASSUNG_MAX = 280;
/** Bis hierhin passt ein Text auf X und Bluesky ("passt auf X/Bluesky" in Formular und Karte). */
export const PLATTFORM_GRENZE = KURZFASSUNG_MAX;
/** Fassung Lang eines Kommentars (#355): Platz fuer Begruendung und Herkunft. */
export const LANGFASSUNG_MAX = 2000;
