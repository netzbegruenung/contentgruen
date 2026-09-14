/**
 * Der Hinweis ueber dem Absenden-Knopf, gleich in allen vier Formularen
 * (Einwurf, Kommentar, Hintergrundinfo, Bild). In drei Teilen, weil der Link auf
 * die Nutzungsbedingungen im Template als routerLink steht.
 */
export const CONSENT_HINWEIS = {
  vorLink: 'Mit dem Absenden stellst du deine Formulierung unwiderruflich unter CC0 und bestätigst die ',
  link: 'Nutzungsbedingungen',
  nachLink: ' – keine personenbezogenen Daten Dritter.',
} as const;
