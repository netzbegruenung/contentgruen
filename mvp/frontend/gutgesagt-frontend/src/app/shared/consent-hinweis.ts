/** Die CC0-Erklaerung, auf die das Wort "CC0" im Hinweis verlinkt (wie NB §4). */
export const CC0_ERKLAERUNG_URL = 'https://creativecommons.org/publicdomain/zero/1.0/deed.de';

/**
 * Der CC0-Hinweis ueber dem Absenden-Knopf, gleich in allen Formularen, die etwas fuer
 * andere sichtbar speichern (Einwurf, Kommentar, Hintergrundinfo, Bild, Post,
 * Aussage vorab anlegen in "Hier fehlt eine Antwort"; der Satz beim Destillieren mit eigenem
 * Wortlaut, siehe unten). Er traegt die CC0-Freigabe und bezieht die Nutzungsbedingungen ein
 * (#415). In Teilen, weil "CC0" und "Nutzungsbedingungen" im Template als Links stehen
 * (`Cc0HinweisComponent`).
 *
 * Jeder Wortlaut hat eine Kennung, die mit Beitrag, Satz und Einwurf gespeichert wird
 * (#431). Wer den Wortlaut aendert, vergibt eine neue: docs/CC0_HINWEIS_WORTLAUTE.md.
 */
export const CONSENT_HINWEIS = {
  kennung: '2026-11-02-formular',
  vorCc0: 'Mit dem Absenden stellst du deine eigene Formulierung unter ',
  cc0: 'CC0',
  nachCc0: ' und stimmst den ',
  nutzungsbedingungen: 'Nutzungsbedingungen',
  nachNutzungsbedingungen: ' zu – keine personenbezogenen Daten Dritter.',
} as const;

/** Beim Satz gibt es keinen Absenden-Knopf: Er wird beim Tippen gespeichert. */
export const CONSENT_HINWEIS_SATZ = {
  ...CONSENT_HINWEIS,
  kennung: '2026-11-02-satz',
  vorCc0: 'Dein Satz wird beim Tippen gespeichert. Damit stellst du deine eigene Formulierung unter ',
} as const;

export type ConsentHinweis = typeof CONSENT_HINWEIS | typeof CONSENT_HINWEIS_SATZ;

/** Der Hinweis als ein Satz, so wie er auf der Seite steht. */
export function hinweisText(hinweis: ConsentHinweis): string {
  return `${hinweis.vorCc0}${hinweis.cc0}${hinweis.nachCc0}${hinweis.nutzungsbedingungen}${hinweis.nachNutzungsbedingungen}`;
}

/** Eine Anfrage mit der Kennung des Hinweises, den das Formular gezeigt hat. */
export function mitCc0Wortlaut<T extends object>(
  anfrage: T,
  hinweis: { kennung: string } = CONSENT_HINWEIS,
): T & { cc0_wortlaut: string } {
  return { ...anfrage, cc0_wortlaut: hinweis.kennung };
}
