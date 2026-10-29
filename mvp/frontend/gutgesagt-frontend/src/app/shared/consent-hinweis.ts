/** Die Freigabe selbst, gleich in jedem Wortlaut des CC0-Hinweises. */
const FREIGABE = 'stellst du deine eigene Formulierung unwiderruflich unter CC0 und bestätigst die ';

/**
 * Der CC0-Hinweis ueber dem Absenden-Knopf, gleich in allen Formularen, die etwas fuer
 * andere sichtbar speichern (Einwurf, Kommentar, Hintergrundinfo, Bild, Post,
 * Aussage vorab anlegen in "Hier fehlt eine Antwort"; der Satz beim Destillieren mit eigenem
 * Wortlaut, siehe unten). In drei Teilen, weil der Link auf die Nutzungsbedingungen im
 * Template als routerLink steht.
 */
export const CONSENT_HINWEIS = {
  vorLink: `Mit dem Absenden ${FREIGABE}`,
  link: 'Nutzungsbedingungen',
  nachLink: ' – keine personenbezogenen Daten Dritter.',
} as const;

/** Beim Satz gibt es keinen Absenden-Knopf: Er wird beim Tippen gespeichert. */
export const CONSENT_HINWEIS_SATZ = {
  ...CONSENT_HINWEIS,
  vorLink: `Dein Satz wird beim Tippen gespeichert. Damit ${FREIGABE}`,
} as const;
