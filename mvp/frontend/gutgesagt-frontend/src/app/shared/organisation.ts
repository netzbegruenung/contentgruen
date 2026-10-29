/**
 * Namen und Links der Organisation, die diese Instanz betreibt (CODING_STANDARDS.md,
 * „Organisation-neutral where it costs nothing“). Neue Texte nehmen sie von hier;
 * Bestehendes zieht nach, wenn es aus anderem Grund angefasst wird.
 *
 * Die Angaben für die Rechtstexte (voller Vereinsname, Anschrift, Vorstand) stehen in
 * `legal-entity.ts` und ändern sich nur mit den Rechtstexten; hier steht, wie die
 * Organisation im übrigen Text heißt und wo man sie erreicht.
 */
export const ORGANISATION = {
  name: 'Netzbegrünung',
  vereinsname: 'Netzbegrünung e.V.',
  url: 'https://netzbegruenung.de/',
  kontakt: {
    name: 'Chatbegrünung',
    url: 'https://chatbegruenung.de/channel/GutGesagt',
  },
} as const;
