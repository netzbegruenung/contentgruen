/**
 * Die Texte der Rückmeldung „Gepostet?“ nach dem Kopieren (#643), an einer Stelle.
 * Der Dank nennt eine echte Zahl: verschiedene Personen dieser Kalenderwoche, wie der
 * Server sie gezählt hat (CODING_STANDARDS.md „Visible numbers are real“).
 */
export const KOPIERT = 'Erfolgreich kopiert!';
export const KOPIERT_GEPOSTET_FRAGE = 'Kopiert. Gepostet?';
export const JA_GEPOSTET = 'Ja, gepostet';
/** So lange bleibt die Frage stehen: Zeit, den Knopf zu lesen und zu treffen. */
export const GEPOSTET_FRAGE_MS = 8000;
export const GEPOSTET_NICHT_GEZAEHLT = 'Danke! Zählen hat gerade nicht geklappt.';

/** Der Dank nach „Ja, gepostet“; ``personen`` schließt die Person selbst ein. */
export function gepostetDank(personen: number | null): string {
  if (personen === null) {
    return GEPOSTET_NICHT_GEZAEHLT;
  }
  if (personen <= 1) {
    return 'Danke! Du bist diese Woche die erste Person, die öffentlich kontert.';
  }
  return `Danke! Diese Woche haben ${personen} Menschen öffentlich gekontert, du bist dabei.`;
}
