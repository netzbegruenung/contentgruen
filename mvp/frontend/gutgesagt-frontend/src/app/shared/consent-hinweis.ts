/** Die Freigabe selbst, gleich in jedem Wortlaut des CC0-Hinweises. */
const FREIGABE = 'stellst du deine eigene Formulierung unter CC0 und bestätigst die ';

/**
 * Der CC0-Hinweis ueber dem Absenden-Knopf, gleich in allen Formularen, die etwas fuer
 * andere sichtbar speichern (Einwurf, Kommentar, Hintergrundinfo, Bild, Post,
 * Aussage vorab anlegen in "Hier fehlt eine Antwort"; der Satz beim Destillieren mit eigenem
 * Wortlaut, siehe unten). In drei Teilen, weil der Link auf die Nutzungsbedingungen im
 * Template als routerLink steht.
 *
 * Jeder Wortlaut hat eine Kennung, die mit Beitrag, Satz und Einwurf gespeichert wird
 * (#431). Wer den Wortlaut aendert, vergibt eine neue: docs/CC0_HINWEIS_WORTLAUTE.md.
 */
export const CONSENT_HINWEIS = {
  kennung: '2026-10-29-formular',
  vorLink: `Mit dem Absenden ${FREIGABE}`,
  link: 'Nutzungsbedingungen',
  nachLink: ' – keine personenbezogenen Daten Dritter.',
} as const;

/** Beim Satz gibt es keinen Absenden-Knopf: Er wird beim Tippen gespeichert. */
export const CONSENT_HINWEIS_SATZ = {
  ...CONSENT_HINWEIS,
  kennung: '2026-10-29-satz',
  vorLink: `Dein Satz wird beim Tippen gespeichert. Damit ${FREIGABE}`,
} as const;

/** Eine Anfrage mit der Kennung des Hinweises, den das Formular gezeigt hat. */
export function mitCc0Wortlaut<T extends object>(
  anfrage: T,
  hinweis: { kennung: string } = CONSENT_HINWEIS,
): T & { cc0_wortlaut: string } {
  return { ...anfrage, cc0_wortlaut: hinweis.kennung };
}
